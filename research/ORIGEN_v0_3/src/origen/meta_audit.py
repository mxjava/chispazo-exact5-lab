"""MetaObserver checks for temporal validity of the recorded search path."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

from .search_ledger import audit_ledger_bytes

OUTCOME_ACCESS = {"outcome_access", "result_viewed", "test_outcome_access"}
ADAPTIVE_CHANGES = {
    "metric_changed", "hypothesis_generated", "frame_dropped",
    "exclusion_rule_changed", "primary_outcome_changed",
    "search_parameter_changed", "model_family_changed",
}
PREREG_EVENTS = {"protocol_preregistered", "protocol_sealed"}
_TIMESTAMP_RE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?P<zone>Z|[+-][0-9]{2}:[0-9]{2})?\Z"
)


def audit_search_path(path: str | Path) -> dict:
    # Read once, then audit and interpret this exact immutable snapshot. A
    # second path read after a successful audit would create a TOCTOU gap.
    raw = Path(path).read_bytes()
    integrity = audit_ledger_bytes(raw)
    if integrity["state"] != "PASS":
        return {
            "state": "BLOCKED",
            "ledger_integrity": integrity["state"],
            "events": integrity["events"],
            "first_outcome_access_index": None,
            "findings": [{
                "severity": "BLOCKER",
                "type": "ledger_integrity_blocked",
            }],
            "ledger_errors": integrity["errors"],
            "interpretation": (
                "Search-path semantics were not evaluated because ledger "
                "integrity did not pass. The auditor fails closed and does not "
                "parse malformed or tampered records. A valid local hash chain "
                "still does not prove that every real-world action was logged."
            ),
        }
    text = raw.decode("utf-8", errors="strict")
    events = [
        json.loads(line)["event"]
        for line in text.splitlines()
        if line.strip()
    ]
    findings = []
    timestamps = []
    for index, event in enumerate(events):
        event_id = event.get("event_id")
        ts = event.get("timestamp_utc", "")
        if type(ts) is not str:
            findings.append({
                "severity": "BLOCKER",
                "type": "invalid_timestamp",
                "event_id": event_id,
            })
            continue
        match = _TIMESTAMP_RE.fullmatch(ts)
        if match is None:
            findings.append({
                "severity": "BLOCKER",
                "type": "invalid_timestamp",
                "event_id": event_id,
            })
            continue
        zone = match.group("zone")
        if zone is None:
            findings.append({
                "severity": "BLOCKER",
                "type": "timestamp_without_timezone",
                "event_id": event_id,
            })
            continue
        if zone == "-00:00":
            findings.append({
                "severity": "BLOCKER",
                "type": "timestamp_unknown_offset",
                "event_id": event_id,
            })
            continue
        try:
            normalized = ts[:-1] + "+00:00" if zone == "Z" else ts
            parsed = datetime.fromisoformat(normalized)
            offset = parsed.utcoffset()
            if parsed.tzinfo is None or offset is None:
                findings.append({
                    "severity": "BLOCKER",
                    "type": "timestamp_without_timezone",
                    "event_id": event_id,
                })
                continue
            if offset.total_seconds() != 0:
                findings.append({
                    "severity": "BLOCKER",
                    "type": "timestamp_not_utc",
                    "event_id": event_id,
                })
                continue
            timestamps.append((parsed.astimezone(timezone.utc), index, event))
        except (TypeError, ValueError, OverflowError):
            findings.append({
                "severity": "BLOCKER",
                "type": "invalid_timestamp",
                "event_id": event_id,
            })

    for (earlier, _, earlier_event), (later, _, later_event) in zip(
        timestamps, timestamps[1:]
    ):
        if later < earlier:
            findings.append({
                "severity": "BLOCKER",
                "type": "non_monotonic_event_time",
                "event_ids": [
                    earlier_event.get("event_id"),
                    later_event.get("event_id"),
                ],
            })

    first_access = next(
        (index for index, event in enumerate(events)
         if event.get("event_type") in OUTCOME_ACCESS),
        None,
    )
    prereg_indices = [
        index for index, event in enumerate(events)
        if event.get("event_type") in PREREG_EVENTS
    ]
    if first_access is None:
        findings.append({
            "severity": "WARNING",
            "type": "no_outcome_access_event_recorded",
        })
    elif not prereg_indices or min(prereg_indices) > first_access:
        findings.append({
            "severity": "BLOCKER",
            "type": "outcome_access_before_preregistration",
        })
    else:
        for index, event in enumerate(events):
            if index > first_access and event.get("event_type") in ADAPTIVE_CHANGES:
                findings.append({
                    "severity": "EXPLORATORY_ONLY",
                    "type": "post_outcome_adaptation",
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                })

    blockers = [item for item in findings if item["severity"] == "BLOCKER"]
    state = (
        "BLOCKED"
        if integrity["state"] != "PASS" or blockers
        else "REVIEW_REQUIRED"
        if findings
        else "PASS"
    )
    return {
        "state": state,
        "ledger_integrity": integrity["state"],
        "events": len(events),
        "first_outcome_access_index": first_access,
        "findings": findings,
        "interpretation": (
            "A hash-valid ledger is not proof that every search action was logged. "
            "Post-outcome adaptations are exploratory and cannot be retroactively "
            "preregistered. Timestamps must be explicit UTC instants; unknown "
            "offsets and local/non-UTC offsets are blocked."
        ),
    }
