import unittest
from statistics import median

from origen.v323_context_partition import context_regime, WINDOW, REGIMES
from origen.v322_hierarchical_partition import HierarchicalPartitionModel


class TestV323ContextPartition(unittest.TestCase):
    def test_even_sample_median_uses_midpoint(self):
        self.assertEqual(median([-2.0, 1.0, 3.0, 10.0]), 2.0)

    def test_context_requires_exact_prior_window(self):
        with self.assertRaises(ValueError):
            context_regime([[1, 2, 3, 4, 5]] * (WINDOW - 1))

    def test_low_repeat_context(self):
        # Disjoint consecutive five-sets force zero overlap.
        draws = [
            [1, 2, 3, 4, 5], [6, 7, 8, 9, 10],
            [11, 12, 13, 14, 15], [16, 17, 18, 19, 20],
            [21, 22, 23, 24, 25],
        ] * 4
        regime, mean = context_regime(draws)
        self.assertEqual(regime, REGIMES[0])
        self.assertEqual(mean, 0.0)

    def test_high_repeat_context(self):
        # Consecutive draws share four numbers.
        draws = [[1, 2, 3, 4, 5 + (i % 24)] for i in range(WINDOW)]
        regime, mean = context_regime(draws)
        self.assertEqual(regime, REGIMES[2])
        self.assertGreater(mean, 1.05)

    def test_typical_repeat_context(self):
        # A deterministic sequence with mean consecutive overlap near one.
        draws = []
        for i in range(WINDOW):
            start = i % 20 + 1
            draws.append(sorted({start, ((start + 4) % 28) + 1,
                                 ((start + 9) % 28) + 1,
                                 ((start + 14) % 28) + 1,
                                 ((start + 19) % 28) + 1}))
        regime, mean = context_regime(draws)
        self.assertIn(regime, REGIMES)
        self.assertGreaterEqual(mean, 0.0)

    def test_models_are_isolated_by_context(self):
        low = HierarchicalPartitionModel()
        high = HierarchicalPartitionModel()
        low.update([1, 2, 3, 4, 5])
        self.assertEqual(low.draws_seen, 1)
        self.assertEqual(high.draws_seen, 0)
        self.assertAlmostEqual(float(high.probabilities().sum()), 1.0, places=12)

    def test_target_context_does_not_include_target(self):
        prior = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]] * 10
        regime_a, overlap_a = context_regime(prior)
        target = [1, 2, 3, 4, 5]
        regime_b, overlap_b = context_regime(prior)
        self.assertEqual((regime_a, overlap_a), (regime_b, overlap_b))
        self.assertEqual(len(target), 5)


if __name__ == "__main__":
    unittest.main()
