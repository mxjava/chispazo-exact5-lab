"""V314 higher-order triple motif max-statistic falsification."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
from origen.exact5_modalities import assign_modality, read_history
from origen.v313_global_null import PICK, UNIVERSE, _matrix, _simulate_draws

TRIPLES = tuple((i, j, k) for i in range(UNIVERSE) for j in range(i + 1, UNIVERSE) for k in range(j + 1, UNIVERSE))
TRIPLE_P = 5 / 1638


def _triple_counts(draws: np.ndarray) -> np.ndarray:
    if draws.ndim != 2 or draws.shape[1] != UNIVERSE or draws.shape[0] < 2 or not np.all(draws.sum(axis=1) == PICK):
        raise ValueError("invalid_v314_matrix")
    # For each pair (i,j), count rows containing the pair, then multiply by
    # every number indicator. Selecting k>j yields each unordered triple once.
    pairs = [(i, j) for i in range(UNIVERSE) for j in range(i + 1, UNIVERSE)]
    pair_indicators = np.empty((draws.shape[0], len(pairs)), dtype=np.int32)
    for col, (i, j) in enumerate(pairs):
        pair_indicators[:, col] = draws[:, i] * draws[:, j]
    counts_by_pair_number = pair_indicators.T @ draws.astype(np.int32, copy=False)
    counts = [int(counts_by_pair_number[col, k]) for col, (i, j) in enumerate(pairs) for k in range(j + 1, UNIVERSE)]
    return np.asarray(counts, dtype=np.int32)


def _triple_max_z(draws: np.ndarray) -> float:
    n = draws.shape[0]
    counts = _triple_counts(draws)
    variance = n * TRIPLE_P * (1.0 - TRIPLE_P)
    return float(np.max(np.abs(counts - n * TRIPLE_P) / math.sqrt(variance)))


def _winning_triple(draws: np.ndarray) -> dict:
    counts = _triple_counts(draws)
    n = draws.shape[0]
    z = np.abs(counts - n * TRIPLE_P) / math.sqrt(n * TRIPLE_P * (1.0 - TRIPLE_P))
    idx = int(np.argmax(z))
    triple = TRIPLES[idx]
    return {"numbers": [x + 1 for x in triple], "count": int(counts[idx]),
            "expected_count": float(n * TRIPLE_P), "standardized_deviation": float(z[idx]),
            "direction": "excess" if counts[idx] > n * TRIPLE_P else "deficit"}


def run_v314(labelled: list[dict], source_sha256: str, simulations: int = 1999, seed: int = 3142026) -> dict:
    if simulations < 999:
        raise ValueError("simulations_must_be_at_least_999")
    classic = sorted((r for r in labelled if r.get("draw_type") == "CLASSIC"), key=lambda r: int(r["contest"]))
    if len(classic) < 1000:
        raise ValueError("insufficient_classic_draws")
    draws = _matrix(classic)
    observed = _triple_max_z(draws)
    rng = np.random.default_rng(seed)
    null = np.empty(simulations, dtype=float)
    for b in range(simulations):
        null[b] = _triple_max_z(_simulate_draws(rng, len(classic)))
    p_value = (1 + int(np.count_nonzero(null >= observed))) / (simulations + 1)
    winner = _winning_triple(draws)
    # Descriptive chronological stability for the single full-history winner.
    triple_idx = np.asarray(winner["numbers"], dtype=int) - 1
    block_counts = []
    for block in np.array_split(np.arange(len(classic)), 4):
        count = int(np.sum(np.all(draws[block][:, triple_idx] == 1, axis=1)))
        block_counts.append({"block": len(block_counts) + 1, "n": int(len(block)), "count": count})
    return {
        "candidate": "V314_TRIPLE_MOTIF_MAX_STATISTIC",
        "classification": "RESEARCH_ONLY_HISTORICAL_MOTIF_TEST_NOT_PREDICTIVE_EDGE",
        "draw_stream": "CLASSIC_ONLY", "n_classic_draws": len(classic),
        "first_contest": classic[0]["contest"], "last_contest": classic[-1]["contest"],
        "source_sha256": source_sha256, "simulations": simulations, "seed": seed,
        "family_size": len(TRIPLES), "triple_probability_under_null": TRIPLE_P,
        "observed_max_z": observed, "null_95th_percentile": float(np.quantile(null, 0.95)),
        "monte_carlo_p_value": float(p_value), "winning_triple": winner,
        "winning_triple_chronological_blocks": block_counts,
        "interpretation": "A significant max-statistic indicates a historical triple motif only; it is not causal or predictive evidence.",
        "warning": "Historical discovery only; no prospective custody, official row-level source audit, or predictive edge."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=1999)
    parser.add_argument("--seed", type=int, default=3142026)
    args = parser.parse_args()
    rows, digest = read_history(args.history)
    labelled, _ = assign_modality(rows)
    report = run_v314(labelled, digest, args.simulations, args.seed)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "v314_triple_motif_report.json").write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
