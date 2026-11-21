import unittest

import numpy as np

from origen.v325_portfolio_hit_audit import (
    portfolio_hit_counts, random_portfolio_expectations, select_top_k,
)


class TestV325PortfolioHitAudit(unittest.TestCase):
    def test_top_k_is_exact_and_ties_are_seed_reproducible(self):
        pmf = np.array([0.5, 0.3, 0.1, 0.1, 0.0])
        a = select_top_k(pmf, 3, np.random.Generator(np.random.PCG64(7)))
        b = select_top_k(pmf, 3, np.random.Generator(np.random.PCG64(7)))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 3)
        self.assertEqual(set(a[:2]), {0, 1})
        self.assertIn(a[2], {2, 3})

    def test_portfolio_overlap_counts_exactly(self):
        target = (1, 2, 3, 4, 5)
        portfolio = [
            (1, 2, 3, 4, 5),  # 5/5
            (1, 2, 3, 4, 6),  # 4/5
            (1, 2, 3, 7, 8),  # 3/5
            (1, 2, 9, 10, 11),  # 2/5
        ]
        self.assertEqual(portfolio_hit_counts(portfolio, target), {
            "hits_3of5": 1, "hits_4of5": 1, "hits_5of5": 1,
            "hits_at_least_3": 3, "hits_at_least_4": 2,
            "best_match": 5,
        })

    def test_uniform_expectation_has_correct_5of5_rate(self):
        e = random_portfolio_expectations(100, 30)
        self.assertAlmostEqual(e["5of5"]["expected_hit_lines"], 30 * 100 / 98280)
        self.assertAlmostEqual(e["5of5"]["expected_targets_with_at_least_one"], 30 * 100 / 98280, places=10)

    def test_top_k_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            select_top_k(np.array([0.5, 0.5]), 0, np.random.default_rng(1))
        with self.assertRaises(ValueError):
            select_top_k(np.array([0.5, np.nan]), 1, np.random.default_rng(1))


if __name__ == "__main__":
    unittest.main()
