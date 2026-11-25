"""Cross-contest audit of physical sphere-to-number mapping intervals.

Structural consistency only: this does not authenticate source documents,
clocks, signatures, or the physical identity asserted by a supplied sphere ID.
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


def _overlap_conflicts(
    groups: Mapping[tuple[str, str], list[dict[str, Any]]],
    differs: str,
    quarantined: dict[str, set[str]],
) -> int:
    conflicts = 0
    for entries in groups.values():
        entries.sort(key=lambda item: (item["start"], item["end"], item["contest"]))
        for index, left in enumerate(entries):
            for right in entries[index + 1:]:
                if right["start"] > left["end"]:
                    break
                if left[differs] != right[differs]:
                    quarantined[left["contest"]].add("Q_REMAP")
                    quarantined[right["contest"]].add("Q_REMAP")
                    conflicts += 1
    return conflicts


def audit_mapping_history(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Check both directions of the sphere-ID <-> printed-number mapping.

    Required fields: contest_id, sphere_set_id, sphere_id, printed_number,
    mapping_valid_from, mapping_valid_to, set_assigned_at, draw_at.
    Validity intervals are closed at both ends for conservative overlap checks.
    """
    by_sphere: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    by_number: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    quarantined: dict[str, set[str]] = defaultdict(set)
    row_count = 0

    for index, raw in enumerate(rows, start=2):
        row_count += 1
        contest_raw = str(raw.get("contest_id", "")).strip()
        if not contest_raw.isdecimal() or int(contest_raw) <= 0:
            quarantined[f"row:{index}"].add("Q_REMAP")
            continue
        contest = str(int(contest_raw))
        try:
            set_id = str(raw["sphere_set_id"]).strip()
            sphere_id = str(raw["sphere_id"]).strip()
            number_raw = str(raw["printed_number"]).strip()
            if not set_id or not sphere_id:
                raise ValueError("missing sphere identity")
            if not number_raw.isdecimal() or not 1 <= int(number_raw) <= 28:
                raise ValueError("invalid printed number")
            start = _aware_utc(raw["mapping_valid_from"], "mapping_valid_from")
            end = _aware_utc(raw["mapping_valid_to"], "mapping_valid_to")
            assigned = _aware_utc(raw["set_assigned_at"], "set_assigned_at")
            draw = _aware_utc(raw["draw_at"], "draw_at")
            if start > end or not (start <= assigned <= end) or not (start <= draw <= end) or assigned > draw:
                quarantined[contest].add("Q_REMAP")
                continue
            entry = {
                "contest": contest, "sphere": sphere_id, "number": int(number_raw),
                "start": start, "end": end,
            }
            by_sphere[(set_id, sphere_id)].append(entry)
            by_number[(set_id, str(int(number_raw)))].append(entry)
        except (KeyError, TypeError, ValueError):
            quarantined[contest].add("Q_REMAP")

    forward_conflicts = _overlap_conflicts(by_sphere, "number", quarantined)
    inverse_conflicts = _overlap_conflicts(by_number, "sphere", quarantined)
    return {
        "status": "MAPPING_CONFLICTS" if quarantined else "MAPPING_HISTORY_CLEAR",
        "row_count": row_count,
        "sphere_identity_count": len(by_sphere),
        "number_identity_count": len(by_number),
        "forward_conflicts": forward_conflicts,
        "inverse_conflicts": inverse_conflicts,
        "overlapping_conflicts": forward_conflicts + inverse_conflicts,
        "quarantined": {key: sorted(value) for key, value in sorted(quarantined.items())},
        "scope_warning": (
            "Structural interval audit only; it does not authenticate sphere IDs, "
            "mapping records, timestamps, signatures, or source documents."
        ),
    }
