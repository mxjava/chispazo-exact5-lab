"""V316 identity-resolved temporal persistence omnibus (frozen design).

One global maximum statistic across 20 lags, 28 number identities, 378 pair
identities, and aggregate overlap. Monte Carlo null preserves exact 5-of-28
sampling. Research-only historical falsification; never a forecasting model.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from itertools import combinations
from pathlib import Path

import numpy as np

from origen.exact5_modalities import assign_modality, read_history
from origen.v313_global_null import PICK, UNIVERSE, _matrix, _simulate_draws, _validate_binary_draw_matrix

EXPECTED_SOURCE_SHA256 = "5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a"
EXPECTED_CLASSIC_DRAWS = 7723
EXPECTED_FIRST_CONTEST = 1363
EXPECTED_LAST_CONTEST = 12248
SIMULATIONS = 1999
SEED = 3162026
LAGS = tuple(range(1, 21))
PAIRS = tuple(combinations(range(UNIVERSE), 2))
P1 = PICK / UNIVERSE
P2 = PICK * (PICK - 1) / (UNIVERSE * (UNIVERSE - 1))
Q1 = P1 ** 2
Q2 = P2 ** 2
OVERLAP_MEAN = PICK * PICK / UNIVERSE
BIT_COUNTS = np.asarray([value.bit_count() for value in range(256)], dtype=np.uint8)
OVERLAP_VARIANCE = (
    PICK * P1 * (1.0 - P1) * (UNIVERSE - PICK) / (UNIVERSE - 1)
)


def _statistics_by_component(draws: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
    """Return max statistic and materialized aggregate/number/pair z arrays."""
    matrix = _validate_binary_draw_matrix(draws, min_rows=22)
    n = matrix.shape[0]
    aggregate_z = np.empty(len(LAGS), dtype=np.float64)
    number_z = np.empty((len(LAGS), UNIVERSE), dtype=np.float64)
    pair_z = np.empty((len(LAGS), len(PAIRS)), dtype=np.float64)
    pair_i = np.fromiter((i for i, _ in PAIRS), dtype=np.intp)
    pair_j = np.fromiter((j for _, j in PAIRS), dtype=np.intp)

    for lag_index, lag in enumerate(LAGS):
        common = matrix[:-lag] & matrix[lag:]
        transitions = n - lag

        overlap = common.sum(axis=1, dtype=np.int64)
        aggregate_mean = float(overlap.mean())
        aggregate_se = math.sqrt(OVERLAP_VARIANCE / transitions)
        aggregate_z[lag_index] = abs(aggregate_mean - OVERLAP_MEAN) / aggregate_se

        number_counts = common.sum(axis=0, dtype=np.int64)
        number_mean = transitions * Q1
        number_var = transitions * Q1 * (1.0 - Q1)
        number_z[lag_index] = np.abs(number_counts - number_mean) / math.sqrt(number_var)

        packed = np.packbits(common, axis=0, bitorder="little")
        pair_bits = packed[:, pair_i] & packed[:, pair_j]
        pair_counts = BIT_COUNTS[pair_bits].sum(axis=0, dtype=np.int64)
        pair_mean = transitions * Q2
        pair_var = transitions * Q2 * (1.0 - Q2)
        pair_z[lag_index] = np.abs(pair_counts - pair_mean) / math.sqrt(pair_var)

    maximum = max(
        float(aggregate_z.max()),
        float(number_z.max()),
        float(pair_z.max()),
    )
    return maximum, aggregate_z, number_z, pair_z


def _max_statistic(draws: np.ndarray) -> float:
    return _statistics_by_component(draws)[0]


def _reference_counts(draws: np.ndarray, lag: int) -> tuple[float, np.ndarray, np.ndarray]:
    """Deliberately simple nested-loop oracle for tests only."""
    matrix = _validate_binary_draw_matrix(draws, min_rows=lag + 1)
    n = matrix.shape[0]
    overlap_sum = 0
    number_counts = np.zeros(UNIVERSE, dtype=np.int64)
    pair_counts = np.zeros(len(PAIRS), dtype=np.int64)
    pair_index = {pair: idx for idx, pair in enumerate(PAIRS)}
    for t in range(n - lag):
        shared = np.flatnonzero(matrix[t] & matrix[t + lag])
        overlap_sum += len(shared)
        for value in shared:
            number_counts[value] += 1
        for pair in combinations(shared.tolist(), 2):
            pair_counts[pair_index[pair]] += 1
    return overlap_sum / (n - lag), number_counts, pair_counts


def run_v316(
    labelled: list[dict],
    source_sha256: str,
    simulations: int = SIMULATIONS,
    seed: int = SEED,
) -> dict:
    if simulations != SIMULATIONS or seed != SEED:
        raise ValueError("v316_frozen_simulations_and_seed_must_not_change")
    if source_sha256 != EXPECTED_SOURCE_SHA256:
        raise ValueError("v316_canonical_source_sha256_mismatch")
    classic = sorted(
        (row for row in labelled if row.get("draw_type") == "CLASSIC"),
        key=lambda row: int(row["contest"]),
    )
    if len(classic) != EXPECTED_CLASSIC_DRAWS:
        raise ValueError("v316_classic_draw_count_mismatch")
    if int(classic[0]["contest"]) != EXPECTED_FIRST_CONTEST or int(classic[-1]["contest"]) != EXPECTED_LAST_CONTEST:
        raise ValueError("v316_classic_contest_boundaries_mismatch")

    observed_draws = _matrix(classic)
    observed_max, aggregate_z, number_z, pair_z = _statistics_by_component(observed_draws)
    rng = np.random.default_rng(seed)
    null_max = np.empty(simulations, dtype=np.float64)
    started = time.perf_counter()
    for index in range(simulations):
        null_max[index] = _max_statistic(_simulate_draws(rng, len(classic)))
    elapsed = time.perf_counter() - started
    exceedances = int(np.count_nonzero(null_max >= observed_max))
    p_value = (1 + exceedances) / (simulations + 1)

    max_location = int(np.argmax(np.concatenate((aggregate_z.ravel(), number_z.ravel(), pair_z.ravel()))))
    if max_location < len(LAGS):
        component = "aggregate_overlap"
        lag = LAGS[max_location]
        identity = None
        observed_cell_z = float(aggregate_z.ravel()[max_location])
    elif max_location < len(LAGS) + number_z.size:
        local = max_location - len(LAGS)
        lag_index, number_index = divmod(local, UNIVERSE)
        component = "number_identity"
        lag = LAGS[lag_index]
        identity = number_index + 1
        observed_cell_z = float(number_z[lag_index, number_index])
    else:
        local = max_location - len(LAGS) - number_z.size
        lag_index, pair_index = divmod(local, len(PAIRS))
        component = "pair_identity"
        lag = LAGS[lag_index]
        identity = [PAIRS[pair_index][0] + 1, PAIRS[pair_index][1] + 1]
        observed_cell_z = float(pair_z[lag_index, pair_index])

    return {
        "candidate": "V316_IDENTITY_RESOLVED_TEMPORAL_PERSISTENCE",
        "classification": "RESEARCH_ONLY_HISTORICAL_FALSIFICATION_NOT_PREDICTIVE_EDGE",
        "draw_stream": "CLASSIC_ONLY",
        "n_classic_draws": len(classic),
        "first_contest": int(classic[0]["contest"]),
        "last_contest": int(classic[-1]["contest"]),
        "source_sha256": source_sha256,
        "family_size": len(LAGS) + len(LAGS) * UNIVERSE + len(LAGS) * len(PAIRS),
        "lags": list(LAGS),
        "simulations": simulations,
        "seed": seed,
        "observed_max_abs_z": observed_max,
        "null_95th_percentile": float(np.quantile(null_max, 0.95)),
        "monte_carlo_exceedances": exceedances,
        "monte_carlo_p_value": float(p_value),
        "strongest_cell_descriptive_only": {
            "component": component, "lag": lag, "identity": identity,
            "absolute_standardized_value": observed_cell_z,
        },
        "runtime_seconds": elapsed,
        "interpretation": "One global maximum-statistic test of historical identity-resolved temporal persistence. Rejection would not establish causality or prospective predictive advantage.",
        "warning": "Retrospective falsification only. No candidate selection, forecast, or betting edge."
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
    report = run_v316(labelled, digest, args.simulations, args.seed)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    (output / "v316_identity_persistence_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
