from __future__ import annotations

import unittest

from origen.mapping_history import audit_mapping_history


def rows():
    base = {
        "sphere_set_id": "SET-1",
        "sphere_id": "BALL-01",
        "printed_number": "7",
        "mapping_valid_from": "2026-01-01T00:00:00-06:00",
        "mapping_valid_to": "2026-12-31T23:59:59-06:00",
        "set_assigned_at": "2026-06-01T12:00:00-06:00",
        "draw_at": "2026-06-01T21:00:00-06:00",
    }
    return [
        {**base, "contest_id": "1001"},
        {**base, "contest_id": "1002"},
    ]


class MappingHistoryTests(unittest.TestCase):
    def test_same_mapping_across_contests_is_clear(self):
        report = audit_mapping_history(rows())
        self.assertEqual(report["status"], "MAPPING_HISTORY_CLEAR")
        self.assertEqual(report["overlapping_conflicts"], 0)

    def test_overlapping_sphere_remap_quarantines_both_contests(self):
        data = rows()
        data[1]["printed_number"] = "8"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_CONFLICTS")
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])
        self.assertIn("Q_REMAP", report["quarantined"]["1002"])
        self.assertGreater(report["forward_conflicts"], 0)

    def test_overlapping_duplicate_number_for_two_spheres_is_quarantined(self):
        data = rows()
        data[1]["sphere_id"] = "BALL-02"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_CONFLICTS")
        self.assertGreater(report["inverse_conflicts"], 0)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])
        self.assertIn("Q_REMAP", report["quarantined"]["1002"])

    def test_non_overlapping_remap_is_allowed(self):
        data = rows()
        data[0]["mapping_valid_to"] = "2026-03-31T23:59:59-06:00"
        data[0]["set_assigned_at"] = "2026-02-01T12:00:00-06:00"
        data[0]["draw_at"] = "2026-02-01T21:00:00-06:00"
        data[1]["mapping_valid_from"] = "2026-04-01T00:00:00-06:00"
        data[1]["printed_number"] = "8"
        data[1]["set_assigned_at"] = "2026-05-01T12:00:00-06:00"
        data[1]["draw_at"] = "2026-05-01T21:00:00-06:00"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_HISTORY_CLEAR")

    def test_assignment_outside_mapping_interval_is_quarantined(self):
        data = rows()
        data[0]["set_assigned_at"] = "2027-01-01T00:00:00-06:00"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_mapping_must_remain_valid_at_draw(self):
        data = rows()
        data[0]["mapping_valid_to"] = "2026-06-01T20:59:59-06:00"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_naive_timestamp_fails_closed(self):
        data = rows()
        data[0]["mapping_valid_from"] = "2026-01-01T00:00:00"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_missing_contest_id_fails_closed(self):
        data = rows()
        data[0].pop("contest_id")
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["row:2"])

    def test_different_sphere_sets_are_independent(self):
        data = rows()
        data[1]["sphere_set_id"] = "SET-2"
        data[1]["sphere_id"] = "BALL-02"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_HISTORY_CLEAR")


    def test_mapping_identifiers_require_ascii_decimal_text(self):
        data = rows()
        data[0]["contest_id"] = "１２３４"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["row:2"])

        data = rows()
        data[0]["printed_number"] = "７"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_mapping_timestamps_require_canonical_rfc3339(self):
        for value in (
            "2026-01-01 00:00:00-06:00",
            "20260101T000000-0600",
            "2026-01-01T00:00:00",
            "2026-01-01T00:00:00-0600",
        ):
            with self.subTest(value=value):
                data = rows()
                data[0]["mapping_valid_from"] = value
                report = audit_mapping_history(data)
                self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_mapping_timestamps_accept_canonical_fractional_seconds(self):
        data = rows()
        data[0]["mapping_valid_from"] = "2026-01-01T00:00:00.123456-06:00"
        report = audit_mapping_history(data)
        self.assertNotIn("Q_REMAP", report["quarantined"].get("1001", []))

    def test_unknown_rfc3339_offset_is_rejected_for_every_mapping_event(self):
        for field in (
            "mapping_valid_from", "mapping_valid_to", "set_assigned_at", "draw_at",
        ):
            with self.subTest(field=field):
                data = rows()
                data[0][field] = "2026-01-01T00:00:00-00:00"
                report = audit_mapping_history(data)
                self.assertIn("Q_REMAP", report["quarantined"]["1001"])
                self.assertEqual(report["status"], "MAPPING_CONFLICTS")

    def test_mapping_timestamp_string_subclass_is_rejected(self):
        class SpoofedTimestamp(str):
            def replace(self, old, new, *args):
                return "2026-01-01T00:00:00-06:00"

        data = rows()
        data[0]["mapping_valid_from"] = SpoofedTimestamp(
            "2026-01-01T00:00:00Z"
        )
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])


if __name__ == "__main__":
    unittest.main()
