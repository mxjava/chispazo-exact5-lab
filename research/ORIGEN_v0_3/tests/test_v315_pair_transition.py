import unittest
import numpy as np
from origen.v313_global_null import _simulate_draws
from origen.v315_pair_transition import PAIRS, OVERLAP_PROBS, _cell_counts, _max_stat, run_v315


class V315PairTransitionTests(unittest.TestCase):
    def test_pair_and_overlap_family_dimensions(self):
        self.assertEqual(len(PAIRS), 378)
        self.assertEqual(len(OVERLAP_PROBS), 3)
        self.assertAlmostEqual(float(OVERLAP_PROBS.sum()), 1.0)

    def test_each_transition_contributes_ten_pair_events(self):
        draws = _simulate_draws(np.random.default_rng(15), 120)
        counts = _cell_counts(draws)
        self.assertEqual(counts.shape, (1134,))
        self.assertEqual(int(counts.sum()), 119 * 10)

    def test_max_statistic_finite(self):
        draws = _simulate_draws(np.random.default_rng(16), 200)
        stat, counts = _max_stat(draws)
        self.assertTrue(np.isfinite(stat) and stat >= 0)
        self.assertEqual(int(counts.sum()), 1990)

    def test_reproducible_classic_only(self):
        rng = np.random.default_rng(17)
        rows = []
        for i in range(1000):
            nums = sorted((rng.choice(28, size=5, replace=False) + 1).tolist())
            rows.append({"contest": i+1, "numbers": nums, "draw_type": "CLASSIC"})
        rows.append({"contest": 1001, "numbers": [1,2,3,4,5], "draw_type": "DE_LAS_TRES"})
        a = run_v315(rows, "sha", simulations=999, seed=3152026)
        b = run_v315(rows, "sha", simulations=999, seed=3152026)
        self.assertEqual(a, b)
        self.assertEqual(a["n_classic_draws"], 1000)
        self.assertEqual(a["family_size"], 1134)
        self.assertEqual(len(a["winning_cell_chronological_blocks"]), 4)


if __name__ == "__main__":
    unittest.main()
