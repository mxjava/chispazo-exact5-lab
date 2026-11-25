import csv
import tempfile
import unittest
from pathlib import Path

from origen.v321_weekday_omnibus import FEATURES, analyze, eta_squared, load_atlas


def rows_with_signal():
    rows = []
    contest = 1
    for weekday in range(1, 8):
        for offset in range(4):
            values = {feature: float(offset) for feature in FEATURES}
            values["sum"] = float(weekday * 10 + offset)
            rows.append((contest, weekday, values))
            contest += 1
    return rows


class V321WeekdayOmnibusTests(unittest.TestCase):
    def test_eta_squared_group_separation(self):
        self.assertAlmostEqual(eta_squared([1, 2, 10, 11], [1, 1, 2, 2]), 81 / 82)

    def test_detects_strong_synthetic_association_reproducibly(self):
        first = analyze(rows_with_signal(), permutations=199, seed=3212026)
        second = analyze(rows_with_signal(), permutations=199, seed=3212026)
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "HISTORICAL_ASSOCIATION_DETECTED")
        self.assertEqual(first["n_classic_draws"], 28)
        self.assertEqual(first["rng"], "numpy.random.Generator(PCG64)")

    def test_rejects_zero_permutations(self):
        with self.assertRaises(ValueError):
            analyze(rows_with_signal(), permutations=0)

    def test_load_atlas_sorts_by_contest_and_rejects_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "atlas.csv"
            fields = ["contest", "weekday_iso", *FEATURES]
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for contest, weekday, values in reversed(rows_with_signal()):
                    writer.writerow({"contest": contest, "weekday_iso": weekday, **values})
            loaded = load_atlas(path)
            self.assertEqual([row[0] for row in loaded], sorted(row[0] for row in loaded))
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writerow({"contest": 1, "weekday_iso": 1, **{f: 1 for f in FEATURES}})
            with self.assertRaises(ValueError):
                load_atlas(path)


if __name__ == "__main__":
    unittest.main()
