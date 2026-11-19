from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from origen.physical_intake import (
    REQUIRED_COLUMNS, file_sha256, validate_physical_csv, validate_physical_rows,
)


def make_rows():
    rows = []
    for number in range(1, 29):
        rows.append({
            "contest_id": "12300",
            "draw_date": "2026-11-20",
            "modality": "CLASSIC",
            "draw_close_at": "2026-11-20T19:00:00-06:00",
            "sphere_set_id": "SET-A",
            "set_assigned_at": "2026-11-20T17:00:00-06:00",
            "sphere_type": "Smartballs",
            "machine_id": "M-01",
            "machine_model": "Model-X",
            "sphere_id": f"SPH-{number:02d}",
            "printed_number": str(number),
            "mass_value": f"{4.70 + number / 1000:.3f}",
            "mass_unit": "g",
            "measurement_at": "2026-11-20T17:10:00-06:00",
            "measurement_resolution": "0.001",
            "scale_id": "SCALE-1",
            "calibration_valid_from": "2026-01-01T00:00:00-06:00",
            "calibration_valid_to": "2026-12-31T23:59:59-06:00",
            "calibration_certificate_sha256": "a" * 64,
            "mapping_valid_from": "2026-11-20T16:00:00-06:00",
            "source_document_sha256": "b" * 64,
            "source_document_ref": "ACTA-12300/TIRA-1",
        })
    return rows


class PhysicalIntakeTests(unittest.TestCase):
    def test_complete_preclose_contest_is_structurally_usable(self):
        report = validate_physical_rows(make_rows())
        self.assertEqual(report["usable_contests"], [12300])
        self.assertEqual(report["quarantined"], {})
        self.assertIn("not established", report["scope_warning"])

    def test_missing_sphere_row_quarantines_incomplete_set(self):
        report = validate_physical_rows(make_rows()[:-1])
        self.assertIn("Q_INCOMPLETE_SET", report["quarantined"]["12300"])

    def test_postclose_measurement_is_quarantined(self):
        rows = make_rows()
        rows[0]["measurement_at"] = "2026-11-20T19:01:00-06:00"
        report = validate_physical_rows(rows)
        self.assertIn("Q_TIME", report["quarantined"]["12300"])

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
        self.assertIn("Q_MAPPING", report["quarantined"]["12300"])

    def test_draw_date_must_be_iso_calendar_date(self):
        rows = make_rows()
        rows[0]["draw_date"] = "20/11/2026"
        report = validate_physical_rows(rows)
        self.assertIn("Q_CONTEST_LINK", report["quarantined"]["12300"])

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


if __name__ == "__main__":
    unittest.main()
