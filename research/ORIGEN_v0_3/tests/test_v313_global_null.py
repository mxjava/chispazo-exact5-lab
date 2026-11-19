"""Tests for V313 fixed-size null calibration and guardrails."""
import unittest

import numpy as np

from origen.v313_global_null import _matrix, _simulate_draws, _statistics, run_v313


class V313Tests(unittest.TestCase):
    def test_simulator_always_generates_five_distinct_numbers(self):
        draws = _simulate_draws(np.random.default_rng(7), 250)
        self.assertEqual(draws.shape, (250, 28))
        self.assertTrue(np.all(draws.sum(axis=1) == 5))
        self.assertTrue(np.all((draws == 0) | (draws == 1)))

    def test_matrix_rejects_invalid_draw(self):
        with self.assertRaises(ValueError):
            _matrix([{"numbers": [1, 1, 2, 3, 4]}])

    def test_statistic_is_finite_for_valid_stream(self):
        draws = _simulate_draws(np.random.default_rng(8), 120)
        stats = _statistics(draws)
        self.assertEqual(len(stats), 3)
        self.assertTrue(all(np.isfinite(x) and x >= 0 for x in stats))

    def test_pair_counts_do_not_overflow_int8(self):
        # Every pair among these five numbers co-occurs 2,000 times.
        draws = np.tile(_matrix([{"numbers": [1, 2, 3, 4, 5]}]), (2000, 1))
        _, pair_stat, _ = _statistics(draws)
        pair_p = 5 * 4 / (28 * 27)
        expected = 2000 * pair_p
        variance = 2000 * pair_p * (1 - pair_p)
        expected_max = max(abs(2000 - expected), abs(0 - expected)) / np.sqrt(variance)
        self.assertAlmostEqual(pair_stat, expected_max, places=10)

    def test_run_is_classic_only_and_reproducible(self):
        rows = []
        rng = np.random.default_rng(9)
        for i in range(1000):
            nums = sorted((rng.choice(28, size=5, replace=False) + 1).tolist())
            rows.append({"contest": i + 1, "numbers": nums, "draw_type": "CLASSIC"})
        rows.append({"contest": 1001, "numbers": [1, 2, 3, 4, 5], "draw_type": "DE_LAS_TRES"})
        a = run_v313(rows, "abc", simulations=999, seed=11)
        b = run_v313(rows, "abc", simulations=999, seed=11)
        self.assertEqual(a, b)
        self.assertEqual(a["n_classic_draws"], 1000)
        self.assertEqual(a["last_contest"], 1000)
        self.assertEqual(a["classification"], "RESEARCH_ONLY_HISTORICAL_FALSIFICATION_NOT_PREDICTIVE_EDGE")


if __name__ == "__main__":
    unittest.main()
