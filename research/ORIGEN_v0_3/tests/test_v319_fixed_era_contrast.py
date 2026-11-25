from __future__ import annotations

import unittest

import numpy as np

from origen.v318_combinatorial_shape import EXPECTED_SOURCE_SHA256
from origen.v319_fixed_era_contrast import (
    _era_statistics,
    _max_two_sample_z,
    run_v319,
)


class V319FixedEraContrastTests(unittest.TestCase):
    def test_equal_proportions_have_zero_statistic(self):
        result = _max_two_sample_z(
            np.asarray([5, 5]),
            np.asarray([10, 10]),
            np.asarray([0.5, 0.5]),
            10,
            20,
        )
        self.assertEqual(result, 0.0)

    def test_invalid_shapes_and_probabilities_rejected(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            _max_two_sample_z(
                np.asarray([1, 2]), np.asarray([1]), np.asarray([0.5, 0.5]), 10, 10
            )
        with self.assertRaisesRegex(ValueError, "shape"):
            _max_two_sample_z(
                np.asarray([1]), np.asarray([1]), np.asarray([1.1]), 10, 10
            )

    def test_identical_era_matrices_have_zero_difference(self):
        matrix = np.zeros((20, 28), dtype=np.int8)
        for row in range(20):
            start = row % 24
            matrix[row, start:start + 5] = 1
        # Reuse the exact universe probabilities from V318.
        from origen.v318_combinatorial_shape import _universe_reference
        _, probabilities, _ = _universe_reference()
        stats = _era_statistics(matrix, matrix.copy(), probabilities)
        self.assertEqual(set(stats), {
            "number_identity", "pair_identity", "sum", "range", "odd_count",
            "prime_count", "adjacent_consecutive_pairs", "low_1_to_14_count",
            "three_band_occupancy",
        })
        self.assertTrue(all(value == 0.0 for value in stats.values()))

    def test_frozen_simulation_contract(self):
        with self.assertRaisesRegex(ValueError, "frozen_simulations"):
            run_v319([], EXPECTED_SOURCE_SHA256, simulations=999)
        with self.assertRaisesRegex(ValueError, "frozen_simulations"):
            run_v319([], EXPECTED_SOURCE_SHA256, simulations=1999, seed=7)

    def test_source_hash_guard(self):
        with self.assertRaisesRegex(ValueError, "source_sha256"):
            run_v319([], "0" * 64)

    def test_fixed_era_requires_sufficient_data(self):
        with self.assertRaisesRegex(ValueError, "insufficient_rows"):
            run_v319([], EXPECTED_SOURCE_SHA256)


if __name__ == "__main__":
    unittest.main()
