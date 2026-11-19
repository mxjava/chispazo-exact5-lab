"""V313 global falsification tests under independent uniform 5-of-28 draws.

Research-only diagnostics. Monte Carlo calibration preserves the exact
fixed-size, without-replacement draw structure and uses max statistics to
account for within-family multiplicity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from origen.exact5_modalities import assign_modality, read_history

UNIVERSE = 28
PICK = 5
PAIRS = tuple((i, j) for i in range(UNIVERSE) for j in range(i + 1, UNIVERSE))
LAGS = tuple(range(1, 21))


def _matrix(rows: list[dict]) -> np.ndarray:
    matrix = np.zeros((len(rows), UNIVERSE), dtype=np.int8)
    for i, row in enumerate(rows):
        nums = row["numbers"]
        if len(nums) != PICK or len(set(nums)) != PICK or any(type(n) is not int or not 1 <= n <= UNIVERSE for n in nums):
            raise ValueError("invalid_draw_for_v313")
        matrix[i, np.asarray(nums, dtype=int) - 1] = 1
    return matrix


def _standardized_max(counts: np.ndarray, expected: float, variance: float) -> float:
    if variance <= 0:
        raise ValueError("nonpositive_null_variance")
    return float(np.max(np.abs(counts - expected) / math.sqrt(variance)))


def _statistics(draws: np.ndarray) -> tuple[float, float, float]:
    n = draws.shape[0]
    if draws.ndim != 2 or draws.shape[1] != UNIVERSE or n < 2 or not np.all(draws.sum(axis=1) == PICK):
        raise ValueError("invalid_v313_matrix")
    inclusion = draws.sum(axis=0)
    p = PICK / UNIVERSE
    number_var = n * p * (1.0 - p)
    number_stat = _standardized_max(inclusion, n * p, number_var)

    pair_counts = []
    for i, j in PAIRS:
        pair_counts.append(int(np.dot(draws[:, i], draws[:, j])))
    pair_p = PICK * (PICK - 1) / (UNIVERSE * (UNIVERSE - 1))
    pair_var = n * pair_p * (1.0 - pair_p)
    pair_stat = _standardized_max(np.asarray(pair_counts), n * pair_p, pair_var)

    temporal_stats = []
    for lag in LAGS:
        overlaps = np.sum(draws[lag:] * draws[:-lag], axis=1)
        # Under independent uniform 5-subsets, E[overlap] = 25/28.
        # Variance is calibrated by the same Monte Carlo null below; this
        # scale-free raw deviation is the preregistered max statistic.
        temporal_stats.append(abs(float(np.mean(overlaps)) - PICK * PICK / UNIVERSE))
    temporal_stat = max(temporal_stats)
    return number_stat, pair_stat, temporal_stat


def _simulate_draws(rng: np.random.Generator, n: int) -> np.ndarray:
    # Sorting five independent continuous uniforms gives a uniform 5-subset
    # after selecting the five smallest among 28 iid keys.
    keys = rng.random((n, UNIVERSE))
    chosen = np.argpartition(keys, PICK - 1, axis=1)[:, :PICK]
    matrix = np.zeros((n, UNIVERSE), dtype=np.int8)
    rows = np.arange(n)[:, None]
    matrix[rows, chosen] = 1
    return matrix


def run_v313(labelled: list[dict], source_sha256: str, simulations: int = 1999, seed: int = 3132026) -> dict:
    if simulations < 999:
        raise ValueError("simulations_must_be_at_least_999")
    classic = sorted((r for r in labelled if r.get("draw_type") == "CLASSIC"), key=lambda r: int(r["contest"]))
    if len(classic) < 1000:
        raise ValueError("insufficient_classic_draws")
    observed_matrix = _matrix(classic)
    observed = _statistics(observed_matrix)
    null = np.empty((simulations, 3), dtype=float)
    rng = np.random.default_rng(seed)
    for b in range(simulations):
        null[b, :] = _statistics(_simulate_draws(rng, len(classic)))
    # Add-one Monte Carlo p-values; family-wise maxima already included for
    # numbers (28), pairs (378), and temporal lags (1..20).
    p_values = [(1 + int(np.count_nonzero(null[:, k] >= observed[k]))) / (simulations + 1) for k in range(3)]
    names = ("number_balance_max_z", "pair_balance_max_z", "temporal_overlap_max_deviation")
    raw = {names[k]: float(observed[k]) for k in range(3)}
    null_q95 = {names[k]: float(np.quantile(null[:, k], 0.95)) for k in range(3)}
    ordered = sorted(p_values)
    holm = [0.0, 0.0, 0.0]
    running = 0.0
    for rank, (idx, pval) in enumerate(sorted(enumerate(p_values), key=lambda x: x[1])):
        adjusted = min(1.0, (3 - rank) * pval)
        running = max(running, adjusted)
        holm[idx] = running
    return {
        "candidate": "V313_GLOBAL_NULL_FALSIFICATION",
        "classification": "RESEARCH_ONLY_HISTORICAL_FALSIFICATION_NOT_PREDICTIVE_EDGE",
        "draw_stream": "CLASSIC_ONLY",
        "n_classic_draws": len(classic),
        "first_contest": classic[0]["contest"],
        "last_contest": classic[-1]["contest"],
        "source_sha256": source_sha256,
        "simulations": simulations,
        "seed": seed,
        "statistics": raw,
        "null_95th_percentiles": null_q95,
        "monte_carlo_p_values": dict(zip(names, p_values)),
        "holm_adjusted_p_values": dict(zip(names, holm)),
        "holm_family_alpha": 0.05,
        "interpretation": "A rejected global null is evidence of historical non-uniformity/dependence only. It is not a forecast, causal explanation, or prospective edge.",
        "warning": "Historical discovery only. No row-level official source audit, prospective custody, or prediction validation is established."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=1999)
    parser.add_argument("--seed", type=int, default=3132026)
    args = parser.parse_args()
    rows, digest = read_history(args.history)
    labelled, _ = assign_modality(rows)
    report = run_v313(labelled, digest, args.simulations, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "v313_global_null_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
