from __future__ import annotations

import math
import unittest

import numpy as np

from origen.v318_combinatorial_shape import (
    EXPECTED_SOURCE_SHA256,
    FEATURE_NAMES,
    _feature_codes,
    _family_max_z,
    _universe_reference,
    run_v318,
)


class V318CombinatorialShapeTests(unittest.TestCase):
    def test_fixed_feature_codes_for_known_sets(self):
        sets = np.asarray([
            [1, 2, 3, 4, 5],
            [2, 4, 6, 8, 10],
            [7, 14, 19, 23, 28],
        ], dtype=np.int16)
        features = _feature_codes(sets)
        self.assertEqual(int(features["sum"][0]), 15)
        self.assertEqual(int(features["range"][0]), 4)
        self.assertEqual(int(features["odd_count"][0]), 3)
        self.assertEqual(int(features["prime_count"][0]), 3)
        self.assertEqual(int(features["adjacent_consecutive_pairs"][0]), 4)
        self.assertEqual(int(features["low_1_to_14_count"][0]), 5)
        self.assertEqual(int(features["three_band_occupancy"][0]), (5 * 6 + 0) * 6 + 0)
        self.assertEqual(set(features), set(FEATURE_NAMES))

    def test_feature_codes_reject_unsorted_or_duplicate_sets(self):
        with self.assertRaisesRegex(ValueError, "sorted and distinct"):
            _feature_codes(np.asarray([[1, 3, 2, 4, 5]], dtype=np.int16))
        with self.assertRaisesRegex(ValueError, "sorted and distinct"):
            _feature_codes(np.asarray([[1, 2, 2, 4, 5]], dtype=np.int16))

    def test_feature_codes_reject_out_of_range_and_wrong_shape(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            _feature_codes(np.asarray([[1, 2, 3, 4, 29]], dtype=np.int16))
        with self.assertRaisesRegex(ValueError, "shape"):
            _feature_codes(np.asarray([[1, 2, 3, 4]], dtype=np.int16))

    def test_exact_universe_probabilities_sum_to_one(self):
        universe, probabilities, counts = _universe_reference()
        self.assertEqual(universe.shape, (math.comb(28, 5), 5))
        for name in FEATURE_NAMES:
            self.assertAlmostEqual(float(probabilities[name].sum()), 1.0, places=14)
            self.assertEqual(int(counts[name].sum()), math.comb(28, 5))
            self.assertGreater(int(np.count_nonzero(probabilities[name])), 0)

    def test_max_z_zero_for_exact_expected_integer_fixture(self):
        probabilities = np.asarray([0.5, 0.5])
        self.assertEqual(_family_max_z(np.asarray([0, 1] * 10), probabilities, 20), 0.0)

    def test_run_refuses_changed_simulation_contract(self):
        with self.assertRaisesRegex(ValueError, "frozen_simulations"):
            run_v318([], EXPECTED_SOURCE_SHA256, simulations=999)
        with self.assertRaisesRegex(ValueError, "frozen_simulations"):
            run_v318([], EXPECTED_SOURCE_SHA256, simulations=1999, seed=1)

    def test_run_refuses_unexpected_source_hash(self):
        with self.assertRaisesRegex(ValueError, "source_sha256"):
            run_v318([], "0" * 64)

    def test_run_refuses_wrong_classic_sample_size(self):
        one = {"draw_type": "CLASSIC", "contest": 1363, "numbers": [1, 2, 3, 4, 5]}
        with self.assertRaisesRegex(ValueError, "classic_draw_count"):
            run_v318([one], EXPECTED_SOURCE_SHA256)


if __name__ == "__main__":
    unittest.main()
