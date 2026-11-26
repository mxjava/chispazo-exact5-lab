import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.v265.CHISPAZO_V265_PHYSICAL_REGIME_SCANNER import (
    load_history,
    same_day_pairs,
)


class ModalityIsolationTests(unittest.TestCase):
    def _csv(self, rows):
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.close()
        path = Path(tmp.name)
        pd.DataFrame(rows).to_csv(path, index=False)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_requires_explicit_modality_column(self):
        path = self._csv([{
            "CONCURSO": 1, "R1": 1, "R2": 2, "R3": 3, "R4": 4,
            "R5": 5, "FECHA": "2026-01-01",
        }])
        with self.assertRaisesRegex(ValueError, "explicit modality column"):
            load_history(path, "MODALIDAD")

    def test_rejects_missing_modality_and_duplicate_contest_ids(self):
        missing = self._csv([{
            "CONCURSO": 1, "R1": 1, "R2": 2, "R3": 3, "R4": 4,
            "R5": 5, "FECHA": "2026-01-01", "MODALIDAD": None,
        }])
        with self.assertRaisesRegex(ValueError, "Missing draw modality"):
            load_history(missing, "MODALIDAD")

        duplicate = self._csv([
            {"CONCURSO": 1, "R1": 1, "R2": 2, "R3": 3, "R4": 4,
             "R5": 5, "FECHA": "2026-01-01", "MODALIDAD": "CLASSIC"},
            {"CONCURSO": 1, "R1": 6, "R2": 7, "R3": 8, "R4": 9,
             "R5": 10, "FECHA": "2026-01-01", "MODALIDAD": "EARLY"},
        ])
        with self.assertRaisesRegex(ValueError, "Duplicate contest IDs"):
            load_history(duplicate, "MODALIDAD")

    def test_pairs_by_explicit_labels_not_contest_order(self):
        frame = pd.DataFrame([
            {"CONCURSO": 102, "FECHA": "2026-01-01", "MODALIDAD": "CLASSIC",
             "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5},
            {"CONCURSO": 101, "FECHA": "2026-01-01", "MODALIDAD": "EARLY",
             "R1": 6, "R2": 7, "R3": 8, "R4": 9, "R5": 10},
        ])
        pairs = same_day_pairs(frame, "MODALIDAD", "EARLY", "CLASSIC")
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][1:3], (101, 102))
        self.assertEqual(pairs[0][3], {6, 7, 8, 9, 10})
        self.assertEqual(pairs[0][4], {1, 2, 3, 4, 5})

    def test_rejects_unexpected_labels_and_ambiguous_same_day(self):
        frame = pd.DataFrame([
            {"CONCURSO": 1, "FECHA": "2026-01-01", "MODALIDAD": "CLASSIC",
             "R1": 1, "R2": 2, "R3": 3, "R4": 4, "R5": 5},
            {"CONCURSO": 2, "FECHA": "2026-01-01", "MODALIDAD": "OTHER",
             "R1": 6, "R2": 7, "R3": 8, "R4": 9, "R5": 10},
        ])
        with self.assertRaisesRegex(ValueError, "Unexpected modality labels"):
            same_day_pairs(frame, "MODALIDAD", "EARLY", "CLASSIC")

        frame.loc[1, "MODALIDAD"] = "CLASSIC"
        with self.assertRaisesRegex(ValueError, "Multiple draws for a modality"):
            same_day_pairs(frame, "MODALIDAD", "EARLY", "CLASSIC")


if __name__ == "__main__":
    unittest.main()
