"""Strict, non-predictive intake validation for primary physical sphere records.

This module validates provenance and measurement structure only. It does not
estimate extraction bias, rank numbers, or certify that supplied timestamps,
signatures, calibration certificates, or source hashes are authentic.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Iterable, Mapping, Any

from .mapping_history import audit_mapping_history

HEX64 = re.compile(r"[0-9a-f]{64}")
MASS_LIMITS = {
    "smartballs": (4.25, 5.25, 0.30),
    "ping-pong": (2.30, 3.00, 0.15),
}
DRAW_TIMEZONE = ZoneInfo("America/Mexico_City")
REQUIRED_COLUMNS = (
    "contest_id", "draw_date", "modality", "draw_close_at",
    "sphere_set_id", "set_assigned_at", "sphere_type", "machine_id",
    "machine_model", "sphere_id", "printed_number", "mass_value",
    "mass_unit", "measurement_at", "measurement_resolution",
    "scale_id", "calibration_valid_from", "calibration_valid_to",
    "calibration_certificate_sha256", "mapping_valid_from", "mapping_valid_to", "draw_at",
    "source_document_sha256", "source_document_ref",
)
QUARANTINE_CODES = {
    "Q_SOURCE_UNVERIFIED", "Q_CONTEST_LINK", "Q_MAPPING", "Q_TIME",
    "Q_METROLOGY", "Q_INCOMPLETE_SET", "Q_REMAP", "Q_CONFLICT",
}


def _timestamp(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}: timezone offset is required")
    return parsed.astimezone(timezone.utc)


def _positive_float(value: str, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}: must be numeric") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field}: must be finite and positive")
    return number


def _positive_int(value: str, field: str) -> int:
    if not isinstance(value, str) or not value.isdecimal():
        raise ValueError(f"{field}: must be a positive integer")
    number = int(value)
    if number <= 0:
        raise ValueError(f"{field}: must be a positive integer")
    return number


def validate_physical_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate long-form rows; return per-contest quarantine labels and metrics."""
    materialized = list(rows)
    if not materialized:
        return {"status": "EMPTY", "contest_count": 0, "usable_contests": [],
                "quarantined": {}, "row_count": 0}

    missing = sorted(set(REQUIRED_COLUMNS) - set(materialized[0].keys()))
    if missing:
        raise ValueError("missing required columns: " + ", ".join(missing))

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    row_errors: dict[int, set[str]] = defaultdict(set)
    masses_by_contest: dict[int, list[float]] = defaultdict(list)
    for index, raw in enumerate(materialized, start=2):
        try:
            contest = _positive_int(str(raw.get("contest_id", "")), "contest_id")
        except ValueError:
            row_errors[-index].add("Q_CONTEST_LINK")
            continue
        row = dict(raw)
        grouped[contest].append(row)
        try:
            if row["modality"] not in {"CLASSIC", "TRES"}:
                raise ValueError("unknown modality")
            if not str(row["draw_date"]).strip() or not str(row["source_document_ref"]).strip():
                row_errors[contest].add("Q_CONTEST_LINK")
            draw_date = str(row["draw_date"])
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", draw_date):
                row_errors[contest].add("Q_CONTEST_LINK")
            else:
                try:
                    datetime.strptime(draw_date, "%Y-%m-%d")
                except ValueError:
                    row_errors[contest].add("Q_CONTEST_LINK")
            for field in ("source_document_sha256", "calibration_certificate_sha256"):
                if not HEX64.fullmatch(str(row[field])):
                    row_errors[contest].add("Q_SOURCE_UNVERIFIED" if field == "source_document_sha256" else "Q_METROLOGY")
            close = _timestamp(str(row["draw_close_at"]), "draw_close_at")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", draw_date):
                if close.astimezone(DRAW_TIMEZONE).date().isoformat() != draw_date:
                    row_errors[contest].add("Q_CONTEST_LINK")
            assigned = _timestamp(str(row["set_assigned_at"]), "set_assigned_at")
            measured = _timestamp(str(row["measurement_at"]), "measurement_at")
            mapped = _timestamp(str(row["mapping_valid_from"]), "mapping_valid_from")
            mapped_to = _timestamp(str(row["mapping_valid_to"]), "mapping_valid_to")
            draw_at = _timestamp(str(row["draw_at"]), "draw_at")
            cal_from = _timestamp(str(row["calibration_valid_from"]), "calibration_valid_from")
            cal_to = _timestamp(str(row["calibration_valid_to"]), "calibration_valid_to")
            if not (assigned < close and measured < close and mapped < close and close < draw_at):
                row_errors[contest].add("Q_TIME")
            if not (mapped <= assigned <= mapped_to and mapped <= draw_at <= mapped_to):
                row_errors[contest].add("Q_REMAP")
            if draw_at.astimezone(DRAW_TIMEZONE).date().isoformat() != draw_date:
                row_errors[contest].add("Q_CONTEST_LINK")
            if not (cal_from <= measured <= cal_to):
                row_errors[contest].add("Q_METROLOGY")
            if not all(str(row[k]).strip() for k in ("sphere_set_id", "sphere_type", "machine_id", "machine_model", "sphere_id", "scale_id")):
                row_errors[contest].add("Q_SOURCE_UNVERIFIED")
            if str(row["mass_unit"]).lower() != "g":
                row_errors[contest].add("Q_METROLOGY")
            sphere_type = str(row["sphere_type"]).strip().casefold()
            if sphere_type not in MASS_LIMITS:
                row_errors[contest].add("Q_METROLOGY")
            mass = _positive_float(str(row["mass_value"]), "mass_value")
            masses_by_contest[contest].append(mass)
            _positive_float(str(row["measurement_resolution"]), "measurement_resolution")
            number = _positive_int(str(row["printed_number"]), "printed_number")
            if number > 28:
                row_errors[contest].add("Q_MAPPING")
        except (ValueError, TypeError, KeyError):
            row_errors[contest].add("Q_METROLOGY")

    quarantined: dict[str, list[str]] = {}
    usable: list[int] = []
    for contest, group in sorted(grouped.items()):
        labels = row_errors[contest]
        if len(group) != 28:
            labels.add("Q_INCOMPLETE_SET")
        numbers: list[int] = []
        sphere_ids: list[str] = []
        identity_fields = ("modality", "draw_date", "draw_close_at", "sphere_set_id",
                           "set_assigned_at", "sphere_type", "machine_id", "machine_model",
                           "scale_id", "measurement_resolution", "calibration_valid_from",
                           "calibration_valid_to", "draw_at",
                           "source_document_sha256", "source_document_ref",
                           "calibration_certificate_sha256")
        for row in group:
            try:
                numbers.append(int(row["printed_number"]))
            except (ValueError, TypeError, KeyError):
                pass
            sphere_ids.append(str(row.get("sphere_id", "")))
        if sorted(numbers) != list(range(1, 29)) or len(numbers) != len(set(numbers)):
            labels.add("Q_MAPPING")
        if len(sphere_ids) != len(set(sphere_ids)) or "" in sphere_ids:
            labels.add("Q_MAPPING")
        for field in identity_fields:
            values = {str(row.get(field, "")) for row in group}
            if len(values) != 1:
                labels.add("Q_CONFLICT")
        sphere_types = {str(row.get("sphere_type", "")).strip().casefold() for row in group}
        if len(sphere_types) == 1:
            sphere_type = next(iter(sphere_types))
            limits = MASS_LIMITS.get(sphere_type)
            masses = masses_by_contest[contest]
            if limits is None:
                labels.add("Q_METROLOGY")
            elif len(masses) == 28:
                lower, upper, max_spread = limits
                if any(mass < lower or mass > upper for mass in masses):
                    labels.add("Q_METROLOGY")
                if max(masses) - min(masses) > max_spread:
                    labels.add("Q_METROLOGY")
        if labels:
            quarantined[str(contest)] = sorted(labels)
        else:
            usable.append(contest)

    for key, labels in row_errors.items():
        if key < 0:
            quarantined[f"row:{-key}"] = sorted(labels)

    mapping_report = audit_mapping_history(materialized)
    for contest_key, codes in mapping_report["quarantined"].items():
        quarantined[contest_key] = sorted(set(quarantined.get(contest_key, [])) | set(codes))
        try:
            invalidated_contest = int(contest_key)
            usable = [value for value in usable if value != invalidated_contest]
        except ValueError:
            pass
    return {
        "status": "VALIDATED_WITH_QUARANTINE" if quarantined else "STRUCTURE_VALID",
        "contest_count": len(grouped),
        "row_count": len(materialized),
        "mapping_history_status": mapping_report["status"],
        "mapping_history_conflicts": mapping_report["overlapping_conflicts"],
        "usable_contests": usable,
        "quarantined": quarantined,
        "scope_warning": "Structural validation only; source authenticity, clock trust, signatures and predictive value are not established.",
    }


def validate_physical_csv(path: str | Path) -> dict[str, Any]:
    """Read a UTF-8 CSV and validate its rows without modifying the source."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        missing = sorted(set(REQUIRED_COLUMNS) - set(reader.fieldnames))
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        return validate_physical_rows(reader)


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
