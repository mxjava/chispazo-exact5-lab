"""V2 temporal eligibility gate for physical evidence.

This module is deliberately separate from V1. It does not authenticate signatures,
custodians, trusted clocks, hashes, metrology or physical continuity. Those must be
verified against primary records by an independent process.
"""
from __future__ import annotations

import csv
import math
from collections import defaultdict
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

DRAW_TIMEZONE = ZoneInfo("America/Mexico_City")

V2_REQUIRED_COLUMNS = (
    "source_contest_id", "target_contest_id", "contest_id", "draw_date",
    "modality", "draw_close_at", "target_draw_close_at", "target_draw_at", "sphere_set_id",
    "set_assigned_at", "sphere_type", "machine_id", "machine_model",
    "sphere_id", "printed_number", "mass_value", "mass_unit", "measurement_at",
    "measurement_resolution", "scale_id", "calibration_valid_from",
    "calibration_valid_to", "calibration_certificate_sha256",
    "mapping_valid_from", "mapping_valid_to", "source_draw_at",
    "source_document_sha256", "source_document_ref", "source_signed_at",
    "source_signer_id", "source_signature_ref", "evidence_available_at",
    "custody_received_at", "custodian_id", "custodian_role",
    "custody_receipt_ref", "custody_receipt_sha256", "trusted_timestamp_ref",
)

def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: missing timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field}: invalid ISO-8601 timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field}: timezone offset required")
    return result.astimezone(timezone.utc)


def evaluate_temporal_eligibility(
    rows: Iterable[Mapping[str, Any]],
    *,
    verified_custody_refs: set[str] | None = None,
    verified_timestamp_refs: set[str] | None = None,
    verified_source_refs: set[str] | None = None,
    verified_continuity_targets: set[str] | None = None,
) -> dict[str, Any]:
    """Classify each target independently; missing external attestations fail closed.

    The verification sets must be populated by an independent verifier, not from
    caller-supplied booleans in the CSV. An empty/omitted set means unverified.
    """
    materialized = list(rows)
    if not materialized:
        return {"status": "EMPTY", "targets": {}, "row_count": 0}
    missing = sorted(set(V2_REQUIRED_COLUMNS) - set(materialized[0]))
    if missing:
        raise ValueError("missing required columns: " + ", ".join(missing))

    custody = verified_custody_refs or set()
    timestamps = verified_timestamp_refs or set()
    sources = verified_source_refs or set()
    continuity = verified_continuity_targets or set()
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in materialized:
        target = str(row.get("target_contest_id", "")).strip()
        if not target.isdecimal() or int(target) <= 0:
            raise ValueError("target_contest_id: positive contest ID required")
        target = str(int(target))
        grouped[target].append(row)

    results: dict[str, dict[str, Any]] = {}
    for target, group in sorted(grouped.items()):
        reasons: set[str] = set()
        closes: set[datetime] = set()
        source_contests: set[str] = set()
        modalities: set[str] = set()
        sphere_ids: set[str] = set()
        printed_numbers: set[int] = set()
        set_ids: set[str] = set()
        machine_ids: set[str] = set()
        target_draws: set[datetime] = set()
        assignments: set[datetime] = set()
        source_closes: set[datetime] = set()
        source_draws: set[datetime] = set()
        sphere_types: set[str] = set()
        machine_models: set[str] = set()
        scales: set[str] = set()
        source_refs: set[str] = set()
        source_hashes: set[str] = set()
        custody_refs: set[str] = set()
        custody_hashes: set[str] = set()
        calibration_hashes: set[str] = set()
        signature_refs: set[str] = set()
        signer_ids: set[str] = set()
        timestamp_refs: set[str] = set()
        for row in group:
            try:
                close = _parse_time(row["target_draw_close_at"], "target_draw_close_at")
                available = _parse_time(row["evidence_available_at"], "evidence_available_at")
                received = _parse_time(row["custody_received_at"], "custody_received_at")
                measurement = _parse_time(row["measurement_at"], "measurement_at")
                source_close = _parse_time(row["draw_close_at"], "draw_close_at")
                source_draw = _parse_time(row["source_draw_at"], "source_draw_at")
                source_draw_local_date = source_draw.astimezone(DRAW_TIMEZONE).date().isoformat()
                declared_date_raw = row["draw_date"]
                if not isinstance(declared_date_raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", declared_date_raw.strip()):
                    reasons.add("INVALID_SOURCE_DRAW_DATE")
                    declared_draw_date = ""
                else:
                    try:
                        declared_draw_date = date.fromisoformat(declared_date_raw.strip()).isoformat()
                    except ValueError:
                        reasons.add("INVALID_SOURCE_DRAW_DATE")
                        declared_draw_date = ""
                contest_id = str(row["contest_id"]).strip()
                source_contest_id = str(row["source_contest_id"]).strip()
                if (not contest_id.isdecimal() or int(contest_id) <= 0
                        or not source_contest_id.isdecimal() or int(source_contest_id) <= 0):
                    reasons.add("INVALID_SOURCE_CONTEST_ID")
                elif int(contest_id) != int(source_contest_id):
                    reasons.add("SOURCE_CONTEST_ID_MISMATCH")
                if declared_draw_date and declared_draw_date != source_draw_local_date:
                    reasons.add("SOURCE_DRAW_DATE_MISMATCH")
                target_draw = _parse_time(row["target_draw_at"], "target_draw_at")
                assignment = _parse_time(row["set_assigned_at"], "set_assigned_at")
                signed = _parse_time(row["source_signed_at"], "source_signed_at")
                closes.add(close)
                target_draws.add(target_draw)
                assignments.add(assignment)
                source_closes.add(source_close)
                source_draws.add(source_draw)
                for identity_field in ("sphere_type", "machine_model", "scale_id", "sphere_id", "sphere_set_id", "machine_id"):
                    identity_value = row[identity_field]
                    if not isinstance(identity_value, str) or not identity_value.strip():
                        reasons.add("INVALID_PHYSICAL_IDENTITY")
                sphere_types.add(str(row["sphere_type"]).strip())
                machine_models.add(str(row["machine_model"]).strip())
                scales.add(str(row["scale_id"]).strip())
                source_refs.add(str(row["source_document_ref"]).strip())
                source_hashes.add(str(row["source_document_sha256"]).strip().lower())
                custody_refs.add(str(row["custody_receipt_ref"]).strip())
                custody_hashes.add(str(row["custody_receipt_sha256"]).strip().lower())
                calibration_hashes.add(str(row["calibration_certificate_sha256"]).strip().lower())
                signature_refs.add(str(row["source_signature_ref"]).strip())
                signer_ids.add(str(row["source_signer_id"]).strip())
                timestamp_refs.add(str(row["trusted_timestamp_ref"]).strip())
                source_contests.add(str(row["source_contest_id"]).strip())
                modalities.add(str(row["modality"]).strip().upper())
                sphere_ids.add(str(row["sphere_id"]).strip())
                set_ids.add(str(row["sphere_set_id"]).strip())
                machine_ids.add(str(row["machine_id"]).strip())
                try:
                    printed_numbers.add(int(str(row["printed_number"]).strip()))
                except ValueError:
                    reasons.add("INVALID_PRINTED_NUMBER")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(row["source_document_sha256"]).strip()):
                    reasons.add("INVALID_SOURCE_SHA256")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(row["custody_receipt_sha256"]).strip()):
                    reasons.add("INVALID_CUSTODY_RECEIPT_SHA256")
                mapping_start = _parse_time(row["mapping_valid_from"], "mapping_valid_from")
                mapping_end = _parse_time(row["mapping_valid_to"], "mapping_valid_to")
                calibration_start = _parse_time(row["calibration_valid_from"], "calibration_valid_from")
                calibration_end = _parse_time(row["calibration_valid_to"], "calibration_valid_to")
                if mapping_start >= mapping_end or not (mapping_start <= assignment <= target_draw <= mapping_end):
                    reasons.add("MAPPING_NOT_VALID_AT_TARGET_DRAW")
                if calibration_start >= calibration_end or not (calibration_start <= measurement <= calibration_end):
                    reasons.add("CALIBRATION_NOT_VALID_AT_MEASUREMENT")
                if available >= close or received >= close:
                    reasons.add("EVIDENCE_NOT_AVAILABLE_PRE_CLOSE")
                if source_draw < source_close:
                    reasons.add("SOURCE_DRAW_PRECEDES_SOURCE_CLOSE")
                if measurement < source_close:
                    reasons.add("MEASUREMENT_PRECEDES_SOURCE_CLOSE")
                if measurement > source_draw:
                    reasons.add("MEASUREMENT_AFTER_SOURCE_DRAW")
                if signed < measurement:
                    reasons.add("SOURCE_SIGNED_PRECEDES_MEASUREMENT")
                if signed > source_draw:
                    reasons.add("SOURCE_SIGNED_AFTER_SOURCE_DRAW")
                if not (assignment <= source_close <= measurement <= source_draw < close):
                    reasons.add("BROKEN_EVIDENCE_TEMPORAL_ORDER")
                if not (measurement <= signed <= source_draw):
                    reasons.add("BROKEN_SOURCE_SIGNATURE_TEMPORAL_ORDER")
                if not (signed <= available <= received < close):
                    reasons.add("BROKEN_EVIDENCE_AVAILABILITY_ORDER")
                if signed > available:
                    reasons.add("SOURCE_SIGNED_AFTER_EVIDENCE_AVAILABLE")
                try:
                    mass = float(str(row["mass_value"]).strip())
                    resolution = float(str(row["measurement_resolution"]).strip())
                    if not math.isfinite(mass) or mass <= 0 or not math.isfinite(resolution) or resolution <= 0:
                        reasons.add("INVALID_MASS_OR_RESOLUTION")
                except (ValueError, TypeError):
                    reasons.add("INVALID_MASS_OR_RESOLUTION")
                if str(row["mass_unit"]).strip().lower() != "g":
                    reasons.add("UNSUPPORTED_MASS_UNIT")
                if not re.fullmatch(r"[0-9a-fA-F]{64}", str(row["calibration_certificate_sha256"]).strip()):
                    reasons.add("INVALID_CALIBRATION_SHA256")
                if not str(row["source_signature_ref"]).strip() or not str(row["source_signer_id"]).strip():
                    reasons.add("SOURCE_SIGNATURE_MISSING")
                if not str(row["custodian_id"]).strip() or not str(row["custodian_role"]).strip():
                    reasons.add("CUSTODIAN_IDENTITY_MISSING")
                if not str(row["custody_receipt_ref"]).strip():
                    reasons.add("CUSTODY_RECEIPT_MISSING")
                if not str(row["trusted_timestamp_ref"]).strip():
                    reasons.add("TRUSTED_TIMESTAMP_MISSING")
                if not str(row["source_document_ref"]).strip():
                    reasons.add("PRIMARY_SOURCE_MISSING")
            except (ValueError, TypeError, KeyError):
                reasons.add("INVALID_OR_MISSING_TIMESTAMP_OR_PROVENANCE")
        if len(closes) != 1:
            reasons.add("TARGET_CLOSE_CONFLICT")
        if len(target_draws) != 1 or (closes and target_draws and next(iter(target_draws)) <= next(iter(closes))):
            reasons.add("TARGET_DRAW_TIME_CONFLICT")
        if len(assignments) != 1 or len(source_closes) != 1:
            reasons.add("SOURCE_ASSIGNMENT_OR_CLOSE_CONFLICT")
        if len(source_draws) != 1:
            reasons.add("SOURCE_DRAW_TIME_CONFLICT")
        if len(sphere_types) != 1 or "" in sphere_types or len(machine_models) != 1 or "" in machine_models or len(scales) != 1 or "" in scales:
            reasons.add("METROLOGY_CONFIGURATION_CONFLICT")
        if any(len(values) != 1 or "" in values for values in (
            source_refs, source_hashes, custody_refs, custody_hashes,
            calibration_hashes, signature_refs, signer_ids, timestamp_refs
        )):
            reasons.add("EVIDENCE_DOCUMENT_SET_CONFLICT")
        if len(source_contests) != 1:
            reasons.add("SOURCE_CONTEST_CONFLICT")
        if len(group) != 28 or len(sphere_ids) != 28 or printed_numbers != set(range(1, 29)):
            reasons.add("INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET")
        if len(set_ids) != 1 or "" in set_ids or len(machine_ids) != 1 or "" in machine_ids:
            reasons.add("PHYSICAL_SET_OR_MACHINE_CONFLICT")
        if modalities != {"CLASSIC"}:
            reasons.add("MODALITY_NOT_VERIFIED_CLASSIC")
        if not all(str(row.get("custody_receipt_ref", "")) in custody for row in group):
            reasons.add("CUSTODY_NOT_INDEPENDENTLY_VERIFIED")
        if not all(str(row.get("trusted_timestamp_ref", "")) in timestamps for row in group):
            reasons.add("TIMESTAMP_NOT_INDEPENDENTLY_VERIFIED")
        if not all(str(row.get("source_document_ref", "")) in sources for row in group):
            reasons.add("SOURCE_NOT_INDEPENDENTLY_VERIFIED")
        if target not in continuity:
            reasons.add("PHYSICAL_CONTINUITY_NOT_VERIFIED")

        if "EVIDENCE_NOT_AVAILABLE_PRE_CLOSE" in reasons:
            classification = "INELIGIBLE_POST_CLOSE"
        elif any(reason in reasons for reason in (
            "INVALID_OR_MISSING_TIMESTAMP_OR_PROVENANCE", "INVALID_SOURCE_SHA256",
            "INVALID_CUSTODY_RECEIPT_SHA256", "INVALID_CALIBRATION_SHA256",
            "CUSTODY_NOT_INDEPENDENTLY_VERIFIED", "TIMESTAMP_NOT_INDEPENDENTLY_VERIFIED",
            "SOURCE_NOT_INDEPENDENTLY_VERIFIED", "CUSTODIAN_IDENTITY_MISSING",
            "CUSTODY_RECEIPT_MISSING", "TRUSTED_TIMESTAMP_MISSING",
            "PRIMARY_SOURCE_MISSING", "SOURCE_SIGNATURE_MISSING",
            "SOURCE_SIGNED_AFTER_EVIDENCE_AVAILABLE"
        )):
            classification = "BLOCKED_PROVENANCE"
        elif any(reason in reasons for reason in (
            "PHYSICAL_CONTINUITY_NOT_VERIFIED", "SOURCE_CONTEST_CONFLICT",
            "INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET", "PHYSICAL_SET_OR_MACHINE_CONFLICT",
            "MAPPING_NOT_VALID_AT_TARGET_DRAW", "MODALITY_NOT_VERIFIED_CLASSIC",
            "BROKEN_EVIDENCE_TEMPORAL_ORDER", "MEASUREMENT_PRECEDES_SOURCE_CLOSE",
            "MEASUREMENT_AFTER_SOURCE_DRAW", "SOURCE_SIGNED_PRECEDES_MEASUREMENT",
            "SOURCE_SIGNED_AFTER_SOURCE_DRAW", "BROKEN_SOURCE_SIGNATURE_TEMPORAL_ORDER",
            "BROKEN_EVIDENCE_AVAILABILITY_ORDER", "SOURCE_DRAW_PRECEDES_SOURCE_CLOSE", "TARGET_DRAW_TIME_CONFLICT",
            "SOURCE_ASSIGNMENT_OR_CLOSE_CONFLICT", "SOURCE_DRAW_TIME_CONFLICT",
            "INVALID_SOURCE_CONTEST_ID", "SOURCE_CONTEST_ID_MISMATCH",
            "SOURCE_DRAW_DATE_MISMATCH", "INVALID_SOURCE_DRAW_DATE",
            "INVALID_PHYSICAL_IDENTITY", "METROLOGY_CONFIGURATION_CONFLICT",
            "EVIDENCE_DOCUMENT_SET_CONFLICT"
        )):
            classification = "BLOCKED_CONTINUITY"
        elif reasons:
            classification = "BLOCKED_PROVENANCE"
        else:
            classification = "ELIGIBLE_PRE_CLOSE"
        results[target] = {
            "predictive_eligibility": classification,
            "reasons": sorted(reasons),
            "source_contests": sorted(source_contests),
            "row_count": len(group),
        }
    return {
        "status": "ELIGIBILITY_REVIEWED",
        "targets": results,
        "row_count": len(materialized),
        "scope_warning": (
            "Temporal gate only. ELIGIBLE_PRE_CLOSE means external attestations were "
            "declared verified by the independent verifier; it is not a physical-bias "
            "finding or a predictive-edge claim."
        ),
    }


def evaluate_temporal_csv(path: str | Path, **verification: set[str]) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        missing = sorted(set(V2_REQUIRED_COLUMNS) - set(reader.fieldnames))
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        return evaluate_temporal_eligibility(reader, **verification)
