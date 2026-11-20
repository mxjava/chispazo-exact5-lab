"""V319 fixed-era contrast under independent uniform 5-of-28 null."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

from origen.exact5_modalities import assign_modality, read_history
from origen.v313_global_null import PICK, UNIVERSE, _matrix, _simulate_draws, _validate_binary_draw_matrix
from origen.v318_combinatorial_shape import (
    EXPECTED_SOURCE_SHA256,
    FEATURE_NAMES,
    _feature_codes,
    _universe_reference,
)

SIMULATIONS = 1999
SEED = 3192026
ERA_BOUNDARY = "2022-03-10"
NUMBER_PROB = PICK / UNIVERSE
PAIR_PROB = PICK * (PICK - 1) / (UNIVERSE * (UNIVERSE - 1))


def _sets_from_matrix(draws: np.ndarray) -> np.ndarray:
    matrix = _validate_binary_draw_matrix(draws)
    return np.sort(np.argsort(matrix, axis=1)[:, -PICK:] + 1, axis=1).astype(np.int16)


def _max_two_sample_z(
    counts_a: np.ndarray, counts_b: np.ndarray, probabilities: np.ndarray,
    n_a: int, n_b: int,
) -> float:
    p = np.asarray(probabilities, dtype=np.float64)
    a = np.asarray(counts_a, dtype=np.float64)
    b = np.asarray(counts_b, dtype=np.float64)
    if a.shape != p.shape or b.shape != p.shape or np.any(p < 0) or np.any(p > 1):
        raise ValueError("v319_invalid_category_count_or_probability_shape")
    valid = (p > 0) & (p < 1)
    if not np.any(valid):
        raise ValueError("v319_no_non_degenerate_categories")
    se = np.sqrt(p[valid] * (1.0 - p[valid]) * (1.0 / n_a + 1.0 / n_b))
    delta = a[valid] / n_a - b[valid] / n_b
    return float(np.max(np.abs(delta) / se))


def _category_counts(sets: np.ndarray, probabilities: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    features = _feature_codes(sets)
    return {
        name: np.bincount(features[name], minlength=len(probabilities[name])).astype(np.int64)
        for name in FEATURE_NAMES
    }


def _era_statistics(
    matrix_a: np.ndarray,
    matrix_b: np.ndarray,
    shape_probabilities: dict[str, np.ndarray],
) -> dict[str, float]:
    a = _validate_binary_draw_matrix(matrix_a)
    b = _validate_binary_draw_matrix(matrix_b)
    n_a, n_b = len(a), len(b)
    results: dict[str, float] = {}

    number_a = a.sum(axis=0, dtype=np.int64)
    number_b = b.sum(axis=0, dtype=np.int64)
    results["number_identity"] = _max_two_sample_z(
        number_a, number_b, np.full(UNIVERSE, NUMBER_PROB), n_a, n_b
    )

    wide_a = a.astype(np.int64, copy=False)
    wide_b = b.astype(np.int64, copy=False)
    pair_a = (wide_a.T @ wide_a)[np.triu_indices(UNIVERSE, 1)]
    pair_b = (wide_b.T @ wide_b)[np.triu_indices(UNIVERSE, 1)]
    results["pair_identity"] = _max_two_sample_z(
        pair_a, pair_b, np.full(math.comb(UNIVERSE, 2), PAIR_PROB), n_a, n_b
    )

    sets_a = _sets_from_matrix(a)
    sets_b = _sets_from_matrix(b)
    counts_a = _category_counts(sets_a, shape_probabilities)
    counts_b = _category_counts(sets_b, shape_probabilities)
    for name in FEATURE_NAMES:
        results[name] = _max_two_sample_z(
            counts_a[name], counts_b[name], shape_probabilities[name], n_a, n_b
        )
    return results


def run_v319(
    labelled: list[dict],
    source_sha256: str,
    simulations: int = SIMULATIONS,
    seed: int = SEED,
) -> dict:
    if simulations != SIMULATIONS or seed != SEED:
        raise ValueError("v319_frozen_simulations_and_seed_must_not_change")
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("v319_canonical_source_sha256_mismatch")

    classic = sorted(
        (row for row in labelled if row.get("draw_type") == "CLASSIC"),
        key=lambda row: int(row["contest"]),
    )
    era_a = [row for row in classic if row["date"] < ERA_BOUNDARY]
    era_b = [row for row in classic if row["date"] >= ERA_BOUNDARY]
    if len(era_a) < 1000 or len(era_b) < 1000:
        raise ValueError("v319_insufficient_rows_in_fixed_era")
    if not era_a or era_a[-1]["date"] >= ERA_BOUNDARY or not era_b or era_b[0]["date"] < ERA_BOUNDARY:
        raise ValueError("v319_fixed_era_boundary_integrity_failure")

    matrix_a = _matrix(era_a)
    matrix_b = _matrix(era_b)
    _, shape_probabilities, _ = _universe_reference()
    observed_families = _era_statistics(matrix_a, matrix_b, shape_probabilities)
    observed_global = max(observed_families.values())

    rng = np.random.default_rng(seed)
    null_global = np.empty(simulations, dtype=np.float64)
    null_by_family = {name: np.empty(simulations, dtype=np.float64) for name in observed_families}
    for index in range(simulations):
        sim_a = _simulate_draws(rng, len(era_a))
        sim_b = _simulate_draws(rng, len(era_b))
        stats = _era_statistics(sim_a, sim_b, shape_probabilities)
        for name, value in stats.items():
            null_by_family[name][index] = value
        null_global[index] = max(stats.values())

    exceedances = int(np.count_nonzero(null_global >= observed_global))
    global_p = (1 + exceedances) / (simulations + 1)
    family_results = {}
    for name, value in observed_families.items():
        p = (1 + int(np.count_nonzero(null_by_family[name] >= value))) / (simulations + 1)
        family_results[name] = {
            "observed_max_abs_z": value,
            "null_95th_percentile": float(np.quantile(null_by_family[name], 0.95)),
            "descriptive_monte_carlo_p": float(p),
        }

    return {
        "candidate": "V319_FIXED_ERA_CONTRAST",
        "classification": "NO_ERA_DIFFERENCE_DETECTED" if global_p >= 0.05 else "HISTORICAL_ERA_DIFFERENCE_ONLY",
        "draw_stream": "CLASSIC_ONLY",
        "source_sha256": source_sha256,
        "era_boundary": ERA_BOUNDARY,
        "era_a": {
            "label": "before_boundary",
            "n": len(era_a),
            "first_contest": int(era_a[0]["contest"]),
            "last_contest": int(era_a[-1]["contest"]),
            "last_date": era_a[-1]["date"],
        },
        "era_b": {
            "label": "on_or_after_boundary",
            "n": len(era_b),
            "first_contest": int(era_b[0]["contest"]),
            "last_contest": int(era_b[-1]["contest"]),
            "first_date": era_b[0]["date"],
        },
        "simulations": simulations,
        "seed": seed,
        "family_size": 28 + math.comb(UNIVERSE, 2) + sum(
            int(np.count_nonzero(shape_probabilities[name])) for name in FEATURE_NAMES
        ),
        "family_results_descriptive_only": family_results,
        "primary_global_max_abs_z": observed_global,
        "primary_null_95th_percentile": float(np.quantile(null_global, 0.95)),
        "primary_monte_carlo_exceedances": exceedances,
        "primary_monte_carlo_p_value": float(global_p),
        "interpretation": (
            "A rejection indicates a historical distribution difference across the fixed era boundary only. "
            "It does not identify a machine, sphere set, causal mechanism, or predictive edge."
        ),
        "warning": (
            "The date boundary is inherited from V265 and is not proof of equipment identity. "
            "Classic modality labels remain structurally derived, not row-by-row verified."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=SIMULATIONS)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    rows, digest = read_history(args.history)
    labelled, _ = assign_modality(rows)
    report = run_v319(labelled, digest, args.simulations, args.seed)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    (output / "v319_fixed_era_contrast_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
