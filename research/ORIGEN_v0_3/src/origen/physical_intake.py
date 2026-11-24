"""Strict, non-predictive intake validation for primary physical sphere records.

This module validates provenance and measurement structure only. It does not
estimate extraction bias, rank numbers, or certify that supplied timestamps,
signatures, calibration certificates, or source hashes are authentic.
"""
from __future__ import annotations

import csv
import hashlib
from decimal import Decimal, InvalidOperation, localcontext
import re
from collections import defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Iterable, Mapping, Any

from .mapping_history import audit_mapping_history

HEX64 = re.compile(r"[0-9a-f]{64}")
MASS_LIMITS = {
    "smartballs": (Decimal("4.25"), Decimal("5.25"), Decimal("0.30")),
    "ping-pong": (Decimal("2.30"), Decimal("3.00"), Decimal("0.15")),
}
DRAW_TIMEZONE = ZoneInfo("America/Mexico_City")
MAX_PHYSICAL_INTAKE_ROWS = 28_000
OFFICIAL_SALES_CLOSE_SLOTS = {
    "TRES": (15, 0, 0, 0),
    "CLASSIC": (21, 0, 0, 0),
}
REQUIRED_COLUMNS = (
    "contest_id", "draw_date", "modality", "draw_close_at",
    "sphere_set_id", "set_assigned_at", "sphere_type", "machine_id",
    "machine_model", "sphere_id", "printed_number", "mass_value",
    "mass_unit", "measurement_at", "measurement_resolution",
    "scale_id", "calibration_valid_from", "calibration_valid_to",
    "calibration_certificate_sha256", "mapping_valid_from", "mapping_valid_to", "draw_at",
    "source_document_sha256", "source_document_ref",
)

# V1 CSV input is single-line/scalar: bound header, each physical record,
# decoded field payload, and total bytes before CSV objects are materialized.
MAX_PHYSICAL_CSV_ROW_TEXT_BYTES = 32_768
MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES = 64_000_000
MAX_PHYSICAL_CSV_HEADER_BYTES = 4_096
MAX_PHYSICAL_CSV_RECORD_BYTES = (
    2 * MAX_PHYSICAL_CSV_ROW_TEXT_BYTES + 4 * len(REQUIRED_COLUMNS) + 4
)

QUARANTINE_CODES = {
    "Q_SOURCE_UNVERIFIED", "Q_CONTEST_LINK", "Q_MAPPING", "Q_TIME",
    "Q_METROLOGY", "Q_INCOMPLETE_SET", "Q_REMAP", "Q_CONFLICT",
}


_RFC3339_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})\\Z"
)


def _timestamp(value: str, field: str) -> datetime:
    # The CSV is a provenance boundary: accept one canonical RFC3339 form,
    # not every relaxed spelling that datetime.fromisoformat happens to parse.
    if type(value) is not str or not _RFC3339_TIMESTAMP.fullmatch(value):
        raise ValueError(f"{field}: must be canonical RFC3339 with an explicit offset")
    # RFC3339 -00:00 means the local offset is unknown, not UTC. Treating it
    # as UTC could falsely satisfy the Classic/De las Tres local-time gate.
    if value.endswith("-00:00"):
        raise ValueError(f"{field}: unknown UTC offset -00:00 is not accepted")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field}: invalid RFC3339 calendar timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}: timezone offset is required")
    return parsed.astimezone(timezone.utc)


def _positive_decimal(value: str, field: str) -> Decimal:
    if type(value) is not str:
        raise ValueError(f"{field}: must be exact text")
    # Accept one unambiguous decimal spelling only. Decimal() itself also
    # accepts whitespace, underscores, leading signs and exponent notation;
    # those alternate spellings are not part of the physical CSV contract.
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError(f"{field}: must use canonical unsigned decimal text")
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field}: must be numeric") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field}: must be finite and positive")
    # Bound precision and scale so exact comparisons/subtraction remain
    # deterministic and cannot be affected by ambient Decimal context.
    parts = number.as_tuple()
    if len(parts.digits) > 18 or abs(parts.exponent) > 9:
        raise ValueError(f"{field}: decimal precision or scale exceeds supported bounds")
    return number


def _positive_int(value: str, field: str) -> int:
    if type(value) is not str or not re.fullmatch(r"[0-9]+", value):
        raise ValueError(f"{field}: must be a positive ASCII integer")
    number = int(value)
    if number <= 0:
        raise ValueError(f"{field}: must be a positive integer")
    return number


def _official_sales_close_slot(modality: str, close_at: datetime) -> bool:
    """Require the modality's official Mexico City sales-close slot."""
    expected = OFFICIAL_SALES_CLOSE_SLOTS.get(modality)
    if expected is None:
        return False
    local = close_at.astimezone(DRAW_TIMEZONE)
    return (local.hour, local.minute, local.second, local.microsecond) == expected


def validate_physical_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate source-draw records; target pre-close eligibility is handled by V2."""
    materialized = []
    for row_number, row in enumerate(rows, start=1):
        if row_number > MAX_PHYSICAL_INTAKE_ROWS:
            raise ValueError(
                f"physical intake exceeds maximum {MAX_PHYSICAL_INTAKE_ROWS} rows"
            )
        # Snapshot exact built-in dictionaries as they are yielded; a generator
        # may mutate a previously yielded row before list materialization ends.
        materialized.append(row.copy() if type(row) is dict else row)
    if not materialized:
        return {"status": "EMPTY", "contest_count": 0, "usable_contests": [],
                "quarantined": {}, "row_count": 0}

    if type(materialized[0]) is not dict or any(
        type(key) is not str for key in materialized[0]
    ):
        raise ValueError("rows must be exact built-in dict objects with built-in string keys")
    missing = sorted(set(REQUIRED_COLUMNS) - set(materialized[0]))
    if missing:
        raise ValueError("missing required columns: " + ", ".join(missing))
    unexpected = sorted(set(materialized[0]) - set(REQUIRED_COLUMNS))
    if unexpected:
        raise ValueError("unexpected columns: " + ", ".join(unexpected))

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    mapping_rows: list[dict[str, Any]] = []
    row_errors: dict[int, set[str]] = defaultdict(set)
    masses_by_contest: dict[int, list[Decimal]] = defaultdict(list)
    for index, raw in enumerate(materialized, start=2):
        if type(raw) is not dict or any(type(key) is not str for key in raw):
            row_errors[-index].add("Q_CONTEST_LINK")
            continue
        if set(raw) != set(REQUIRED_COLUMNS):
            row_errors[-index].add("Q_CONTEST_LINK")
            continue
        if any(type(value) is not str for value in raw.values()):
            row_errors[-index].add("Q_SOURCE_UNVERIFIED")
            continue
        try:
            contest = _positive_int(raw.get("contest_id", ""), "contest_id")
        except ValueError:
            row_errors[-index].add("Q_CONTEST_LINK")
            continue
        row = raw
        mapping_rows.append(row)
        grouped[contest].append(row)
        try:
            modality = row["modality"]
            if modality not in {"CLASSIC", "TRES"}:
                raise ValueError("unknown modality")
            if not str(row["draw_date"]).strip() or not str(row["source_document_ref"]).strip():
                row_errors[contest].add("Q_CONTEST_LINK")
            draw_date = row["draw_date"]
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
            close = _timestamp(row["draw_close_at"], "draw_close_at")
            if not _official_sales_close_slot(modality, close):
                row_errors[contest].add("Q_TIME")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", draw_date):
                if close.astimezone(DRAW_TIMEZONE).date().isoformat() != draw_date:
                    row_errors[contest].add("Q_CONTEST_LINK")
            assigned = _timestamp(row["set_assigned_at"], "set_assigned_at")
            measured = _timestamp(row["measurement_at"], "measurement_at")
            mapped = _timestamp(row["mapping_valid_from"], "mapping_valid_from")
            mapped_to = _timestamp(row["mapping_valid_to"], "mapping_valid_to")
            draw_at = _timestamp(row["draw_at"], "draw_at")
            cal_from = _timestamp(row["calibration_valid_from"], "calibration_valid_from")
            cal_to = _timestamp(row["calibration_valid_to"], "calibration_valid_to")
            # SGVO-PRO-05 Rev. 39 closes sales before the weighing activity.
            # This V1 validator checks the source draw's event chronology only;
            # it cannot certify pre-close availability for a later target.
            if not (
                assigned < close and mapped < close and close < draw_at
                and close <= measured <= draw_at
            ):
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
            mass = _positive_decimal(row["mass_value"], "mass_value")
            masses_by_contest[contest].append(mass)
            _positive_decimal(row["measurement_resolution"], "measurement_resolution")
            number = _positive_int(row["printed_number"], "printed_number")
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
                with localcontext() as decimal_context:
                    decimal_context.prec = 40
                    if max(masses) - min(masses) > max_spread:
                        labels.add("Q_METROLOGY")
        if labels:
            quarantined[str(contest)] = sorted(labels)
        else:
            usable.append(contest)

    for key, labels in row_errors.items():
        if key < 0:
            quarantined[f"row:{-key}"] = sorted(labels)

    mapping_report = audit_mapping_history(mapping_rows)
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
        "scope_warning": (
            "V1 validates source-draw structure and event chronology only. SGVO-PRO-05 "
            "weighing occurs after source sales close; this output does not establish "
            "pre-close availability or eligibility for a later target. Use the V2 "
            "source-to-target gate for target availability, custody and continuity. "
            "Source authenticity, clock trust, signatures and predictive value are "
            "not established."
        ),
    }


def validate_physical_csv(path: str | Path) -> dict[str, Any]:
    """Read bounded, single-physical-line CSV records without modifying the source.

    V1 fields are scalar. Multiline CSV cells are rejected so one physical record
    can be bounded before the parser allocates its field strings. The aggregate
    byte limit and row-count limit independently bound total work and memory.
    """
    with Path(path).open("rb") as stream:
        raw_header = stream.readline(MAX_PHYSICAL_CSV_HEADER_BYTES + 1)
        if not raw_header:
            raise ValueError("CSV has no header")
        if len(raw_header) > MAX_PHYSICAL_CSV_HEADER_BYTES:
            raise ValueError(
                f"CSV header exceeds maximum {MAX_PHYSICAL_CSV_HEADER_BYTES} bytes"
            )
        if (
            (raw_header.endswith(b"\r\n") and b"\r" in raw_header[:-2])
            or (not raw_header.endswith(b"\r\n") and b"\r" in raw_header)
        ):
            raise ValueError("CSV header contains an embedded or unsupported carriage return")
        try:
            header_line = raw_header.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("CSV header is not valid UTF-8") from exc
        try:
            headers = next(csv.reader([header_line], strict=True))
        except (csv.Error, StopIteration) as exc:
            raise ValueError("CSV header syntax is invalid") from exc
        if any(
            type(name) is not str or not name or name != name.strip()
            for name in headers
        ):
            raise ValueError("CSV headers must be non-empty canonical strings")
        if len(headers) != len(set(headers)):
            raise ValueError("CSV headers must be unique; duplicate column names are ambiguous")
        missing = sorted(set(REQUIRED_COLUMNS) - set(headers))
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        unexpected = sorted(set(headers) - set(REQUIRED_COLUMNS))
        if unexpected:
            raise ValueError("unexpected columns: " + ", ".join(unexpected))

        total_bytes = len(raw_header)
        if total_bytes > MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES:
            raise ValueError(
                f"CSV input exceeds maximum {MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES} bytes"
            )

        def rows() -> Iterable[dict[str, Any]]:
            nonlocal total_bytes
            while True:
                raw_line = stream.readline(MAX_PHYSICAL_CSV_RECORD_BYTES + 1)
                if not raw_line:
                    return
                if len(raw_line) > MAX_PHYSICAL_CSV_RECORD_BYTES:
                    raise ValueError(
                        f"CSV record exceeds maximum {MAX_PHYSICAL_CSV_RECORD_BYTES} bytes"
                    )
                total_bytes += len(raw_line)
                if total_bytes > MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES:
                    raise ValueError(
                        f"CSV input exceeds maximum {MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES} bytes"
                    )
                if (
                    (raw_line.endswith(b"\r\n") and b"\r" in raw_line[:-2])
                    or (not raw_line.endswith(b"\r\n") and b"\r" in raw_line)
                ):
                    raise ValueError(
                        "CSV record contains an embedded or unsupported carriage return"
                    )
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ValueError("CSV record is not valid UTF-8") from exc
                try:
                    values = next(csv.reader([line], strict=True))
                except StopIteration:
                    continue
                except csv.Error as exc:
                    raise ValueError("CSV record syntax is invalid") from exc
                if not values:
                    continue
                if any(
                    type(value) is str and ("\r" in value or "\n" in value)
                    for value in values
                ):
                    raise ValueError("CSV multiline fields are not supported")
                if len(values) > len(headers):
                    raise ValueError("CSV record has more fields than its header")
                if len(values) < len(headers):
                    values.extend([None] * (len(headers) - len(values)))
                row_text_bytes = 0
                for value in values:
                    if type(value) is str:
                        row_text_bytes += len(value.encode("utf-8"))
                        if row_text_bytes > MAX_PHYSICAL_CSV_ROW_TEXT_BYTES:
                            raise ValueError(
                                f"CSV row text exceeds maximum {MAX_PHYSICAL_CSV_ROW_TEXT_BYTES} bytes"
                            )
                yield dict(zip(headers, values))

        return validate_physical_rows(rows())


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
