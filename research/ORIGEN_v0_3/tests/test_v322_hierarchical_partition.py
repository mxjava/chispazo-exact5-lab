import math
import unittest

import numpy as np

from origen.v322_hierarchical_partition import (
    ALPHA,
    UNIVERSE_SIZE,
    HierarchicalPartitionModel,
    candidate_features,
)


class TestV322HierarchicalPartition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = HierarchicalPartitionModel()

    def test_universe_is_exactly_98280_unique_sets(self):
        self.assertEqual(len(self.model.combinations), 98280)
        self.assertEqual(len(set(self.model.combinations)), 98280)
        self.assertEqual(UNIVERSE_SIZE, 98280)

    def test_each_tree_and_equal_mixture_are_normalized_before_data(self):
        for tree in self.model.trees:
            leaf_p = tree.leaf_probabilities(0, ALPHA)
            self.assertTrue(np.all(leaf_p > 0))
            self.assertAlmostEqual(float(leaf_p.sum()), 1.0, places=12)
        pmf = self.model.probabilities()
        self.assertTrue(np.all(pmf > 0))
        self.assertAlmostEqual(float(pmf.sum()), 1.0, places=12)
        self.assertAlmostEqual(float(pmf.min()), 1.0 / UNIVERSE_SIZE, delta=1e-15)
        self.assertAlmostEqual(float(pmf.max()), 1.0 / UNIVERSE_SIZE, delta=1e-15)

    def test_prior_update_preserves_normalization(self):
        model = HierarchicalPartitionModel()
        for draw in ([1, 2, 3, 4, 5], [6, 9, 12, 20, 28], [2, 7, 13, 19, 25]):
            model.update(draw)
            pmf = model.probabilities()
            self.assertAlmostEqual(float(pmf.sum()), 1.0, places=12)
            self.assertTrue(np.all(np.isfinite(pmf)))
            self.assertTrue(np.all(pmf > 0))

    def test_target_is_scored_before_it_is_added(self):
        model = HierarchicalPartitionModel()
        model.update([1, 2, 3, 4, 5])
        before = model.probabilities().copy()
        score = model.score([6, 9, 12, 20, 28])
        self.assertEqual(model.draws_seen, 1)
        np.testing.assert_array_equal(before, model.probabilities())
        self.assertGreater(score["target_probability"], 0)
        self.assertLessEqual(score["top_30_inclusion_probability"], 1)
        self.assertGreaterEqual(score["top_30_inclusion_probability"], 0)
        self.assertLessEqual(score["rank_low"], score["rank_high"])
        self.assertEqual(score["tie_size"], score["rank_high"] - score["rank_low"] + 1)

    def test_future_observation_cannot_change_already_computed_score(self):
        a = HierarchicalPartitionModel()
        b = HierarchicalPartitionModel()
        prior = ([1, 2, 3, 4, 5], [6, 9, 12, 20, 28], [2, 7, 13, 19, 25])
        for draw in prior:
            a.update(draw)
            b.update(draw)
        target = [4, 8, 15, 22, 27]
        score_a = a.score(target)
        score_b = b.score(target)
        self.assertEqual(score_a, score_b)
        b.update([3, 10, 14, 21, 26])
        self.assertEqual(a.draws_seen, 3)
        self.assertEqual(b.draws_seen, 4)
        self.assertEqual(score_a, score_b)

    def test_invalid_draws_and_alpha_fail_closed(self):
        with self.assertRaises(ValueError):
            candidate_features((1, 1, 2, 3, 4))
        with self.assertRaises(ValueError):
            HierarchicalPartitionModel(alpha=0)
        with self.assertRaises(ValueError):
            self.model.update([1, 2, 3, 4, 29])

    def test_rank_and_top_k_ties_are_probability_aware(self):
        model = HierarchicalPartitionModel()
        model.update([1, 2, 3, 4, 5])
        result = model.score([1, 2, 3, 4, 5])
        self.assertGreaterEqual(result["rank_low"], 1)
        self.assertLessEqual(result["rank_high"], UNIVERSE_SIZE)
        for k in (1, 5, 10, 30, 100):
            value = result[f"top_{k}_inclusion_probability"]
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main()
