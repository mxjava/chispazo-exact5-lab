"""Cross-contest audit of physical sphere-to-number mapping intervals.

This is a structural consistency check only. It cannot authenticate source
documents, clocks, or the physical identity asserted by a supplied sphere ID.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


def _aware_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}: timezone offset is required")
    return parsed.astimezone(timezone.utc)


def audit_mapping_history(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Find invalid intervals and overlapping contradictory mappings.

    Required fields: contest_id, sphere_set_id, sphere_id, printed_number,
    mapping_valid_from, mapping_valid_to, set_assigned_at. Intervals are
    closed at both ends for conservative overlap detection.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    quarantined: dict[str, set[str]] = defaultdict(set)
    row_count = 0

    for index, raw in enumerate(rows, start=2):
        row_count += 1
        contest = str(raw.get("contest_id", "")).strip() or f"row:{index}"
        try:
            set_id = str(raw["sphere_set_id"]).strip()
            sphere_id = str(raw["sphere_id"]).strip()
            number_raw = str(raw["printed_number"]).strip()
            if not contest or not set_id or not sphere_id:
                raise ValueError("missing identity")
            if not number_raw.isdecimal() or not 1 <= int(number_raw) <= 28:
                raise ValueError("invalid printed number")
            start = _aware_utc(raw["mapping_valid_from"], "mapping_valid_from")
            end = _aware_utc(raw["mapping_valid_to"], "mapping_valid_to")
            assigned = _aware_utc(raw["set_assigned_at"], "set_assigned_at")
            if start > end or not (start <= assigned <= end):
                quarantined[contest].add("Q_REMAP")
                continue
            groups[(set_id, sphere_id)].append({
                "contest": contest, "number": int(number_raw),
                "start": start, "end": end,
            })
        except (KeyError, TypeError, ValueError):
            quarantined[contest].add("Q_REMAP")

    conflicts = 0
    for identity, entries in groups.items():
        entries.sort(key=lambda item: (item["start"], item["end"], item["contest"]))
        for i, left in enumerate(entries):
            for right in entries[i + 1:]:
                if right["start"] > left["end"]:
                    break
                if left["number"] != right["number"]:
                    quarantined[left["contest"]].add("Q_REMAP")
                    quarantined[right["contest"]].add("Q_REMAP")
                    conflicts += 1

    return {
        "status": "MAPPING_CONFLICTS" if quarantined else "MAPPING_HISTORY_CLEAR",
        "row_count": row_count,
        "sphere_identity_count": len(groups),
        "overlapping_conflicts": conflicts,
        "quarantined": {key: sorted(value) for key, value in sorted(quarantined.items())},
        "scope_warning": (
            "Structural interval audit only; it does not authenticate sphere IDs, "
            "mapping records, timestamps, signatures, or source documents."
        ),
    }
