"""V318 fixed combinatorial-shape omnibus under uniform 5-of-28 null."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np

from origen.exact5_modalities import assign_modality, read_history
from origen.v313_global_null import PICK, UNIVERSE, _matrix, _simulate_draws, _validate_binary_draw_matrix

SIMULATIONS = 1999
SEED = 3182026
EXPECTED_SOURCE_SHA256 = "5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a"
EXPECTED_CLASSIC_DRAWS = 7723
EXPECTED_FIRST_CONTEST = 1363
EXPECTED_LAST_CONTEST = 12248
PRIMES = np.asarray([2, 3, 5, 7, 11, 13, 17, 19, 23], dtype=np.int16)
FEATURE_NAMES = (
    "sum",
    "range",
    "odd_count",
    "prime_count",
    "adjacent_consecutive_pairs",
    "low_1_to_14_count",
    "three_band_occupancy",
)


def _feature_codes(sorted_numbers: np.ndarray) -> dict[str, np.ndarray]:
    """Encode seven frozen shape summaries for rows of sorted 5-number sets."""
    values = np.asarray(sorted_numbers)
    if values.ndim != 2 or values.shape[1] != PICK:
        raise ValueError("v318_sets_must_have_shape_n_by_5")
    if not np.issubdtype(values.dtype, np.integer):
        raise ValueError("v318_numbers_must_be_integers")
    if np.any(values < 1) or np.any(values > UNIVERSE):
        raise ValueError("v318_numbers_outside_1_to_28")
    if np.any(np.diff(values, axis=1) <= 0):
        raise ValueError("each set must be sorted and distinct")

    band1 = np.sum((values >= 1) & (values <= 9), axis=1)
    band2 = np.sum((values >= 10) & (values <= 19), axis=1)
    band3 = np.sum((values >= 20) & (values <= 28), axis=1)
    band_code = (band1 * 6 + band2) * 6 + band3
    return {
        "sum": values.sum(axis=1).astype(np.int16),
        "range": (values[:, -1] - values[:, 0]).astype(np.int8),
        "odd_count": (values % 2).sum(axis=1).astype(np.int8),
        "prime_count": np.isin(values, PRIMES).sum(axis=1).astype(np.int8),
        "adjacent_consecutive_pairs": (np.diff(values, axis=1) == 1).sum(axis=1).astype(np.int8),
        "low_1_to_14_count": (values <= 14).sum(axis=1).astype(np.int8),
        "three_band_occupancy": band_code.astype(np.int16),
    }


def _sets_from_matrix(draws: np.ndarray) -> np.ndarray:
    matrix = _validate_binary_draw_matrix(draws)
    return np.sort(np.argsort(matrix, axis=1)[:, -PICK:] + 1, axis=1).astype(np.int16)


def _universe_reference() -> tuple[np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]]:
    universe = np.asarray(list(combinations(range(1, UNIVERSE + 1), PICK)), dtype=np.int16)
    if universe.shape != (math.comb(UNIVERSE, PICK), PICK):
        raise RuntimeError("v318_universe_cardinality_mismatch")
    codes = _feature_codes(universe)
    probabilities: dict[str, np.ndarray] = {}
    category_counts: dict[str, np.ndarray] = {}
    for name in FEATURE_NAMES:
        max_code = int(codes[name].max()) + 1
        counts = np.bincount(codes[name], minlength=max_code).astype(np.int64)
        if counts.sum() != len(universe) or np.any(counts < 0):
            raise RuntimeError(f"v318_invalid_universe_counts:{name}")
        category_counts[name] = counts
        probabilities[name] = counts.astype(np.float64) / len(universe)
    return universe, probabilities, category_counts


def _family_max_z(codes: np.ndarray, probabilities: np.ndarray, n: int) -> float:
    counts = np.bincount(codes, minlength=len(probabilities)).astype(np.int64)
    valid = probabilities > 0
    expected = n * probabilities[valid]
    variance = n * probabilities[valid] * (1.0 - probabilities[valid])
    if np.any(variance <= 0):
        raise RuntimeError("v318_nonpositive_category_variance")
    return float(np.max(np.abs(counts[valid] - expected) / np.sqrt(variance)))


def _statistics_for_sets(
    sets: np.ndarray, probabilities: dict[str, np.ndarray]
) -> dict[str, float]:
    features = _feature_codes(sets)
    n = len(sets)
    return {
        name: _family_max_z(features[name], probabilities[name], n)
        for name in FEATURE_NAMES
    }


def run_v318(
    labelled: list[dict],
    source_sha256: str,
    simulations: int = SIMULATIONS,
    seed: int = SEED,
) -> dict:
    if simulations != SIMULATIONS or seed != SEED:
        raise ValueError("v318_frozen_simulations_and_seed_must_not_change")
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("v318_canonical_source_sha256_mismatch")
    classic = sorted(
        (row for row in labelled if row.get("draw_type") == "CLASSIC"),
        key=lambda row: int(row["contest"]),
    )
    if len(classic) != EXPECTED_CLASSIC_DRAWS:
        raise ValueError("v318_classic_draw_count_mismatch")
    if int(classic[0]["contest"]) != EXPECTED_FIRST_CONTEST or int(classic[-1]["contest"]) != EXPECTED_LAST_CONTEST:
        raise ValueError("v318_classic_contest_boundaries_mismatch")

    observed_matrix = _matrix(classic)
    observed_sets = _sets_from_matrix(observed_matrix)
    _, probabilities, category_counts = _universe_reference()
    observed_family = _statistics_for_sets(observed_sets, probabilities)
    observed_global = max(observed_family.values())

    rng = np.random.default_rng(seed)
    null_global = np.empty(simulations, dtype=np.float64)
    null_by_family = {name: np.empty(simulations, dtype=np.float64) for name in FEATURE_NAMES}
    for index in range(simulations):
        simulated_sets = _sets_from_matrix(_simulate_draws(rng, len(classic)))
        stats = _statistics_for_sets(simulated_sets, probabilities)
        for name in FEATURE_NAMES:
            null_by_family[name][index] = stats[name]
        null_global[index] = max(stats.values())

    exceedances = int(np.count_nonzero(null_global >= observed_global))
    global_p = (1 + exceedances) / (simulations + 1)
    family_results = {}
    for name in FEATURE_NAMES:
        family_exceed = int(np.count_nonzero(null_by_family[name] >= observed_family[name]))
        family_results[name] = {
            "observed_max_abs_z": observed_family[name],
            "null_95th_percentile": float(np.quantile(null_by_family[name], 0.95)),
            "descriptive_monte_carlo_p": float((1 + family_exceed) / (simulations + 1)),
            "category_count": int(np.count_nonzero(probabilities[name] > 0)),
        }

    return {
        "candidate": "V318_COMBINATORIAL_SHAPE_OMNIBUS",
        "classification": "NO_REJECTION" if global_p >= 0.05 else "HISTORICAL_SHAPE_DEPARTURE_ONLY",
        "draw_stream": "CLASSIC_ONLY",
        "n_classic_draws": len(classic),
        "first_contest": int(classic[0]["contest"]),
        "last_contest": int(classic[-1]["contest"]),
        "source_sha256": source_sha256,
        "simulations": simulations,
        "seed": seed,
        "universe_size": math.comb(UNIVERSE, PICK),
        "feature_families": list(FEATURE_NAMES),
        "family_results_descriptive_only": family_results,
        "primary_global_max_abs_z": observed_global,
        "primary_null_95th_percentile": float(np.quantile(null_global, 0.95)),
        "primary_monte_carlo_exceedances": exceedances,
        "primary_monte_carlo_p_value": float(global_p),
        "primary_family_size": sum(result["category_count"] for result in family_results.values()),
        "null_category_counts": {
            name: int(np.count_nonzero(category_counts[name])) for name in FEATURE_NAMES
        },
        "interpretation": (
            "A global rejection indicates only a historical draw-shape departure in this frozen family. "
            "It is not a number-level signal, physical mechanism, causal result, or prospective edge."
        ),
        "warning": (
            "Retrospective Classic-only shape falsification. The modality mapping remains structurally "
            "derived, not row-by-row verified against every official act. No prospective custody."
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
    report = run_v318(labelled, digest, args.simulations, args.seed)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    (output / "v318_combinatorial_shape_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
