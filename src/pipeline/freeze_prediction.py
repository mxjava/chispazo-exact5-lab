from __future__ import annotations
from pathlib import Path
import argparse, hashlib, hmac, json, re, subprocess, os, tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd

if __package__:
    from .strict_json import load_json_object
else:
    from strict_json import load_json_object


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def publish_immutable_registration(dest: Path, serialized: str) -> None:
    """Atomically publish a complete registration without replacing an existing target.

    The staged file is fsynced first. A same-directory hard link is an atomic
    no-replace publication on supported local filesystems. On Windows, where
    hard links can be unavailable to the process, same-directory ``os.rename``
    provides atomic no-replace publication as well.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{dest.name}.", suffix=".tmp", dir=str(dest.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp_name, dest)
        except FileExistsError as exc:
            raise SystemExit(f"Immutable registration already exists: {dest}") from exc
        except OSError:
            if os.name != "nt":
                raise
            try:
                # Windows rename fails atomically if dest already exists. The
                # source is staged beside dest, so this cannot cross volumes.
                os.rename(temp_name, dest)
            except FileExistsError as exc:
                raise SystemExit(f"Immutable registration already exists: {dest}") from exc
        # Persist the directory entry where directory fsync is supported.
        if os.name == "posix":
            dir_fd = os.open(dest.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def verify_commit_binding(expected_sha: str, repo_root: Path | str = ".") -> str:
    """Require the registration SHA to match the current, clean tracked Git checkout."""
    expected = str(expected_sha).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("--commit-sha must be a full 40-character Git SHA")
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=repo_root, check=True, capture_output=True, text=True, timeout=5,
        ).stdout.strip().lower()
        diff = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=repo_root, capture_output=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("cannot verify commit binding: a readable Git checkout is required") from exc
    if diff.returncode == 1:
        raise ValueError("cannot freeze from a checkout with tracked changes; commit or discard them first")
    if diff.returncode != 0:
        raise ValueError("cannot verify tracked working-tree cleanliness")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("Git returned an invalid HEAD commit SHA")
    if expected != head:
        raise ValueError(f"--commit-sha {expected} does not match checked-out HEAD {head}")
    return head


def verify_registration_payload(payload: dict) -> bool:
    """Verify checksum and structural invariants before a registration is published."""
    if not isinstance(payload, dict):
        return False
    claimed = payload.get("registration_sha256")
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        return False
    target = payload.get("target")
    if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
        return False
    history_max = payload.get("history_max")
    if isinstance(history_max, bool) or not isinstance(history_max, int) or history_max != target - 1:
        return False
    commit_sha = payload.get("commit_sha")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        return False
    for key in ("history_sha256", "ranking_sha256"):
        value = payload.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            return False
    if not isinstance(payload.get("model_version"), str) or not payload["model_version"].strip():
        return False
    if payload.get("preflight_state") != "PASS":
        return False
    lines = payload.get("lines")
    if not isinstance(lines, list) or len(lines) != 30:
        return False
    normalized = []
    for line in lines:
        if not isinstance(line, str):
            return False
        parts = line.split("-")
        if len(parts) != 5 or any(not re.fullmatch(r"\d{2}", part) for part in parts):
            return False
        nums = [int(part) for part in parts]
        if any(n < 1 or n > 28 for n in nums) or len(set(nums)) != 5:
            return False
        if nums != sorted(nums) or line != "-".join(f"{n:02d}" for n in nums):
            return False
        normalized.append(line)
    if len(set(normalized)) != 30:
        return False
    try:
        utc_dt = datetime.fromisoformat(str(payload.get("registered_at_utc", "")).replace("Z", "+00:00"))
        local_dt = datetime.fromisoformat(str(payload.get("registered_at_mexico_city", "")).replace("Z", "+00:00"))
        mexico_zone = ZoneInfo("America/Mexico_City")
        if utc_dt.tzinfo is None or local_dt.tzinfo is None:
            return False
        # Require UTC semantics, the expected Mexico City offset for that date,
        # and exact equality of instants. Merely checking tzinfo allows forged
        # or independently sampled timestamps to disagree while checksum-valid.
        if utc_dt.utcoffset() != timezone.utc.utcoffset(utc_dt):
            return False
        if local_dt.utcoffset() != mexico_zone.utcoffset(local_dt):
            return False
        if utc_dt.astimezone(timezone.utc) != local_dt.astimezone(timezone.utc):
            return False
    except (ValueError, OverflowError):
        return False
    unsigned = {key: value for key, value in payload.items() if key != "registration_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hmac.compare_digest(claimed, sha256_bytes(canonical))


def normalize_lines(df: pd.DataFrame) -> list[str]:
    if "combo" in df.columns:
        vals = df["combo"].astype(str).tolist()
    else:
        cols = [c for c in ["R1","R2","R3","R4","R5","n1","n2","n3","n4","n5"] if c in df.columns]
        if len(cols) < 5:
            raise ValueError("portfolio requires combo or five number columns")
        cols = cols[:5]
        vals = ["-".join(map(str,row)) for row in df[cols].itertuples(index=False, name=None)]
    out=[]
    for v in vals:
        parts=[int(x) for x in v.replace(","," ").replace("-"," ").split()]
        if len(parts)!=5 or len(set(parts))!=5 or any(x<1 or x>28 for x in parts):
            raise ValueError(f"invalid combo: {v}")
        out.append("-".join(f"{x:02d}" for x in sorted(parts)))
    if len(out)!=30 or len(set(out))!=30:
        raise ValueError(f"portfolio must contain exactly 30 distinct lines; got rows={len(out)}, unique={len(set(out))}")
    return out


def main() -> int:
    ap=argparse.ArgumentParser(description="Freeze an immutable pre-sorteo 30-line registration")
    ap.add_argument("--target",type=int,required=True)
    ap.add_argument("--portfolio",required=True)
    ap.add_argument("--preflight",required=True)
    ap.add_argument("--model-version",required=True)
    ap.add_argument("--commit-sha",required=True,help="must match the clean tracked checkout HEAD")
    ap.add_argument("--ledger-dir",default="data/prospective-ledger")
    ap.add_argument("--repo-root",default=".",help="Git repository root used to verify --commit-sha")
    a=ap.parse_args()
    try:
        verified_head = verify_commit_binding(a.commit_sha, a.repo_root)
    except ValueError as exc:
        raise SystemExit(f"Refusing freeze: {exc}") from exc
    try:
        pre = load_json_object(a.preflight)
    except ValueError as exc:
        raise SystemExit(f"Refusing freeze: invalid preflight JSON: {exc}") from exc
    if pre.get("state")!="PASS":
        raise SystemExit("Refusing freeze: preflight state is not PASS")
    if pre.get("target") != a.target:
        raise SystemExit(f"Refusing freeze: preflight target={pre.get('target')} does not match requested target={a.target}")
    history_meta=pre.get("inputs",{}).get("history",{})
    if history_meta.get("contest_max") != a.target - 1:
        raise SystemExit(f"Refusing freeze: history_max={history_meta.get('contest_max')} must equal target-1={a.target-1}")
    lines=normalize_lines(pd.read_csv(a.portfolio))
    ledger=Path(a.ledger_dir); ledger.mkdir(parents=True,exist_ok=True)
    dest=ledger/f"target_{a.target}.json"
    if dest.exists():
        raise SystemExit(f"Immutable registration already exists: {dest}")
    # Recheck immediately before publication to reduce the chance of a HEAD move
    # or tracked edit between initial validation and freezing.
    try:
        verify_commit_binding(verified_head, a.repo_root)
    except ValueError as exc:
        raise SystemExit(f"Refusing freeze: repository changed before publication: {exc}") from exc
    registered_at_utc = datetime.now(timezone.utc)
    registered_at_mexico_city = registered_at_utc.astimezone(ZoneInfo("America/Mexico_City"))
    payload={
      "target":a.target,
      "registered_at_utc":registered_at_utc.isoformat(),
      "registered_at_mexico_city":registered_at_mexico_city.isoformat(),
      "commit_sha":verified_head,
      "model_version":a.model_version,
      "history_max":history_meta.get("contest_max"),
      "history_sha256":history_meta.get("sha256"),
      "ranking_sha256":pre.get("inputs",{}).get("ranking",{}).get("sha256"),
      "preflight_state":"PASS",
      "gate_summary":{
        "state":pre.get("state"),
        "failed_checks":[c.get("name") for c in pre.get("checks",[]) if c.get("critical",True) and c.get("status")!="PASS"],
      },
      "lines":lines,
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    payload["registration_sha256"]=sha256_bytes(canonical)
    if not verify_registration_payload(payload):
        raise SystemExit("Refusing freeze: generated registration failed schema/checksum self-validation")
    serialized = json.dumps(payload,indent=2,ensure_ascii=False)
    publish_immutable_registration(dest, serialized)
    print(dest)
    print(payload["registration_sha256"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
