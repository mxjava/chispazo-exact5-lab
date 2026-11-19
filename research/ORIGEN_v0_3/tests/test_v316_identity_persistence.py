from __future__ import annotations

import unittest
from itertools import combinations

import numpy as np

from origen.v313_global_null import _simulate_draws
from origen.v316_identity_persistence import (
    LAGS, PAIRS, P1, P2, Q1, Q2, _max_statistic,
    _reference_counts, _statistics_by_component,
)


class V316IdentityPersistenceTests(unittest.TestCase):
    def test_frozen_family_size_is_8140(self):
        self.assertEqual(len(LAGS), 20)
        self.assertEqual(len(PAIRS), 378)
        self.assertEqual(20 + 20 * 28 + 20 * 378, 8140)

    def test_identity_probabilities_match_exact_5_of_28(self):
        self.assertAlmostEqual(P1, 5 / 28, places=15)
        self.assertAlmostEqual(P2, 5 / 189, places=15)
        self.assertAlmostEqual(Q1, (5 / 28) ** 2, places=15)
        self.assertAlmostEqual(Q2, (5 / 189) ** 2, places=15)

    def test_packed_pair_counts_match_nested_loop_reference(self):
        draws = _simulate_draws(np.random.default_rng(3162026), 100)
        maximum, aggregate, numbers, pairs = _statistics_by_component(draws)
        self.assertEqual(aggregate.shape, (20,))
        self.assertEqual(numbers.shape, (20, 28))
        self.assertEqual(pairs.shape, (20, 378))
        self.assertEqual(maximum, max(float(aggregate.max()), float(numbers.max()), float(pairs.max())))
        for lag in (1, 2, 7, 19, 20):
            mean, number_counts, pair_counts = _reference_counts(draws, lag)
            shared = draws[:-lag] & draws[lag:]
            self.assertAlmostEqual(mean, float(shared.sum(axis=1).mean()), places=15)
            np.testing.assert_array_equal(number_counts, shared.sum(axis=0, dtype=np.int64))
            # Rebuild pair cell counts independently from explicit combinations.
            self.assertEqual(int(pair_counts.sum()), sum(
                len(list(combinations(np.flatnonzero(row).tolist(), 2))) for row in shared
            ))
            lag_idx = LAGS.index(lag)
            transitions = len(draws) - lag
            expected_numbers = transitions * Q1
            number_var = transitions * Q1 * (1 - Q1)
            expected_pairs = transitions * Q2
            pair_var = transitions * Q2 * (1 - Q2)
            direct_number_z = np.abs(number_counts - expected_numbers) / np.sqrt(number_var)
            direct_pair_z = np.abs(pair_counts - expected_pairs) / np.sqrt(pair_var)
            np.testing.assert_allclose(numbers[lag_idx], direct_number_z, rtol=0, atol=1e-14)
            np.testing.assert_allclose(pairs[lag_idx], direct_pair_z, rtol=0, atol=1e-14)

    def test_label_permutation_preserves_global_maximum(self):
        draws = _simulate_draws(np.random.default_rng(44), 120)
        permutation = np.random.default_rng(45).permutation(28)
        permuted = draws[:, permutation]
        self.assertAlmostEqual(_max_statistic(draws), _max_statistic(permuted), places=12)

    def test_injected_repeated_draw_persistence_increases_maximum(self):
        fixed = np.zeros((80, 28), dtype=np.int8)
        fixed[:, :5] = 1
        random = _simulate_draws(np.random.default_rng(46), 80)
        self.assertGreater(_max_statistic(fixed), _max_statistic(random))

    def test_kernel_rejects_nonbinary_and_wrong_cardinality(self):
        valid = _simulate_draws(np.random.default_rng(47), 40)
        malformed = valid.astype(np.int16)
        malformed[0, 0] = 2
        with self.assertRaises(ValueError):
            _max_statistic(malformed)
        malformed = valid.copy()
        malformed[0, 0] = 1 - malformed[0, 0]
        with self.assertRaises(ValueError):
            _max_statistic(malformed)


if __name__ == "__main__":
    unittest.main()
