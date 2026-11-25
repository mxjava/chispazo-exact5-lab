"""Synthetic-only tests for the preregistered physical-covariate score test."""
from __future__ import annotations

import unittest

import numpy as np

from origen.physical_covariate_score_v1 import (
    REQUIRED_FEATURES,
    evaluate_physical_covariate_family,
)


def synthetic_epoch(*, biased: bool, seed: int = 20261125, draw_count: int = 160):
    rng = np.random.default_rng(seed)
    number_axis = np.linspace(-1.0, 1.0, 28)
    features = {
        "mass_g": 2.65 + 0.025 * number_axis,
        "diameter_mm": 38.0 + 0.08 * np.roll(number_axis, 5),
        "sphericity_index": 0.995 + 0.001 * np.roll(number_axis, 9),
        "surface_roughness_um": 0.8 + 0.12 * np.roll(number_axis, 13),
    }
    draws = []
    probabilities = np.exp(2.5 * number_axis) if biased else np.ones(28)
    probabilities = probabilities / probabilities.sum()
    for _ in range(draw_count):
        draw = rng.choice(28, size=5, replace=False, p=probabilities) + 1
        draws.append([int(value) for value in draw])
    return {
        "epoch_id": "SYNTHETIC-EPOCH-001",
        "machine_id": "SYNTHETIC-MACHINE",
        "ball_set_id": "SYNTHETIC-SET",
        "features_by_number": features,
        "draws": draws,
        "contest_ids": list(range(20000, 20000 + draw_count)),
    }


class TestPhysicalCovariateScoreV1(unittest.TestCase):
    def evaluate(self, epoch, **kwargs):
        return evaluate_physical_covariate_family(
            [epoch],
            modality="CLASSIC",
            scheduled_time_local="21:00",
            simulations=999,
            seed=99125,
            **kwargs,
        )

    def test_detects_large_synthetic_mass_association(self):
        result = self.evaluate(synthetic_epoch(biased=True, draw_count=500))
        mass = next(item for item in result.feature_scores if item.feature == "mass_g")
        self.assertLess(mass.holm_adjusted_p, 0.05)
        self.assertGreater(mass.z_score, 0.0)
        self.assertEqual(result.null_model, "INDEPENDENT_UNIFORM_5_OF_28_PER_CLASSIC_DRAW")

    def test_uniform_synthetic_draws_do_not_claim_a_signal(self):
        result = self.evaluate(synthetic_epoch(biased=False, seed=7, draw_count=500))
        self.assertGreater(result.familywise_monte_carlo_p, 0.01)
        self.assertEqual(result.draw_count, 500)

    def test_rejects_de_las_tres_modality(self):
        epoch = synthetic_epoch(biased=False)
        with self.assertRaisesRegex(ValueError, "CLASSIC at 21:00"):
            evaluate_physical_covariate_family(
                [epoch], modality="DE_LAS_TRES", scheduled_time_local="15:00"
            )

    def test_rejects_fewer_than_100_draws(self):
        epoch = synthetic_epoch(biased=False, draw_count=99)
        with self.assertRaisesRegex(ValueError, "at least 100"):
            self.evaluate(epoch)

    def test_rejects_duplicate_numbers_within_draw(self):
        epoch = synthetic_epoch(biased=False)
        epoch["draws"][0] = [1, 1, 2, 3, 4]
        with self.assertRaisesRegex(ValueError, "duplicate numbers"):
            self.evaluate(epoch)

    def test_rejects_duplicate_contest_ids_across_epochs(self):
        first = synthetic_epoch(biased=False)
        second = synthetic_epoch(biased=False, seed=8)
        second["epoch_id"] = "SYNTHETIC-EPOCH-002"
        second["contest_ids"][0] = first["contest_ids"][0]
        with self.assertRaisesRegex(ValueError, "unique across all epochs"):
            evaluate_physical_covariate_family(
                [first, second], modality="CLASSIC", scheduled_time_local="21:00",
                simulations=999, seed=99125
            )

    def test_rejects_incomplete_feature_schema(self):
        epoch = synthetic_epoch(biased=False)
        del epoch["features_by_number"]["surface_roughness_um"]
        with self.assertRaisesRegex(ValueError, "exactly"):
            self.evaluate(epoch)

    def test_rejects_constant_feature(self):
        epoch = synthetic_epoch(biased=False)
        epoch["features_by_number"]["mass_g"] = [2.65] * 28
        with self.assertRaisesRegex(ValueError, "must vary"):
            self.evaluate(epoch)

    def test_holm_adjusted_p_values_are_not_below_raw_p_values(self):
        result = self.evaluate(synthetic_epoch(biased=False, seed=11, draw_count=300))
        for item in result.feature_scores:
            self.assertGreaterEqual(item.holm_adjusted_p, item.monte_carlo_p)
            self.assertGreaterEqual(item.monte_carlo_p, 0.0)
            self.assertLessEqual(item.holm_adjusted_p, 1.0)

    def test_feature_order_is_fixed_and_complete(self):
        self.assertEqual(
            REQUIRED_FEATURES,
            ("diameter_mm", "mass_g", "sphericity_index", "surface_roughness_um"),
        )


if __name__ == "__main__":
    unittest.main()
