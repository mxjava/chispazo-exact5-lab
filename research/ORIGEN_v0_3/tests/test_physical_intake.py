from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from origen.physical_intake import (
    MAX_PHYSICAL_CSV_HEADER_BYTES, MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES,
    MAX_PHYSICAL_CSV_RECORD_BYTES, MAX_PHYSICAL_CSV_ROW_TEXT_BYTES,
    MAX_PHYSICAL_INTAKE_ROWS, REQUIRED_COLUMNS, file_sha256,
    validate_physical_csv, validate_physical_rows,
)


def make_rows():
    rows = []
    for number in range(1, 29):
        rows.append({
            "contest_id": "12300",
            "draw_date": "2026-11-20",
            "modality": "CLASSIC",
            "draw_close_at": "2026-11-20T21:00:00-06:00",
            "draw_at": "2026-11-20T21:10:00-06:00",
            "sphere_set_id": "SET-A",
            "set_assigned_at": "2026-11-20T17:00:00-06:00",
            "sphere_type": "Smartballs",
            "machine_id": "M-01",
            "machine_model": "Model-X",
            "sphere_id": f"SPH-{number:02d}",
            "printed_number": str(number),
            "mass_value": f"{4.70 + number / 1000:.3f}",
            "mass_unit": "g",
            "measurement_at": "2026-11-20T21:05:00-06:00",
            "measurement_resolution": "0.001",
            "scale_id": "SCALE-1",
            "calibration_valid_from": "2026-01-01T00:00:00-06:00",
            "calibration_valid_to": "2026-12-31T23:59:59-06:00",
            "calibration_certificate_sha256": "a" * 64,
            "mapping_valid_from": "2026-11-20T16:00:00-06:00",
            "mapping_valid_to": "2026-11-20T21:30:00-06:00",
            "source_document_sha256": "b" * 64,
            "source_document_ref": "ACTA-12300/TIRA-1",
        })
    return rows


class PhysicalIntakeTests(unittest.TestCase):
    def test_complete_postclose_source_contest_is_structurally_usable(self):
        report = validate_physical_rows(make_rows())
        self.assertEqual(report["usable_contests"], [12300])
        self.assertEqual(report["quarantined"], {})
        self.assertIn("not established", report["scope_warning"])

    def test_missing_sphere_row_quarantines_incomplete_set(self):
        report = validate_physical_rows(make_rows()[:-1])
        self.assertIn("Q_INCOMPLETE_SET", report["quarantined"]["12300"])

    def test_preclose_measurement_is_quarantined(self):
        rows = make_rows()
        rows[0]["measurement_at"] = "2026-11-20T20:59:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_TIME", report["quarantined"]["12300"])

    def test_measurement_after_source_draw_is_quarantined(self):
        rows = make_rows()
        rows[0]["measurement_at"] = "2026-11-20T21:11:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_TIME", report["quarantined"]["12300"])

    def test_classic_rejects_the_1500_de_las_tres_slot(self):
        rows = make_rows()
        for row in rows:
            row["draw_close_at"] = "2026-11-20T15:00:00-06:00"
            row["set_assigned_at"] = "2026-11-20T14:00:00-06:00"
            row["measurement_at"] = "2026-11-20T15:05:00-06:00"
            row["draw_at"] = "2026-11-20T15:10:00-06:00"
            row["mapping_valid_from"] = "2026-11-20T13:00:00-06:00"
            row["mapping_valid_to"] = "2026-11-20T15:30:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_TIME", report["quarantined"]["12300"])

    def test_tres_accepts_its_official_1500_slot(self):
        rows = make_rows()
        for row in rows:
            row["modality"] = "TRES"
            row["draw_close_at"] = "2026-11-20T15:00:00-06:00"
            row["set_assigned_at"] = "2026-11-20T14:00:00-06:00"
            row["measurement_at"] = "2026-11-20T15:05:00-06:00"
            row["draw_at"] = "2026-11-20T15:10:00-06:00"
            row["mapping_valid_from"] = "2026-11-20T13:00:00-06:00"
            row["mapping_valid_to"] = "2026-11-20T15:30:00-06:00"
        report = validate_physical_rows(rows)
        self.assertEqual(report["usable_contests"], [12300])

    def test_timestamp_string_subclass_cannot_spoof_a_valid_close(self):
        class SpoofedTimestamp(str):
            def __str__(self):
                return "2026-11-20T21:00:00-06:00"

        rows = make_rows()
        rows[0]["draw_close_at"] = SpoofedTimestamp("2026-11-20T15:00:00-06:00")
        report = validate_physical_rows(rows)
        self.assertIn("row:2", report["quarantined"])
        self.assertNotIn(12300, report["usable_contests"])

    def test_row_mapping_subclass_cannot_spoof_contest_fields(self):
        class SpoofedRow(dict):
            def get(self, key, default=None):
                if key == "contest_id":
                    return "12300"
                return super().get(key, default)

        rows = make_rows()
        rows[1] = SpoofedRow(rows[1])
        report = validate_physical_rows(rows)
        self.assertIn("row:3", report["quarantined"])
        self.assertNotIn(12300, report["usable_contests"])

    def test_rows_are_snapshotted_as_they_are_iterated(self):
        rows = make_rows()
        first_row = rows[0]

        def mutating_rows():
            yield first_row
            first_row["printed_number"] = "999"
            yield from rows[1:]

        report = validate_physical_rows(mutating_rows())
        self.assertEqual(report["usable_contests"], [12300])

    def test_intake_row_limit_stops_unbounded_iterable(self):
        def unbounded_rows():
            while True:
                yield {}

        with self.assertRaisesRegex(
            ValueError,
            f"physical intake exceeds maximum {MAX_PHYSICAL_INTAKE_ROWS} rows",
        ):
            validate_physical_rows(unbounded_rows())

    def test_mapping_requires_each_number_exactly_once(self):
        rows = make_rows()
        rows[0]["printed_number"] = "2"
        report = validate_physical_rows(rows)
        self.assertIn("Q_MAPPING", report["quarantined"]["12300"])

    def test_physical_sphere_ids_must_be_unique(self):
        rows = make_rows()
        rows[1]["sphere_id"] = rows[0]["sphere_id"]
        report = validate_physical_rows(rows)
        self.assertIn("Q_MAPPING", report["quarantined"]["12300"])

    def test_calibration_must_cover_measurement(self):
        rows = make_rows()
        rows[0]["calibration_valid_to"] = "2026-11-20T17:00:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

    def test_timezone_is_mandatory(self):
        rows = make_rows()
        rows[0]["measurement_at"] = "2026-11-20T17:10:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

    def test_mixed_machine_or_set_within_contest_is_conflict(self):
        rows = make_rows()
        rows[-1]["machine_id"] = "M-02"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONFLICT", report["quarantined"]["12300"])

    def test_mass_must_be_finite_positive_grams(self):
        rows = make_rows()
        rows[0]["mass_value"] = "nan"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])
        rows = make_rows()
        rows[0]["mass_unit"] = "mg"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

    def test_smartballs_mass_envelope_and_spread_are_enforced(self):
        rows = make_rows()
        rows[0]["mass_value"] = "5.251"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

        rows = make_rows()
        rows[0]["mass_value"] = "4.700"
        rows[-1]["mass_value"] = "5.001"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

    def test_pingpong_mass_envelope_and_spread_are_enforced(self):
        rows = make_rows()
        for row in rows:
            row["sphere_type"] = "ping-pong"
            row["mass_value"] = "2.500"
        rows[0]["mass_value"] = "2.299"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

        rows = make_rows()
        for row in rows:
            row["sphere_type"] = "ping-pong"
            row["mass_value"] = "2.500"
        rows[0]["mass_value"] = "2.300"
        rows[-1]["mass_value"] = "2.451"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

    def test_unknown_sphere_type_is_quarantined(self):
        rows = make_rows()
        for row in rows:
            row["sphere_type"] = "unknown-sphere"
        report = validate_physical_rows(rows)
        self.assertIn("Q_METROLOGY", report["quarantined"]["12300"])

    def test_contest_metrology_identity_must_be_consistent(self):
        rows = make_rows()
        rows[-1]["scale_id"] = "SCALE-2"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONFLICT", report["quarantined"]["12300"])

        rows = make_rows()
        rows[-1]["calibration_valid_to"] = "2027-01-01T00:00:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONFLICT", report["quarantined"]["12300"])

    def test_mapping_must_be_effective_before_set_assignment(self):
        rows = make_rows()
        rows[0]["mapping_valid_from"] = "2026-11-20T17:05:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_REMAP", report["quarantined"]["12300"])

    def test_mapping_must_remain_valid_through_draw(self):
        rows = make_rows()
        rows[0]["mapping_valid_to"] = "2026-11-20T20:59:59-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_REMAP", report["quarantined"]["12300"])

    def test_draw_timestamp_must_follow_sales_close(self):
        rows = make_rows()
        for row in rows:
            row["draw_at"] = "2026-11-20T18:59:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_TIME", report["quarantined"]["12300"])

    def test_cross_contest_mapping_conflict_is_integrated(self):
        first = make_rows()
        second = make_rows()
        for row in second:
            row["contest_id"] = "12301"
        second[0]["printed_number"], second[1]["printed_number"] = "2", "1"
        report = validate_physical_rows(first + second)
        self.assertIn("Q_REMAP", report["quarantined"]["12300"])
        self.assertIn("Q_REMAP", report["quarantined"]["12301"])
        self.assertNotIn(12300, report["usable_contests"])
        self.assertNotIn(12301, report["usable_contests"])

    def test_draw_date_must_be_iso_calendar_date(self):
        rows = make_rows()
        rows[0]["draw_date"] = "20/11/2026"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONTEST_LINK", report["quarantined"]["12300"])

    def test_draw_date_requires_zero_padded_iso_calendar_date(self):
        rows = make_rows()
        rows[0]["draw_date"] = "2026-1-2"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONTEST_LINK", report["quarantined"]["12300"])

    def test_draw_date_must_match_mexico_city_close_date(self):
        rows = make_rows()
        for row in rows:
            row["draw_date"] = "2026-11-19"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONTEST_LINK", report["quarantined"]["12300"])
        self.assertNotIn(12300, report["usable_contests"])

    def test_utc_close_timestamp_is_compared_in_mexico_city_timezone(self):
        rows = make_rows()
        for row in rows:
            row["draw_close_at"] = "2026-11-21T03:00:00Z"
        report = validate_physical_rows(rows)
        self.assertEqual(report["usable_contests"], [12300])

    def test_source_hash_must_be_sha256(self):
        rows = make_rows()
        rows[0]["source_document_sha256"] = "not-a-hash"
        report = validate_physical_rows(rows)
        self.assertIn("Q_SOURCE_UNVERIFIED", report["quarantined"]["12300"])

    def test_missing_columns_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            validate_physical_rows([{"contest_id": "12300"}])

    def test_empty_intake_is_not_misreported_as_success(self):
        self.assertEqual(validate_physical_rows([])["status"], "EMPTY")

    def test_csv_reader_and_hash_do_not_modify_original(self):
        rows = make_rows()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "physical.csv"
            import csv
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            before = file_sha256(path)
            report = validate_physical_csv(path)
            self.assertEqual(report["usable_contests"], [12300])
            self.assertEqual(file_sha256(path), before)


    def test_csv_rejects_oversized_header_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized-header.csv"
            path.write_bytes(b"x" * (MAX_PHYSICAL_CSV_HEADER_BYTES + 1) + b"\n")
            with self.assertRaisesRegex(ValueError, "CSV header exceeds maximum"):
                validate_physical_csv(path)

    def test_csv_rejects_oversized_record_before_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized-record.csv"
            header = ",".join(REQUIRED_COLUMNS).encode("utf-8") + b"\n"
            record = b'"' + b"x" * MAX_PHYSICAL_CSV_RECORD_BYTES + b'"\n'
            path.write_bytes(header + record)
            with self.assertRaisesRegex(ValueError, "CSV record exceeds maximum"):
                validate_physical_csv(path)

    def test_csv_rejects_multiline_scalar_fields(self):
        rows = make_rows()
        rows[0]["sphere_set_id"] = "SET-A\nINJECTED"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "multiline.csv"
            import csv
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "CSV record syntax is invalid"):
                validate_physical_csv(path)

    def test_csv_rejects_decoded_row_text_over_limit(self):
        rows = make_rows()
        rows[0]["sphere_set_id"] = "x" * (MAX_PHYSICAL_CSV_ROW_TEXT_BYTES + 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "oversized-payload.csv"
            import csv
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, "CSV row text exceeds maximum"):
                validate_physical_csv(path)

    def test_csv_rejects_aggregate_byte_limit(self):
        rows = make_rows()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "aggregate-limit.csv"
            import csv
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=REQUIRED_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            header_bytes = len((",".join(REQUIRED_COLUMNS) + "\r\n").encode("utf-8"))
            with patch(
                "origen.physical_intake.MAX_PHYSICAL_CSV_INTAKE_TEXT_BYTES",
                header_bytes + 1,
            ):
                with self.assertRaisesRegex(ValueError, "CSV input exceeds maximum"):
                    validate_physical_csv(path)

    def test_csv_rejects_records_with_more_fields_than_header(self):
        row = make_rows()[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "extra-field.csv"
            header = ",".join(REQUIRED_COLUMNS)
            record = ",".join(row[column] for column in REQUIRED_COLUMNS) + ",EXTRA"
            path.write_text(header + "\n" + record + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "more fields than its header"):
                validate_physical_csv(path)


if __name__ == "__main__":
    unittest.main()
