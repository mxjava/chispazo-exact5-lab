import unittest
import numpy as np

from src.v265.CHISPAZO_V265_PHYSICAL_REGIME_SCANNER import (
    TRIPLE_P, exact_binomial_pvalues, holm_adjust,
)


class ExactBinomialPersistenceTests(unittest.TestCase):
    def test_25_occurrences_exact_tail_is_not_normal_approximation(self):
        p = exact_binomial_pvalues([25], 3297, TRIPLE_P)[0]
        self.assertAlmostEqual(p, 5.0174698279902004e-05, places=13)
        self.assertGreater(p, 2.4e-06)

    def test_familywise_adjustment_removes_25_count_triple_signal(self):
        counts = np.array([25] + [10] * 3275)
        raw = exact_binomial_pvalues(counts, 3297, TRIPLE_P)
        adjusted = holm_adjust(raw)
        self.assertGreaterEqual(adjusted[0], 0.05)
        self.assertAlmostEqual(adjusted[0], 3276 * raw[0], places=10)

    def test_rejects_invalid_inputs(self):
        for counts, trials, probability in (
            ([1.5], 100, TRIPLE_P),
            ([101], 100, TRIPLE_P),
            ([1], 0, TRIPLE_P),
            ([1], 100, 1.0),
        ):
            with self.subTest(counts=counts, trials=trials, probability=probability):
                with self.assertRaises(ValueError):
                    exact_binomial_pvalues(counts, trials, probability)


if __name__ == "__main__":
    unittest.main()
