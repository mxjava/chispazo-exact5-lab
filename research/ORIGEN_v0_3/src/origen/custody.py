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
from typing import Any
from zoneinfo import ZoneInfo

GENESIS = "0" * 64
CLASSIC_PORTFOLIO_LINES = 30
MAX_CUSTODY_RECORD_BYTES = 65_536
MAX_CUSTODY_RECORD_JSON_DEPTH = 16
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SHA40 = re.compile(r"[0-9a-f]{40}")
_CHISPAZO_LOCAL_TIMEZONE = ZoneInfo("America/Mexico_City")
_CLASSIC_CLOSE_SLOT = (21, 0, 0, 0)

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


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _require_sha(value: Any, field: str) -> None:
    if type(value) is not str or not _HEX64.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")


def parse_utc(value: str, field: str) -> datetime:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a non-empty ISO-8601 timestamp")
    # RFC 3339 -00:00 means the local offset is unknown, not UTC.
    # Treating it as UTC would manufacture certainty in custody chronology.
    if value.endswith("-00:00"):
        raise ValueError(f"{field} must not use the unknown UTC offset -00:00")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field} must have an explicit UTC offset (+00:00 or Z)")
    return parsed.astimezone(timezone.utc)


def _require_classic_close_slot(closes: datetime) -> None:
    """Reject a CLASSIC label whose declared close is not the official 21:00 slot."""
    local = closes.astimezone(_CHISPAZO_LOCAL_TIMEZONE)
    slot = (local.hour, local.minute, local.second, local.microsecond)
    if slot != _CLASSIC_CLOSE_SLOT:
        raise ValueError(
            "official_draw_close_at_utc must resolve to the 21:00 "
            "America/Mexico_City Classic slot"
        )


def validate_portfolio(portfolio: bytes, expected_lines: int = CLASSIC_PORTFOLIO_LINES) -> list[str]:
    if type(expected_lines) is not int or expected_lines != CLASSIC_PORTFOLIO_LINES:
        raise ValueError(f"Classic custody portfolios must contain exactly {CLASSIC_PORTFOLIO_LINES} lines")
    if type(portfolio) is not bytes:
        raise TypeError("portfolio must be supplied as exact bytes")
    if type(expected_lines) is not int or expected_lines <= 0:
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


def _record_digest(record: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
    return sha256_bytes(canonical_json_bytes(unsigned))


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
    if type(target_contest_id) is not int or target_contest_id <= 0:
        raise ValueError("target_contest_id must be a positive integer")
    if type(expected_lines) is not int or expected_lines != CLASSIC_PORTFOLIO_LINES:
        raise ValueError(f"Classic custody portfolios must contain exactly {CLASSIC_PORTFOLIO_LINES} lines")
    if type(history_max_contest_id) is not int or history_max_contest_id != target_contest_id - 1:
        raise ValueError("history cutoff must be an integer exactly target_contest_id - 1")
    if type(modality) is not str or modality != "CLASSIC":
        raise ValueError("only CLASSIC modality is eligible")
    for field, value in (
        ("candidate_spec_sha256", candidate_spec_sha256),
        ("history_sha256", history_sha256),
        ("environment_manifest_sha256", environment_manifest_sha256),
        ("custodian_recomputed_sha256", custodian_recomputed_sha256),
        ("previous_record_sha256", previous_record_sha256),
    ):
        _require_sha(value, field)
    if type(source_commit) is not str or not _SHA40.fullmatch(source_commit):
        raise ValueError("source_commit must be a full 40-character Git SHA")
    for field, value in (
        ("candidate_id", candidate_id), ("generator_id", generator_id),
        ("generator_clock_source", generator_clock_source), ("custodian_id", custodian_id),
        ("custodian_clock_source", custodian_clock_source),
        ("official_draw_close_source", official_draw_close_source),
    ):
        if type(value) is not str or not value.strip():
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
    _require_classic_close_slot(closes)
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
        # These are public untrusted-object boundaries. Subclasses can override
        # get/items/decode/strip and make validation inspect a different view.
        if type(record) is not dict:
            return False, "record must be an exact dict"
        # Exact dict containers may still hold str subclasses as keys. Their
        # equality/hash hooks can execute during set construction or lookup.
        # Reject them before the first mapping access at this public boundary.
        if any(type(key) is not str for key in record):
            return False, "record keys must be exact built-in strings"
        if type(portfolio) is not bytes:
            return False, "portfolio must be exact bytes"
        if expected_previous is not None and type(expected_previous) is not str:
            return False, "expected_previous must be an exact string"
        if type(record.get("schema_version")) is not str or record["schema_version"] != "exact5.custody.v1":
            return False, "unsupported record schema"
        if set(record) != _RECORD_FIELDS:
            return False, "record fields do not match exact v1 schema"
        if type(record.get("target_contest_id")) is not int:
            return False, "target_contest_id must be an integer"
        if type(record.get("history_max_contest_id")) is not int:
            return False, "history_max_contest_id must be an integer"
        if record["target_contest_id"] <= 0:
            return False, "target_contest_id must be positive"
        count = record.get("portfolio_line_count")
        if type(count) is not int or count != CLASSIC_PORTFOLIO_LINES:
            return False, f"portfolio_line_count must equal {CLASSIC_PORTFOLIO_LINES}"
        for field in (
            "candidate_spec_sha256", "history_sha256", "environment_manifest_sha256",
            "portfolio_sha256", "custodian_recomputed_sha256",
            "previous_record_sha256", "record_sha256",
        ):
            _require_sha(record.get(field), field)
        if type(record.get("source_commit")) is not str or not _SHA40.fullmatch(record["source_commit"]):
            return False, "source_commit must be a full 40-character Git SHA"
        for field in (
            "candidate_id", "generator_id", "custodian_id",
            "generator_clock_source", "custodian_clock_source",
            "official_draw_close_source",
        ):
            if type(record.get(field)) is not str or not record[field].strip():
                return False, f"{field} must be non-empty"
        if record["generator_id"] == record["custodian_id"]:
            return False, "generator and custodian identities are not independent"
        if type(record.get("seal_status")) is not str or record["seal_status"] != "SEALED":
            return False, "record is not a sealed Classic registration"
        if type(record.get("modality")) is not str or record["modality"] != "CLASSIC":
            return False, "record is not a sealed Classic registration"
        if record["record_sha256"] != _record_digest(record):
            return False, "record digest mismatch"
        validate_portfolio(portfolio, count)
        actual = sha256_bytes(portfolio)
        if actual != record["portfolio_sha256"] or actual != record["custodian_recomputed_sha256"]:
            return False, "portfolio bytes do not match generator and custodian hashes"
        if expected_previous is not None and record["previous_record_sha256"] != expected_previous:
            return False, "previous-record chain link mismatch"
        generated = parse_utc(record["generated_at_utc"], "generated_at_utc")
        received = parse_utc(record["received_at_utc"], "received_at_utc")
        closes = parse_utc(record["official_draw_close_at_utc"], "official_draw_close_at_utc")
        _require_classic_close_slot(closes)
        if not (generated < received < closes):
            return False, "generation/receipt timestamps are not strictly ordered pre-close"
        if record["history_max_contest_id"] != record["target_contest_id"] - 1:
            return False, "history cutoff is not strictly prior to target"
        return True, "seal verified; external identity, timestamp, and custody assertions remain unverified"
    except (TypeError, ValueError, KeyError, OverflowError) as exc:
        return False, str(exc)


def verify_record_chain(
    records: list[dict[str, Any]],
    portfolios_by_target: dict[int, bytes],
    expected_final_hash: str | None = None,
) -> tuple[bool, str]:
    """Verify ordered ledger; optional external head anchor detects tail truncation."""
    # Reject user-defined containers: their iteration, lookup, or length methods
    # can present a different view from the underlying values being verified.
    if type(records) is not list:
        return False, "records must be an exact list"
    if type(portfolios_by_target) is not dict:
        return False, "portfolios_by_target must be an exact dict"
    if any(type(target) is not int or target <= 0 for target in portfolios_by_target):
        return False, "portfolio map keys must be positive exact integers"
    if any(type(value) is not bytes for value in portfolios_by_target.values()):
        return False, "portfolio map values must be exact bytes"
    if not records:
        return False, "custody chain must contain at least one record"
    previous = GENESIS
    seen: set[int] = set()
    last_target = 0
    for index, record in enumerate(records):
        if type(record) is not dict:
            return False, f"record {index} must be an exact dict"
        # Check keys before record.get(): a hostile str subclass can collide
        # with "target_contest_id" and run caller code during dictionary lookup.
        if any(type(key) is not str for key in record):
            return False, f"record {index} keys must be exact built-in strings"
        target = record.get("target_contest_id")
        if type(target) is not int or target <= last_target:
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
    if type(record) is not dict or set(record) != _RECORD_FIELDS:
        raise ValueError("record must be an exact dict matching the exact v1 schema")
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


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON object key: {key}")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def _validate_record_json_depth(raw: bytes) -> None:
    """Bound JSON nesting before the recursive decoder processes untrusted bytes."""
    depth = 0
    in_string = False
    escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_CUSTODY_RECORD_JSON_DEPTH:
                raise ValueError("record JSON exceeds maximum nesting depth " + str(MAX_CUSTODY_RECORD_JSON_DEPTH))
        elif byte in (0x7D, 0x5D) and depth:
            depth -= 1


def _reject_record_json_float(value: str) -> None:
    raise ValueError("floating-point JSON numbers are not permitted in custody records")


def read_record(path: str | Path) -> dict[str, Any]:
    """Read one bounded canonical record; reject ambiguous JSON encodings and values."""
    source = Path(path)
    # Read at most one byte beyond the limit. A stat()-then-read_bytes()
    # sequence is vulnerable to file growth between the size check and read,
    # allowing an untrusted record to consume unbounded memory.
    with source.open("rb") as stream:
        raw = stream.read(MAX_CUSTODY_RECORD_BYTES + 1)
    if len(raw) > MAX_CUSTODY_RECORD_BYTES:
        raise ValueError("record file exceeds maximum size of " + str(MAX_CUSTODY_RECORD_BYTES) + " bytes")
    _validate_record_json_depth(raw)
    if not raw.endswith(b"\n"):
        raise ValueError("record file must end with LF")
    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=_unique_json_object,
        parse_constant=_reject_json_constant,
        parse_float=_reject_record_json_float,
    )
    if type(value) is not dict:
        raise ValueError("record JSON must be an exact object")
    if raw != canonical_json_bytes(value) + b"\n":
        raise ValueError("record JSON must use canonical UTF-8 JSON encoding")
    return value
