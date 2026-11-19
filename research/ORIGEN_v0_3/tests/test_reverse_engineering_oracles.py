"""Independent, deliberately simple reference oracles for Exact5 optimized kernels."""
from itertools import combinations
import math
import unittest

import numpy as np

from origen.v312_static_mixture import (
    UNIFORM, _expert_probability, _mixture_probability,
)
from origen.v313_global_null import (
    _matrix, _simulate_draws, _statistics,
)
from origen.v314_triple_motif import (
    TRIPLES, _triple_counts,
)
from origen.v315_pair_transition import (
    PAIRS, OVERLAP_PROBS, _cell_counts,
)


def reference_triple_counts(draws):
    out = {triple: 0 for triple in TRIPLES}
    for row in draws:
        chosen = tuple(np.flatnonzero(row).tolist())
        for triple in combinations(chosen, 3):
            out[triple] += 1
    return np.asarray([out[t] for t in TRIPLES], dtype=np.int32)


def reference_pair_transition_counts(draws):
    pair_index = {pair: i for i, pair in enumerate(PAIRS)}
    out = np.zeros((len(PAIRS), 3), dtype=np.int64)
    for t in range(len(draws) - 1):
        previous = tuple(np.flatnonzero(draws[t]).tolist())
        following = set(np.flatnonzero(draws[t + 1]).tolist())
        for pair in combinations(previous, 2):
            overlap = int(pair[0] in following) + int(pair[1] in following)
            out[pair_index[pair], overlap] += 1
    return out.ravel()


class ReverseEngineeringOracleTests(unittest.TestCase):
    def test_v312_expert_distribution_exhaustively_normalizes(self):
        feature = [math.sin(i * 0.37) + (i % 5) * 0.13 for i in range(28)]
        for beta in (0.15, 0.60):
            total = math.fsum(
                _expert_probability(feature, beta, list(combo))
                for combo in combinations(range(1, 29), 5)
            )
            self.assertAlmostEqual(total, 1.0, places=10)

    def test_v312_chosen_order_and_feature_translation_invariance(self):
        feature = [float((i * 11) % 17) for i in range(28)]
        chosen = [2, 7, 13, 19, 28]
        p = _expert_probability(feature, 0.30, chosen)
        self.assertAlmostEqual(p, _expert_probability(feature, 0.30, list(reversed(chosen))), places=15)
        shifted = [x + 12345.0 for x in feature]
        self.assertAlmostEqual(p, _expert_probability(shifted, 0.30, chosen), places=14)

    def test_v312_mixture_floor_and_component_count(self):
        names = ("freq50", "freq200", "freq800", "ewma16", "ewma32",
                 "ewma64", "hotgap", "duegap", "transition")
        features = {name: [float((i * 7) % 19) for i in range(28)] for name in names}
        p, experts = _mixture_probability(features, [1, 5, 11, 19, 28])
        self.assertEqual(len(experts), 27)
        self.assertGreaterEqual(p, 0.5 * UNIFORM)
        self.assertTrue(math.isfinite(p))

    def test_uniform_simulator_domain_and_reproducibility(self):
        a = _simulate_draws(np.random.default_rng(20261119), 500)
        b = _simulate_draws(np.random.default_rng(20261119), 500)
        np.testing.assert_array_equal(a, b)
        self.assertTrue(np.all((a == 0) | (a == 1)))
        np.testing.assert_array_equal(a.sum(axis=1), np.full(500, 5))

    def test_v313_matrix_rejects_invalid_draw_numbers(self):
        bad_rows = [
            {"numbers": [1, 1, 2, 3, 4]},
            {"numbers": [0, 2, 3, 4, 5]},
            {"numbers": [1, 2, 3, 4, 29]},
            {"numbers": [1, 2, 3, 4]},
        ]
        for row in bad_rows:
            with self.subTest(row=row), self.assertRaises(ValueError):
                _matrix([row])

    def test_v313_statistics_match_direct_number_and_pair_counts(self):
        draws = _simulate_draws(np.random.default_rng(777), 250)
        number_stat, pair_stat, temporal_stat = _statistics(draws)
        inclusion = draws.astype(np.int64).sum(axis=0)
        p = 5 / 28
        expected = len(draws) * p
        variance = len(draws) * p * (1-p)
        direct_number = float(np.max(np.abs(inclusion - expected)) / math.sqrt(variance))
        pair_counts = [
            int(np.sum(draws[:, i].astype(np.int64) * draws[:, j].astype(np.int64)))
            for i, j in combinations(range(28), 2)
        ]
        pair_p = 5 / 189
        pair_var = len(draws) * pair_p * (1-pair_p)
        direct_pair = float(np.max(np.abs(np.asarray(pair_counts) - len(draws)*pair_p)) / math.sqrt(pair_var))
        self.assertAlmostEqual(number_stat, direct_number, places=14)
        self.assertAlmostEqual(pair_stat, direct_pair, places=14)
        self.assertTrue(math.isfinite(temporal_stat))


    def test_v313_v314_v315_kernels_reject_nonbinary_matrices(self):
        from origen.v314_triple_motif import _triple_counts
        from origen.v315_pair_transition import _cell_counts
        valid = _simulate_draws(np.random.default_rng(999), 8)
        malformed = []
        two = valid.astype(np.int16)
        two[0, 0] = 2
        malformed.append(two)
        negative = valid.astype(np.int16)
        negative[0, 0] = -1
        negative[0, 1] = 2
        malformed.append(negative)
        fractional = valid.astype(float)
        fractional[0, 0] = 0.5
        malformed.append(fractional)
        wrong_cardinality = valid.copy()
        wrong_cardinality[0, 0] = 0
        malformed.append(wrong_cardinality)
        for bad in malformed:
            for kernel in (_statistics, _triple_counts, _cell_counts):
                with self.subTest(kernel=kernel.__name__, dtype=bad.dtype), self.assertRaises(ValueError):
                    kernel(bad)
        with self.assertRaises(ValueError):
            _statistics(valid[:, :-1])

    def test_v314_optimized_triple_map_matches_reference_exactly(self):
        rng = np.random.default_rng(3142026)
        for n in (2, 7, 31, 100):
            draws = _simulate_draws(rng, n)
            np.testing.assert_array_equal(_triple_counts(draws), reference_triple_counts(draws))
            self.assertEqual(int(_triple_counts(draws).sum()), n * 10)

    def test_v315_optimized_transition_map_matches_reference_exactly(self):
        rng = np.random.default_rng(3152026)
        for n in (2, 7, 31, 100):
            draws = _simulate_draws(rng, n)
            np.testing.assert_array_equal(_cell_counts(draws), reference_pair_transition_counts(draws))
            self.assertEqual(int(_cell_counts(draws).sum()), (n - 1) * 10)

    def test_v315_overlap_probabilities_match_hypergeometric_enumeration(self):
        universe = set(range(28))
        pair = {0, 27}
        counts = [0, 0, 0]
        for draw in combinations(universe, 5):
            overlap = len(pair.intersection(draw))
            counts[overlap] += 1
        total = math.comb(28, 5)
        direct = np.asarray(counts, dtype=float) / total
        np.testing.assert_allclose(OVERLAP_PROBS, direct, rtol=0, atol=1e-15)
        self.assertAlmostEqual(float(OVERLAP_PROBS.sum()), 1.0, places=15)


if __name__ == "__main__":
    unittest.main()
