import tempfile, unittest
from pathlib import Path
from origen.v320_draw_atlas import UNIVERSE_SIZE, features, universe_reference, _percentile

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

if __name__ == "__main__":
    unittest.main()
