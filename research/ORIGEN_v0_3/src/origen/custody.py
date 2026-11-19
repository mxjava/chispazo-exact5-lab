"""Pre-close prospective custody primitives for Exact5 (research-only).

This module verifies byte-level seals and independent receipt assertions. It does
not provide a trusted timestamp authority, digital signature, or independent
custodian; those remain operational requirements.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SHA40 = re.compile(r"[0-9a-f]{40}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


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
    if not portfolio or not portfolio.endswith(b"\n"):
        raise ValueError("portfolio must be non-empty and end with LF")
    if b"\r" in portfolio:
        raise ValueError("portfolio must use canonical LF line endings")
    try:
        text = portfolio.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("portfolio must be valid UTF-8") from exc
    lines = text[:-1].split("\n")
    if len(lines) != expected_lines:
        raise ValueError(f"portfolio must contain exactly {expected_lines} lines")
    normalized: list[str] = []
    for index, line in enumerate(lines, start=1):
        if not re.fullmatch(r"(?:0[1-9]|1\d|2[0-8])-(?:0[1-9]|1\d|2[0-8])-(?:0[1-9]|1\d|2[0-8])-(?:0[1-9]|1\d|2[0-8])-(?:0[1-9]|1\d|2[0-8])", line):
            raise ValueError(f"line {index} must contain five two-digit values separated by hyphens")
        nums = [int(part) for part in line.split("-")]
        if nums != sorted(nums) or len(set(nums)) != 5:
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
    """Build a verifiable record; caller must retain receipt independently."""
    if not isinstance(target_contest_id, int) or isinstance(target_contest_id, bool) or target_contest_id <= 0:
        raise ValueError("target_contest_id must be a positive integer")
    if (not isinstance(history_max_contest_id, int) or isinstance(history_max_contest_id, bool)
            or history_max_contest_id != target_contest_id - 1):
        raise ValueError("history cutoff must be an integer exactly target_contest_id - 1")
    if not isinstance(expected_lines, int) or isinstance(expected_lines, bool) or expected_lines <= 0:
        raise ValueError("expected_lines must be a positive integer")
    if modality != "CLASSIC":
        raise ValueError("only CLASSIC modality is eligible")
    for field, value in (
        ("history_sha256", history_sha256),
        ("environment_manifest_sha256", environment_manifest_sha256),
        ("custodian_recomputed_sha256", custodian_recomputed_sha256),
        ("previous_record_sha256", previous_record_sha256),
    ):
        if not isinstance(value, str) or not _HEX64.fullmatch(value):
            raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
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
    validate_portfolio(portfolio, expected_lines)
    portfolio_hash = sha256_bytes(portfolio)
    if custodian_recomputed_sha256 != portfolio_hash:
        raise ValueError("custodian hash does not match exact portfolio bytes")
    generated = parse_utc(generated_at_utc, "generated_at_utc")
    received = parse_utc(received_at_utc, "received_at_utc")
    closes = parse_utc(official_draw_close_at_utc, "official_draw_close_at_utc")
    if received < generated:
        raise ValueError("custodian receipt cannot precede generation")
    if generated >= closes or received >= closes:
        raise ValueError("both generation and independent receipt must precede draw close")
    record: dict[str, Any] = {
        "schema_version": "exact5.custody.v1",
        "candidate_id": candidate_id,
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


def verify_seal_record(record: dict[str, Any], portfolio: bytes, expected_previous: str | None = None) -> tuple[bool, str]:
    """Verify record digest, byte binding, timing, modality, and optional chain link."""
    try:
        if not isinstance(record, dict) or record.get("schema_version") != "exact5.custody.v1":
            return False, "unsupported record schema"
        claimed = record.get("record_sha256")
        if not isinstance(claimed, str) or not _HEX64.fullmatch(claimed):
            return False, "invalid record_sha256"
        if claimed != _record_digest(record):
            return False, "record digest mismatch"
        if record.get("seal_status") != "SEALED" or record.get("modality") != "CLASSIC":
            return False, "record is not a sealed Classic registration"
        validate_portfolio(portfolio, int(record.get("portfolio_line_count", 0)))
        actual = sha256_bytes(portfolio)
        if actual != record.get("portfolio_sha256") or actual != record.get("custodian_recomputed_sha256"):
            return False, "portfolio bytes do not match generator and custodian hashes"
        if expected_previous is not None and record.get("previous_record_sha256") != expected_previous:
            return False, "previous-record chain link mismatch"
        generated = parse_utc(record.get("generated_at_utc"), "generated_at_utc")
        received = parse_utc(record.get("received_at_utc"), "received_at_utc")
        closes = parse_utc(record.get("official_draw_close_at_utc"), "official_draw_close_at_utc")
        if not (generated <= received < closes):
            return False, "generation/receipt timestamps are not pre-close and ordered"
        if record.get("history_max_contest_id") != record.get("target_contest_id") - 1:
            return False, "history cutoff is not strictly prior to target"
        return True, "seal verified; independent assertions still require external corroboration"
    except (TypeError, ValueError, KeyError) as exc:
        return False, str(exc)


def write_record_exclusive(path: str | Path, record: dict[str, Any]) -> None:
    """Create one immutable record file; never replace an existing target record."""
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
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("record JSON must be an object")
    return value
