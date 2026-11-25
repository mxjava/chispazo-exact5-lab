import unittest
import numpy as np
from origen.v313_global_null import _simulate_draws
from origen.v314_triple_motif import TRIPLES, TRIPLE_P, _triple_counts, _triple_max_z, run_v314


class V314TripleMotifTests(unittest.TestCase):
    def test_universe_has_all_3276_unordered_triples(self):
        self.assertEqual(len(TRIPLES), 3276)
        self.assertEqual(len(set(TRIPLES)), 3276)

    def test_triple_count_exact_for_repeated_draw(self):
        draws = np.tile(_simulate_draws(np.random.default_rng(3), 1), (2000, 1))
        counts = _triple_counts(draws)
        self.assertEqual(int(counts.max()), 2000)
        self.assertEqual(int(np.count_nonzero(counts)), 10)

    def test_triple_probability(self):
        self.assertAlmostEqual(TRIPLE_P, 5 / 1638)

    def test_run_is_reproducible_and_classic_only(self):
        rows = []
        rng = np.random.default_rng(7)
        for i in range(1000):
            nums = sorted((rng.choice(28, size=5, replace=False) + 1).tolist())
            rows.append({"contest": i + 1, "numbers": nums, "draw_type": "CLASSIC"})
            rows.append({"contest": i + 10001, "numbers": [1, 2, 3, 4, 5], "draw_type": "DE_LAS_TRES"})
        a = run_v314(rows, "abc", simulations=999, seed=3142026)
        b = run_v314(rows, "abc", simulations=999, seed=3142026)
        self.assertEqual(a, b)
        self.assertEqual(a["n_classic_draws"], 1000)
        self.assertEqual(a["family_size"], 3276)
        self.assertEqual(len(a["winning_triple_chronological_blocks"]), 4)


if __name__ == "__main__":
    unittest.main()
