import unittest

import numpy as np

from origen.v326_diverse_portfolio import (
    greedy_diverse_selection, pair_mask, portfolio_diversity,
    random_portfolio_diversity_expectation,
)


class TestV326DiversePortfolio(unittest.TestCase):
    def test_pair_mask_counts_ten_distinct_pairs(self):
        self.assertEqual(pair_mask((1, 2, 3, 4, 5)).bit_count(), 10)

    def test_greedy_selection_increases_pair_coverage(self):
        combos = [
            (1, 2, 3, 4, 5),
            (1, 2, 3, 4, 6),
            (1, 2, 3, 4, 7),
            (1, 2, 3, 4, 8),
            (9, 10, 11, 12, 13),
            (14, 15, 16, 17, 18),
        ]
        pmf = np.array([0.30, 0.25, 0.20, 0.15, 0.06, 0.04])
        chosen = greedy_diverse_selection(
            pmf, combos, 3, 6, np.random.Generator(np.random.PCG64(1))
        )
        naive = [0, 1, 2]
        self.assertEqual(len(chosen), 3)
        self.assertEqual(len(set(chosen)), 3)
        self.assertGreater(
            portfolio_diversity([combos[i] for i in chosen])["unique_pairs"],
            portfolio_diversity([combos[i] for i in naive])["unique_pairs"],
        )

    def test_diversity_metrics_for_disjoint_portfolio(self):
        result = portfolio_diversity([
            (1, 2, 3, 4, 5),
            (6, 7, 8, 9, 10),
        ])
        self.assertEqual(result["unique_numbers"], 10)
        self.assertEqual(result["unique_pairs"], 20)
        self.assertEqual(result["mean_pairwise_overlap"], 0.0)

    def test_random_portfolio_reference_values(self):
        result = random_portfolio_diversity_expectation(30)
        self.assertAlmostEqual(result["expected_mean_pairwise_overlap"], 25 / 28)
        self.assertGreater(result["expected_unique_numbers"], 27.8)
        self.assertGreater(result["expected_unique_pairs"], 208.0)


if __name__ == "__main__":
    unittest.main()
