from __future__ import annotations

import itertools
import math
import unittest

from origen.plackett_luce import (
    DRAW_SIZE, N_SPHERES, enumerate_set_log_probabilities,
    log_likelihood_ratio, log_plackett_luce_set_probability,
    log_uniform_set_probability, mass_log_weights, prequential_e_process,
)


class PlackettLuceTests(unittest.TestCase):
    def test_uniform_weights_recover_exact_uniform_five_of_28(self):
        log_weights = (0.0,) * 28
        observed = log_plackett_luce_set_probability(log_weights, (1, 2, 3, 4, 5))
        self.assertAlmostEqual(observed, -math.log(math.comb(28, 5)), places=13)
        self.assertAlmostEqual(log_likelihood_ratio(log_weights, (1, 2, 3, 4, 5)), 0.0, places=13)

    def test_unordered_set_probability_matches_explicit_120_orderings(self):
        log_weights = tuple(math.log(0.8 + i / 20) for i in range(28))
        chosen = (2, 7, 13, 19, 28)
        explicit = []
        for ordering in itertools.permutations(chosen):
            remaining = list(range(1, 29))
            logp = 0.0
            for number in ordering:
                denominator = math.fsum(math.exp(log_weights[j - 1]) for j in remaining)
                logp += log_weights[number - 1] - math.log(denominator)
                remaining.remove(number)
            explicit.append(logp)
        peak = max(explicit)
        brute = peak + math.log(math.fsum(math.exp(x - peak) for x in explicit))
        actual = log_plackett_luce_set_probability(log_weights, chosen)
        self.assertAlmostEqual(actual, brute, places=13)

    def test_input_order_does_not_change_unordered_set_probability(self):
        logs = tuple((i - 13.5) / 10 for i in range(28))
        self.assertAlmostEqual(
            log_plackett_luce_set_probability(logs, (1, 8, 12, 20, 28)),
            log_plackett_luce_set_probability(logs, (28, 20, 12, 8, 1)),
            places=14,
        )

    def test_all_98280_five_sets_normalize_to_one(self):
        logs = tuple((i - 13.5) / 25 for i in range(28))
        probabilities = enumerate_set_log_probabilities(logs, DRAW_SIZE)
        self.assertEqual(len(probabilities), math.comb(28, 5))
        total = math.fsum(math.exp(value) for value in probabilities.values())
        self.assertAlmostEqual(total, 1.0, places=11)

    def test_mass_weights_center_and_standardize_before_beta(self):
        masses = [4.7 + i / 1000 for i in range(28)]
        logs = mass_log_weights(masses, 0.75)
        self.assertAlmostEqual(math.fsum(logs), 0.0, places=11)
        self.assertGreater(logs[-1], logs[0])
        reverse = mass_log_weights(masses, -0.75)
        self.assertAlmostEqual(logs[0], -reverse[0], places=13)

    def test_mass_standardization_is_stable_for_extreme_finite_values(self):
        masses = [1e308] * 27 + [1.0]
        logs = mass_log_weights(masses, 0.5)
        self.assertTrue(all(math.isfinite(value) for value in logs))
        self.assertGreater(logs[-1], logs[0])

    def test_log_weights_reject_booleans(self):
        with self.assertRaisesRegex(ValueError, "log_weights"):
            log_plackett_luce_set_probability((0.0,) * 27 + (True,), (1, 2, 3, 4, 5))

    def test_zero_beta_is_exactly_uniform(self):
        masses = [4.7 + i / 1000 for i in range(28)]
        self.assertEqual(mass_log_weights(masses, 0.0), (0.0,) * 28)

    def test_constant_masses_produce_uniform_weights(self):
        self.assertEqual(mass_log_weights([4.7] * 28, 5.0), (0.0,) * 28)

    def test_invalid_mass_and_beta_rejected(self):
        with self.assertRaisesRegex(ValueError, "28 masses"):
            mass_log_weights([4.7] * 27, 1.0)
        with self.assertRaisesRegex(ValueError, "finite and positive"):
            mass_log_weights([4.7] * 27 + [float("nan")], 1.0)
        with self.assertRaisesRegex(ValueError, "beta_per_sd"):
            mass_log_weights([4.7 + i / 100 for i in range(28)], float("inf"))
        with self.assertRaisesRegex(ValueError, "numeric values"):
            mass_log_weights([4.7] * 27 + [True], 1.0)
        with self.assertRaisesRegex(ValueError, "beta_per_sd"):
            mass_log_weights([4.7 + i / 100 for i in range(28)], True)
        with self.assertRaisesRegex(ValueError, "numeric values"):
            mass_log_weights([4.7] * 27 + [None], 1.0)

    def test_prequential_e_process_crosses_threshold_at_twenty(self):
        result = prequential_e_process([math.log(4), math.log(5)])
        self.assertTrue(result["threshold_20_crossed"])
        self.assertAlmostEqual(result["anytime_p_value"], 0.05, places=14)
        self.assertEqual(result["n_observations"], 2)

    def test_prequential_e_process_does_not_claim_evidence_for_nonpositive_path(self):
        result = prequential_e_process([-0.2, -0.1, 0.05])
        self.assertFalse(result["threshold_20_crossed"])
        self.assertEqual(result["anytime_p_value"], 1.0)

    def test_prequential_e_process_rejects_nonfinite_increment(self):
        with self.assertRaisesRegex(ValueError, "must be finite"):
            prequential_e_process([0.0, float("nan")])

    def test_invalid_draw_rejected(self):
        with self.assertRaisesRegex(ValueError, "distinct"):
            log_plackett_luce_set_probability((0.0,) * 28, (1, 2, 3, 4, 4))
        with self.assertRaisesRegex(ValueError, "integers"):
            log_plackett_luce_set_probability((0.0,) * 28, (1, 2, 3, 4, 29))
        with self.assertRaisesRegex(ValueError, "28 finite"):
            log_plackett_luce_set_probability((0.0,) * 27, (1, 2, 3, 4, 5))


if __name__ == "__main__":
    unittest.main()
