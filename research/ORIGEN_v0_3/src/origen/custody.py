"""Research-only pre-close custody primitives for Exact5.

This module binds exact portfolio bytes to a canonical record and verifies a
hash-linked sequence. It does NOT provide signatures, trusted timestamps,
independent identity proof, or tamper-proof storage. Those require external
custody and timestamp infrastructure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

GENESIS = "0" * 64
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_RECORD_FIELDS = {
    "schema_version", "candidate_id", "candidate_spec_sha256",
    "target_contest_id", "modality", "history_max_contest_id",
    "history_sha256", "source_commit", "environment_manifest_sha256",
    "portfolio_sha256", "portfolio_line_count", "generator_id",
    "generated_at_utc", "generator_clock_source", "custodian_id",
    "received_at_utc", "custodian_clock_source",
    "custodian_recomputed_sha256", "official_draw_close_at_utc",
    "official_draw_close_source", "seal_status", "previous_record_sha256",
    "record_sha256",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _require_sha(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")


def parse_utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field} must have an explicit UTC offset (+00:00 or Z)")
    return parsed.astimezone(timezone.utc)


def validate_portfolio(portfolio: bytes, expected_lines: int = 30) -> list[str]:
    if not isinstance(portfolio, bytes):
        raise TypeError("portfolio must be supplied as exact bytes")
    if not isinstance(expected_lines, int) or isinstance(expected_lines, bool) or expected_lines <= 0:
        raise ValueError("expected_lines must be a positive integer")
    if not portfolio or not portfolio.endswith(b"\n"):
        raise ValueError("portfolio must be non-empty and end with LF")
    if b"\r" in portfolio:
        raise ValueError("portfolio must use canonical LF line endings")
    try:
        decoded = portfolio.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("portfolio must be valid UTF-8") from exc
    lines = decoded[:-1].split("\n")
    if len(lines) != expected_lines:
        raise ValueError(f"portfolio must contain exactly {expected_lines} lines")
    normalized: list[str] = []
    pattern = re.compile(
        r"(?:0[1-9]|1\d|2[0-8])-(?:0[1-9]|1\d|2[0-8])-"
        r"(?:0[1-9]|1\d|2[0-8])-(?:0[1-9]|1\d|2[0-8])-"
        r"(?:0[1-9]|1\d|2[0-8])"
    )
    for index, line in enumerate(lines, start=1):
        if not pattern.fullmatch(line):
            raise ValueError(f"line {index} must contain five two-digit values separated by hyphens")
        numbers = [int(part) for part in line.split("-")]
        if numbers != sorted(numbers) or len(set(numbers)) != 5:
            raise ValueError(f"line {index} must contain five distinct ascending values")
        normalized.append(line)
    if len(set(normalized)) != expected_lines:
        raise ValueError("portfolio lines must be unique")
    return normalized


def _record_digest(record: Mapping[str, Any]) -> str:
    unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
    return sha256_bytes(canonical_json_bytes(unsigned))


def _validate_record_semantics(record: Mapping[str, Any]) -> None:
    """Validate all self-contained record invariants (not external authenticity)."""
    if set(record) != _RECORD_FIELDS:
        raise ValueError("record fields do not match exact v1 schema")
    if record.get("schema_version") != "exact5.custody.v1":
        raise ValueError("unsupported record schema")
    target = record.get("target_contest_id")
    if not isinstance(target, int) or isinstance(target, bool) or target <= 0:
        raise ValueError("target_contest_id must be a positive integer")
    history_max = record.get("history_max_contest_id")
    if (not isinstance(history_max, int) or isinstance(history_max, bool)
            or history_max != target - 1):
        raise ValueError("history cutoff must be an integer exactly target_contest_id - 1")
    count = record.get("portfolio_line_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise ValueError("portfolio_line_count must be a positive integer")
    for field in ("candidate_spec_sha256", "history_sha256", "environment_manifest_sha256",
                  "portfolio_sha256", "custodian_recomputed_sha256",
                  "previous_record_sha256", "record_sha256"):
        _require_sha(record.get(field), field)
    if record["portfolio_sha256"] != record["custodian_recomputed_sha256"]:
        raise ValueError("generator and custodian portfolio hashes differ")
    if not isinstance(record.get("source_commit"), str) or not _SHA40.fullmatch(record["source_commit"]):
        raise ValueError("source_commit must be a full 40-character Git SHA")
    for field in ("candidate_id", "generator_id", "custodian_id",
                  "generator_clock_source", "custodian_clock_source",
                  "official_draw_close_source"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"{field} must be non-empty")
    if record.get("modality") != "CLASSIC" or record.get("seal_status") != "SEALED":
        raise ValueError("record is not a sealed Classic registration")
    if record["generator_id"] == record["custodian_id"]:
        raise ValueError("generator and custodian identities are not independent")
    generated = parse_utc(record.get("generated_at_utc"), "generated_at_utc")
    received = parse_utc(record.get("received_at_utc"), "received_at_utc")
    closes = parse_utc(record.get("official_draw_close_at_utc"), "official_draw_close_at_utc")
    if not (generated < received < closes):
        raise ValueError("generation/receipt timestamps are not strictly ordered pre-close")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def build_seal_record(
    *,
    candidate_id: str,
    candidate_spec_sha256: str,
    target_contest_id: int,
    history_max_contest_id: int,
    modality: str,
    history_sha256: str,
    source_commit: str,
    environment_manifest_sha256: str,
    portfolio: bytes,
    generator_id: str,
    generated_at_utc: str,
    generator_clock_source: str,
    custodian_id: str,
    received_at_utc: str,
    custodian_clock_source: str,
    custodian_recomputed_sha256: str,
    official_draw_close_at_utc: str,
    official_draw_close_source: str,
    previous_record_sha256: str = GENESIS,
    expected_lines: int = 30,
) -> dict[str, Any]:
    """Build a hash-bound record; caller must retain an independent receipt."""
    if not isinstance(target_contest_id, int) or isinstance(target_contest_id, bool) or target_contest_id <= 0:
        raise ValueError("target_contest_id must be a positive integer")
    if (not isinstance(history_max_contest_id, int) or isinstance(history_max_contest_id, bool)
            or history_max_contest_id != target_contest_id - 1):
        raise ValueError("history cutoff must be an integer exactly target_contest_id - 1")
    if modality != "CLASSIC":
        raise ValueError("only CLASSIC modality is eligible")
    for field, value in (
        ("candidate_spec_sha256", candidate_spec_sha256),
        ("history_sha256", history_sha256),
        ("environment_manifest_sha256", environment_manifest_sha256),
        ("custodian_recomputed_sha256", custodian_recomputed_sha256),
        ("previous_record_sha256", previous_record_sha256),
    ):
        _require_sha(value, field)
    if not isinstance(source_commit, str) or not _SHA40.fullmatch(source_commit):
        raise ValueError("source_commit must be a full 40-character Git SHA")
    for field, value in (
        ("candidate_id", candidate_id), ("generator_id", generator_id),
        ("generator_clock_source", generator_clock_source), ("custodian_id", custodian_id),
        ("custodian_clock_source", custodian_clock_source),
        ("official_draw_close_source", official_draw_close_source),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be non-empty")
    if generator_id == custodian_id:
        raise ValueError("generator and custodian identities must be distinct")
    validate_portfolio(portfolio, expected_lines)
    portfolio_hash = sha256_bytes(portfolio)
    if custodian_recomputed_sha256 != portfolio_hash:
        raise ValueError("custodian hash does not match exact portfolio bytes")
    generated = parse_utc(generated_at_utc, "generated_at_utc")
    received = parse_utc(received_at_utc, "received_at_utc")
    closes = parse_utc(official_draw_close_at_utc, "official_draw_close_at_utc")
    if received <= generated:
        raise ValueError("custodian receipt must strictly follow generation")
    if generated >= closes or received >= closes:
        raise ValueError("both generation and independent receipt must precede draw close")
    record: dict[str, Any] = {
        "schema_version": "exact5.custody.v1",
        "candidate_id": candidate_id,
        "candidate_spec_sha256": candidate_spec_sha256,
        "target_contest_id": target_contest_id,
        "modality": modality,
        "history_max_contest_id": history_max_contest_id,
        "history_sha256": history_sha256,
        "source_commit": source_commit,
        "environment_manifest_sha256": environment_manifest_sha256,
        "portfolio_sha256": portfolio_hash,
        "portfolio_line_count": expected_lines,
        "generator_id": generator_id,
        "generated_at_utc": generated.isoformat().replace("+00:00", "Z"),
        "generator_clock_source": generator_clock_source,
        "custodian_id": custodian_id,
        "received_at_utc": received.isoformat().replace("+00:00", "Z"),
        "custodian_clock_source": custodian_clock_source,
        "custodian_recomputed_sha256": custodian_recomputed_sha256,
        "official_draw_close_at_utc": closes.isoformat().replace("+00:00", "Z"),
        "official_draw_close_source": official_draw_close_source,
        "seal_status": "SEALED",
        "previous_record_sha256": previous_record_sha256,
    }
    record["record_sha256"] = _record_digest(record)
    return record


def verify_seal_record(
    record: dict[str, Any],
    portfolio: bytes,
    expected_previous: str | None = None,
) -> tuple[bool, str]:
    """Verify schema, digest, byte binding, temporal order, and optional chain link."""
    try:
        if not isinstance(record, dict):
            return False, "record JSON must be an object"
        _validate_record_semantics(record)
        count = record["portfolio_line_count"]
        if record["record_sha256"] != _record_digest(record):
            return False, "record digest mismatch"
        validate_portfolio(portfolio, count)
        actual = sha256_bytes(portfolio)
        if actual != record["portfolio_sha256"] or actual != record["custodian_recomputed_sha256"]:
            return False, "portfolio bytes do not match generator and custodian hashes"
        if expected_previous is not None and record["previous_record_sha256"] != expected_previous:
            return False, "previous-record chain link mismatch"
        return True, "seal verified; external identity, timestamp, and custody assertions remain unverified"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        return False, str(exc)


def verify_record_chain(
    records: Sequence[dict[str, Any]],
    portfolios_by_target: Mapping[int, bytes],
    expected_final_hash: str | None = None,
) -> tuple[bool, str]:
    """Verify ordered ledger; optional external head anchor detects tail truncation."""
    previous = GENESIS
    seen: set[int] = set()
    last_target = 0
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            return False, f"record {index} is not an object"
        target = record.get("target_contest_id")
        if not isinstance(target, int) or isinstance(target, bool) or target <= last_target:
            return False, f"record {index} target is duplicate, invalid, or out of order"
        if target in seen:
            return False, f"duplicate target {target}"
        if target not in portfolios_by_target:
            return False, f"missing portfolio bytes for target {target}"
        ok, reason = verify_seal_record(record, portfolios_by_target[target], previous)
        if not ok:
            return False, f"record {index} failed: {reason}"
        seen.add(target)
        previous = record["record_sha256"]
        last_target = target
    if len(seen) != len(portfolios_by_target):
        return False, "portfolio map contains unregistered targets"
    if expected_final_hash is not None:
        _require_sha(expected_final_hash, "expected_final_hash")
        if previous != expected_final_hash:
            return False, "externally anchored ledger head mismatch (possible tail truncation or rewrite)"
    return True, f"verified {len(records)} ordered custody records"


def write_record_exclusive(path: str | Path, record: dict[str, Any]) -> None:
    """Create a record file without replacement; this is not tamper-proof storage."""
    if not isinstance(record, dict):
        raise ValueError("record does not match exact v1 schema")
    _validate_record_semantics(record)
    if record.get("record_sha256") != _record_digest(record):
        raise ValueError("record digest mismatch; refusing to write")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(record) + b"\n"
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            destination.unlink()
        except OSError:
            pass
        raise


def read_record(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("record file must end with LF")
    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=_reject_duplicate_json_keys,
        parse_constant=_reject_json_constant,
    )
    if not isinstance(value, dict):
        raise ValueError("record JSON must be an object")
    if raw != canonical_json_bytes(value) + b"\n":
        raise ValueError("record file is not canonical JSON serialization")
    return value
