from __future__ import annotations
from pathlib import Path
import argparse, hashlib, hmac, json, os, re, stat, tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

if __package__:
    from .strict_json import load_json_object
else:
    import importlib.util

    _strict_json_spec = importlib.util.spec_from_file_location(
        "_exact5_strict_json", Path(__file__).with_name("strict_json.py")
    )
    if _strict_json_spec is None or _strict_json_spec.loader is None:
        raise ImportError("could not load pipeline strict_json module")
    _strict_json = importlib.util.module_from_spec(_strict_json_spec)
    _strict_json_spec.loader.exec_module(_strict_json)
    load_json_object = _strict_json.load_json_object


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _invalidate_output(path: Path | str | None, inputs: tuple[Path | str, ...]) -> Path | None:
    """Remove any prior report so a failed run cannot leave stale output behind."""
    if path is None:
        return None
    output = Path(path)
    for source in inputs:
        source_path = Path(source)
        try:
            same_path = output.resolve() == source_path.resolve()
            if not same_path and output.exists() and source_path.exists():
                same_path = os.path.samefile(output, source_path)
        except (OSError, RuntimeError):
            same_path = False
        if same_path:
            raise SystemExit("evaluation output path must not overlap an input artifact")

    try:
        mode = output.lstat().st_mode
    except FileNotFoundError:
        return output
    except OSError as exc:
        raise SystemExit(f"cannot inspect evaluation output path: {exc}") from exc
    if not (stat.S_ISREG(mode) or stat.S_ISLNK(mode)):
        raise SystemExit("evaluation output path must be a regular file or symlink")
    try:
        output.unlink()
    except OSError as exc:
        raise SystemExit(f"cannot invalidate previous evaluation output: {exc}") from exc
    return output


def _write_report_atomically(path: Path, text: str) -> None:
    """Publish a complete report at the requested output path."""
    fd: int | None = None
    temp_name: str | None = None
    write_error: OSError | None = None
    cleanup_errors: list[OSError] = []
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        stream = os.fdopen(fd, "w", encoding="utf-8", newline="")
        fd = None  # The stream owns it from this point on.
        with stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except OSError as exc:
        write_error = exc
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as exc:
                cleanup_errors.append(exc)
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError as exc:
                cleanup_errors.append(exc)

    if write_error is not None:
        message = f"cannot write evaluation output: {write_error}"
        if cleanup_errors:
            details = "; ".join(str(error) for error in cleanup_errors)
            message += f"; temporary cleanup failed: {details}"
        raise SystemExit(message) from write_error
    if cleanup_errors:
        details = "; ".join(str(error) for error in cleanup_errors)
        raise SystemExit(f"temporary cleanup failed: {details}") from cleanup_errors[0]


def verify_registration_payload(reg: dict) -> bool:
    """Reject altered or structurally invalid prospective registrations before scoring."""
    if not isinstance(reg, dict):
        return False
    claimed = reg.get("registration_sha256")
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        return False
    target = reg.get("target")
    if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
        return False
    history_max = reg.get("history_max")
    if (isinstance(history_max, bool) or not isinstance(history_max, int)
            or history_max <= 0 or history_max != target - 1
            or reg.get("preflight_state") != "PASS"):
        return False
    if not isinstance(reg.get("model_version"), str) or not reg["model_version"].strip():
        return False
    if not isinstance(reg.get("commit_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", reg["commit_sha"]):
        return False
    for key in ("history_sha256", "ranking_sha256"):
        if not isinstance(reg.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", reg[key]):
            return False
    try:
        utc_dt = datetime.fromisoformat(str(reg.get("registered_at_utc", "")).replace("Z", "+00:00"))
        local_dt = datetime.fromisoformat(str(reg.get("registered_at_mexico_city", "")).replace("Z", "+00:00"))
        mexico_zone = ZoneInfo("America/Mexico_City")
        if utc_dt.tzinfo is None or local_dt.tzinfo is None:
            return False
        if utc_dt.utcoffset() != timezone.utc.utcoffset(utc_dt):
            return False
        if local_dt.utcoffset() != mexico_zone.utcoffset(local_dt):
            return False
        if utc_dt.astimezone(timezone.utc) != local_dt.astimezone(timezone.utc):
            return False
    except (ValueError, OverflowError):
        return False
    lines = reg.get("lines")
    if not isinstance(lines, list) or len(lines) != 30:
        return False
    normalized = []
    for line in lines:
        if not isinstance(line, str):
            return False
        parts = line.split("-")
        if len(parts) != 5 or any(not re.fullmatch(r"\d{2}", p) for p in parts):
            return False
        nums = [int(p) for p in parts]
        if nums != sorted(nums) or len(set(nums)) != 5 or any(n < 1 or n > 28 for n in nums):
            return False
        normalized.append(line)
    if len(set(normalized)) != 30:
        return False
    unsigned = {key: value for key, value in reg.items() if key != "registration_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hmac.compare_digest(claimed, hashlib.sha256(canonical).hexdigest())


def verify_artifact_bindings(
    reg: dict,
    history_path: Path | str,
    ranking_path: Path | str,
    trusted_registration_sha256: str,
) -> tuple[bool, str]:
    """Bind supplied source artifacts to a registration pinned outside its JSON file."""
    if not verify_registration_payload(reg):
        return False, "registration schema or checksum verification failed"

    if (not isinstance(trusted_registration_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", trusted_registration_sha256)):
        return False, "trusted registration SHA-256 must be 64 lowercase hexadecimal characters"
    if not hmac.compare_digest(reg["registration_sha256"], trusted_registration_sha256):
        return False, "registration SHA-256 does not match the externally trusted value"

    for name, path, key in (
        ("history", history_path, "history_sha256"),
        ("ranking", ranking_path, "ranking_sha256"),
    ):
        try:
            actual = sha256_file(path)
        except (OSError, TypeError, ValueError) as exc:
            return False, f"{name} artifact cannot be read: {exc}"
        if not hmac.compare_digest(actual, reg[key]):
            return False, f"{name} artifact SHA-256 does not match the frozen registration"
    return True, "registration and source artifact hashes verified"


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--registration",required=True)
    ap.add_argument("--history",required=True, help="history file whose bytes were hashed at preflight")
    ap.add_argument("--ranking",required=True, help="ranking file whose bytes were hashed at preflight")
    ap.add_argument(
        "--trusted-registration-sha256", required=True,
        help="registration SHA-256 retained independently from the mutable registration file",
    )
    ap.add_argument("--result",required=True,nargs=5,type=int)
    ap.add_argument("--out")
    a=ap.parse_args()
    output_path = _invalidate_output(
        a.out, (a.registration, a.history, a.ranking)
    )
    try:
        reg = load_json_object(a.registration)
    except ValueError as exc:
        raise SystemExit(f"invalid or unreadable prospective registration: {exc}") from exc
    if not verify_registration_payload(reg):
        raise SystemExit("invalid or tampered prospective registration: schema/checksum verification failed")
    artifacts_ok, detail = verify_artifact_bindings(
        reg, a.history, a.ranking, a.trusted_registration_sha256
    )
    if not artifacts_ok:
        raise SystemExit(f"invalid prospective artifact integrity: {detail}")
    result=set(a.result)
    if len(result)!=5 or any(n<1 or n>28 for n in result):
        raise SystemExit("invalid result")
    scores=[]
    for line in reg["lines"]:
        s=set(int(x) for x in line.split("-"))
        scores.append({"combo":line,"hits":len(s & result)})
    scores.sort(key=lambda x:(-x["hits"],x["combo"]))
    report = {
        "target": reg["target"],
        "registration_sha256": reg["registration_sha256"],
        "history_sha256": reg["history_sha256"],
        "ranking_sha256": reg["ranking_sha256"],
        "result": "-".join(f"{x:02d}" for x in sorted(result)),
        "best_hits": scores[0]["hits"],
        "exact5": sum(x["hits"] == 5 for x in scores),
        "lines": scores,
    }
    text=json.dumps(report,indent=2,ensure_ascii=False)
    if output_path is not None:
        _write_report_atomically(output_path, text)
    print(text)
    return 0

if __name__=="__main__": raise SystemExit(main())
