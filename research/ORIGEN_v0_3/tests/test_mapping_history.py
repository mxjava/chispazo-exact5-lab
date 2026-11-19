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

    def test_overlapping_different_number_is_quarantined_both_contests(self):
        data = rows()
        data[1]["printed_number"] = "8"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_CONFLICTS")
        self.assertEqual(report["quarantined"], {
            "1001": ["Q_REMAP"], "1002": ["Q_REMAP"]
        })

    def test_non_overlapping_remap_is_allowed(self):
        data = rows()
        data[0]["mapping_valid_to"] = "2026-03-31T23:59:59-06:00"
        data[0]["set_assigned_at"] = "2026-02-01T12:00:00-06:00"
        data[1]["mapping_valid_from"] = "2026-04-01T00:00:00-06:00"
        data[1]["printed_number"] = "8"
        data[1]["set_assigned_at"] = "2026-05-01T12:00:00-06:00"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_HISTORY_CLEAR")

    def test_assignment_outside_mapping_interval_is_quarantined(self):
        data = rows()
        data[0]["set_assigned_at"] = "2027-01-01T00:00:00-06:00"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_naive_timestamp_fails_closed(self):
        data = rows()
        data[0]["mapping_valid_from"] = "2026-01-01T00:00:00"
        report = audit_mapping_history(data)
        self.assertIn("Q_REMAP", report["quarantined"]["1001"])

    def test_different_sphere_sets_are_independent(self):
        data = rows()
        data[1]["sphere_set_id"] = "SET-2"
        data[1]["printed_number"] = "8"
        report = audit_mapping_history(data)
        self.assertEqual(report["status"], "MAPPING_HISTORY_CLEAR")


if __name__ == "__main__":
    unittest.main()
