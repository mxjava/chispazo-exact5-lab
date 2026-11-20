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

    def test_invalid_rows_do_not_masquerade_as_overlap_conflicts(self):
        invalid = rows()
        invalid[0]["sphere_id"] = " "
        report = audit_mapping_history(invalid)
        self.assertEqual(report["overlapping_conflicts"], 0)
        self.assertTrue(report["overlap_conflicts_clear"])
        self.assertGreater(report["invalid_or_quarantined_mapping_rows"], 0)
        self.assertEqual(report["continuity_status"], "NOT_PROVEN")

    def test_interval_clearance_does_not_claim_continuity(self):
        report = audit_mapping_history(rows())
        self.assertTrue(report["interval_conflicts_clear"])
        self.assertEqual(report["continuity_status"], "NOT_PROVEN")

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

    def test_none_sphere_id_fails_closed(self):
        data = rows()
        data[0]["sphere_id"] = None
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_none_sphere_set_id_fails_closed(self):
        data = rows()
        data[0]["sphere_set_id"] = None
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


if __name__ == "__main__":
    unittest.main()
