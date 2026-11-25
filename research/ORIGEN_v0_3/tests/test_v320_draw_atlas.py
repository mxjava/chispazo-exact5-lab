import tempfile, unittest
from pathlib import Path
from origen.v320_draw_atlas import UNIVERSE_SIZE, features, universe_reference, _percentile, prior_identity_counts

class V320AtlasTests(unittest.TestCase):
    def test_universe_size_and_cell_mass(self):
        scalar, cells = universe_reference()
        self.assertEqual(sum(cells.values()), UNIVERSE_SIZE)
        self.assertEqual(len(scalar["sum"]), UNIVERSE_SIZE)
        self.assertGreater(len(cells), 1)

    def test_known_set_features(self):
        f = features([1, 2, 3, 4, 5])
        self.assertEqual(f["sum"], 15)
        self.assertEqual(f["consecutive_pairs"], 4)
        self.assertEqual(f["odd_count"], 3)
        self.assertEqual(f["gap_vector"], (1, 1, 1, 1))

    def test_rejects_invalid_sets(self):
        for nums in ([1, 2, 3, 4, 4], [0, 2, 3, 4, 5], [1, 2, 3, 4]):
            with self.assertRaises(ValueError):
                features(nums)

    def test_percentile_midrank(self):
        values = [1, 1, 2, 3]
        self.assertEqual(_percentile(values, 1), 0.25)
        self.assertEqual(_percentile(values, 2), 0.625)

    def test_pair_triple_counts_exclude_target_and_future(self):
        first = [1, 2, 3, 4, 5]
        target = [1, 2, 3, 6, 7]
        future = [1, 2, 3, 8, 9]
        pairs, triples = prior_identity_counts([first, target, future], 1)
        self.assertEqual(pairs[(1, 2)], 1)
        self.assertEqual(triples[(1, 2, 3)], 1)
        self.assertNotIn((1, 6), pairs)
        self.assertNotIn((1, 2, 8), triples)

    def test_prior_counts_reject_invalid_index_and_draw(self):
        with self.assertRaises(ValueError):
            prior_identity_counts([[1, 2, 3, 4, 5]], 2)
        with self.assertRaises(ValueError):
            prior_identity_counts([[1, 2, 3, 4, 4]], 1)

    def test_calendar_day_is_iso_date_based(self):
        from datetime import date
        self.assertEqual(date.fromisoformat('2026-11-19').isoweekday(), 4)

if __name__ == "__main__":
    unittest.main()
