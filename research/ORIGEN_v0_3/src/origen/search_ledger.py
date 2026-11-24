"""Tamper-evident hash-chained research event ledger.

A local hash chain detects edits, reordering and interior deletion. It cannot
prove that an unlogged event never occurred; external custody is still required.
"""
from pathlib import Path
from typing import Any
import hashlib
import json
import math
import re

GENESIS = "0" * 64
_REQUIRED_EVENT_FIELDS = {"event_id", "timestamp_utc", "event_type", "frame_id", "details"}
_RECORD_FIELDS = {
    "event", "event_sha256", "previous_chain_sha256", "chain_sha256", "ledger_schema"
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _validate_json_value(value: Any, path: str = "value") -> None:
    """Accept only deterministic, finite JSON values with exact built-in types."""
    kind = type(value)
    if kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{path}_object_keys_must_be_exact_text")
            try:
                key.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise ValueError(f"{path}_contains_invalid_unicode") from exc
            _validate_json_value(item, f"{path}.{key}")
    elif kind is list:
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
    elif kind is str:
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{path}_contains_invalid_unicode") from exc
    elif kind is float:
        if not math.isfinite(value):
            raise ValueError(f"{path}_contains_non_finite_number")
    elif kind in (int, bool) or value is None:
        return
    else:
        raise ValueError(f"{path}_contains_unsupported_json_type")


def _canonical(value: Any) -> str:
    """Serialize one exact JSON value deterministically; NaN/Infinity are forbidden."""
    try:
        _validate_json_value(value)
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (RecursionError, TypeError, UnicodeEncodeError) as exc:
        raise ValueError("value_is_not_canonical_json") from exc


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    """Reject duplicate keys instead of silently accepting the last occurrence."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError("non_finite_json_constant")


def _validate_event(event: Any) -> None:
    if type(event) is not dict:
        raise TypeError("event_must_be_an_exact_builtin_dict")
    if any(type(key) is not str for key in event):
        raise ValueError("event_keys_must_be_exact_text")
    missing = _REQUIRED_EVENT_FIELDS - set(event)
    if missing:
        raise ValueError("missing_fields:" + ",".join(sorted(missing)))
    for field in ("event_id", "timestamp_utc", "event_type", "frame_id"):
        value = event[field]
        if type(value) is not str or not value or value != value.strip():
            raise ValueError(f"{field}_must_be_non_empty_canonical_text")
    if type(event["details"]) is not dict:
        raise ValueError("details_must_be_an_exact_builtin_dict")
    _canonical(event)


def _parse_ledger_record(line: str) -> dict:
    """Parse one canonical ledger line with duplicate-key and number checks."""
    try:
        row = json.loads(
            line,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid_ledger_json") from exc
    if type(row) is not dict:
        raise ValueError("ledger_record_must_be_an_object")
    if line != _canonical(row):
        raise ValueError("noncanonical_json_record")
    if set(row) != _RECORD_FIELDS:
        raise ValueError("ledger_record_fields_mismatch")
    _validate_event(row["event"])
    for field in ("event_sha256", "previous_chain_sha256", "chain_sha256"):
        if type(row[field]) is not str or not _SHA256_RE.fullmatch(row[field]):
            raise ValueError(f"{field}_must_be_lowercase_sha256")
    if type(row["ledger_schema"]) is not str:
        raise ValueError("ledger_schema_must_be_exact_text")
    return row


def append_event(path: str | Path, event: dict[str, Any]) -> str:
    _validate_event(event)
    payload = _canonical(event)
    event_digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    previous = GENESIS
    if p.exists() and p.stat().st_size:
        audit = audit_ledger(p)
        if audit["state"] != "PASS":
            raise ValueError("cannot_append_to_invalid_or_legacy_ledger")
        text = p.read_text(encoding="utf-8")
        lines = text[:-1].split("\n")
        records = [_parse_ledger_record(line) for line in lines]
        if any(row["event"]["event_id"] == event["event_id"] for row in records):
            raise ValueError("duplicate_event_id")
        previous = records[-1]["chain_sha256"]

    chain_digest = hashlib.sha256((previous + event_digest).encode("ascii")).hexdigest()
    record = {
        "event": event,
        "event_sha256": event_digest,
        "previous_chain_sha256": previous,
        "chain_sha256": chain_digest,
        "ledger_schema": "ORIGEN_CHAIN_V1",
    }
    with p.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(_canonical(record) + "\n")
    return chain_digest


def audit_ledger(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    errors = []
    count = 0
    seen = set()
    previous = GENESIS
    legacy = False
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "events": 0,
            "errors": [{"line": 1, "error": "ledger_not_valid_utf8"}],
            "legacy_ledger": False,
            "final_chain_sha256": previous,
            "state": "BLOCKED",
            "interpretation": (
                "Hash chaining detects changes within the retained file, but "
                "independent external custody is required to detect complete-file "
                "replacement or omitted real-world events."
            ),
        }

    if text and "\r" in text:
        errors.append({"line": 1, "error": "unsupported_carriage_return"})
    if text and not text.endswith("\n"):
        errors.append({"line": max(1, text.count("\n") + 1), "error": "unterminated_final_record"})
    lines = text[:-1].split("\n") if text.endswith("\n") else text.split("\n")
    for line_no, line in enumerate(lines, 1):
        try:
            row = _parse_ledger_record(line)
            event = row["event"]
            digest = hashlib.sha256(_canonical(event).encode("utf-8")).hexdigest()
            if digest != row["event_sha256"]:
                errors.append({"line": line_no, "error": "event_hash_mismatch"})
            event_id = event["event_id"]
            if event_id in seen:
                errors.append({"line": line_no, "error": "duplicate_event_id"})
            seen.add(event_id)
            if row["ledger_schema"] != "ORIGEN_CHAIN_V1":
                legacy = True
                errors.append({"line": line_no, "error": "legacy_unanchored_event"})
            else:
                if row["previous_chain_sha256"] != previous:
                    errors.append({"line": line_no, "error": "chain_link_mismatch"})
                expected = hashlib.sha256((previous + digest).encode("ascii")).hexdigest()
                if row["chain_sha256"] != expected:
                    errors.append({"line": line_no, "error": "chain_hash_mismatch"})
                previous = row["chain_sha256"]
            count += 1
        except Exception as exc:
            errors.append({
                "line": line_no,
                "error": "invalid_event",
                "detail": str(exc),
            })

    state = "PASS" if count and not errors else "BLOCKED"
    return {
        "events": count,
        "errors": errors,
        "legacy_ledger": legacy,
        "final_chain_sha256": previous,
        "state": state,
        "interpretation": (
            "Hash chaining detects changes within the retained file, but "
            "independent external custody is required to detect complete-file "
            "replacement or omitted real-world events."
        ),
    }
