"""V315 pair-conditioned next-draw overlap omnibus falsification."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np
from origen.exact5_modalities import assign_modality, read_history
from origen.v313_global_null import PICK, UNIVERSE, _matrix, _simulate_draws

PAIRS = tuple((i, j) for i in range(UNIVERSE) for j in range(i + 1, UNIVERSE))
PAIR_LOOKUP = np.full((UNIVERSE, UNIVERSE), -1, dtype=np.int16)
for _idx, (_i, _j) in enumerate(PAIRS):
    PAIR_LOOKUP[_i, _j] = _idx
    PAIR_LOOKUP[_j, _i] = _idx
PAIR_POSITIONS = np.asarray([(a, b) for a in range(PICK) for b in range(a + 1, PICK)], dtype=np.int8)
PAIR_PROB = PICK * (PICK - 1) / (UNIVERSE * (UNIVERSE - 1))
OVERLAP_PROBS = np.asarray([
    math.comb(UNIVERSE - 2, PICK) / math.comb(UNIVERSE, PICK),
    2 * math.comb(UNIVERSE - 2, PICK - 1) / math.comb(UNIVERSE, PICK),
    math.comb(UNIVERSE - 2, PICK - 2) / math.comb(UNIVERSE, PICK),
], dtype=float)


def _cell_counts(draws: np.ndarray) -> np.ndarray:
    if draws.ndim != 2 or draws.shape[1] != UNIVERSE or draws.shape[0] < 2 or not np.all(draws.sum(axis=1) == PICK):
        raise ValueError("invalid_v315_matrix")
    selected = np.argsort(draws, axis=1)[:, -PICK:]
    selected.sort(axis=1)
    prev_pairs = selected[:-1, PAIR_POSITIONS]
    pair_ids = PAIR_LOOKUP[prev_pairs[:, :, 0], prev_pairs[:, :, 1]]
    next_rows = draws[1:].astype(np.int8, copy=False)
    overlap = next_rows[np.arange(len(next_rows))[:, None], prev_pairs[:, :, 0]] + next_rows[np.arange(len(next_rows))[:, None], prev_pairs[:, :, 1]]
    flat = (pair_ids * 3 + overlap).ravel()
    return np.bincount(flat, minlength=len(PAIRS) * 3).astype(np.int64, copy=False)


def _max_stat(draws: np.ndarray) -> tuple[float, np.ndarray]:
    counts = _cell_counts(draws)
    n = draws.shape[0] - 1
    probabilities = PAIR_PROB * OVERLAP_PROBS
    expected = n * np.tile(probabilities, len(PAIRS))
    variance = n * np.tile(probabilities * (1.0 - probabilities), len(PAIRS))
    z = np.abs(counts - expected) / np.sqrt(variance)
    return float(np.max(z)), counts


def run_v315(labelled: list[dict], source_sha256: str, simulations: int = 1999, seed: int = 3152026) -> dict:
    if simulations < 999:
        raise ValueError("simulations_must_be_at_least_999")
    classic = sorted((r for r in labelled if r.get("draw_type") == "CLASSIC"), key=lambda r: int(r["contest"]))
    if len(classic) < 1000:
        raise ValueError("insufficient_classic_draws")
    draws = _matrix(classic)
    observed, counts = _max_stat(draws)
    rng = np.random.default_rng(seed)
    null = np.empty(simulations, dtype=float)
    for b in range(simulations):
        null[b], _ = _max_stat(_simulate_draws(rng, len(classic)))
    p_value = (1 + int(np.count_nonzero(null >= observed))) / (simulations + 1)
    # Cell vector is pair-major/category-minor: repeat the three overlap
    # probabilities for each of the 378 prior pairs.
    expected = (len(classic)-1) * np.tile(PAIR_PROB * OVERLAP_PROBS, len(PAIRS))
    variance = (len(classic)-1) * np.tile(PAIR_PROB * OVERLAP_PROBS * (1-PAIR_PROB*OVERLAP_PROBS), len(PAIRS))
    z = np.abs(counts - expected) / np.sqrt(variance)
    idx = int(np.argmax(z))
    pair_idx, category = divmod(idx, 3)
    pair = PAIRS[pair_idx]
    winner = {"previous_pair": [pair[0]+1, pair[1]+1], "next_draw_overlap": category,
              "observed_count": int(counts[idx]), "expected_count": float(expected[idx]),
              "standardized_deviation": float(z[idx])}
    # Descriptive chronological stability of the full-history winning cell.
    prev = draws[:-1]
    nxt = draws[1:]
    block_rows = []
    for block_id, positions in enumerate(np.array_split(np.arange(len(prev)), 4), 1):
        pair_present = prev[positions, pair[0]] * prev[positions, pair[1]]
        overlap = nxt[positions, pair[0]] + nxt[positions, pair[1]]
        count = int(np.sum(pair_present * (overlap == category)))
        block_rows.append({"block": block_id, "transitions": int(len(positions)), "count": count})
    return {
        "candidate": "V315_PAIR_CONDITIONED_NEXT_DRAW_OVERLAP",
        "classification": "RESEARCH_ONLY_HISTORICAL_TRANSITION_TEST_NOT_PREDICTIVE_EDGE",
        "draw_stream": "CLASSIC_ONLY", "n_classic_draws": len(classic),
        "first_contest": classic[0]["contest"], "last_contest": classic[-1]["contest"],
        "source_sha256": source_sha256, "simulations": simulations, "seed": seed,
        "family_size": len(PAIRS)*3, "prior_pair_probability": PAIR_PROB,
        "next_overlap_probabilities": {"0": float(OVERLAP_PROBS[0]), "1": float(OVERLAP_PROBS[1]), "2": float(OVERLAP_PROBS[2])},
        "observed_max_z": observed, "null_95th_percentile": float(np.quantile(null, 0.95)),
        "monte_carlo_p_value": float(p_value), "winning_cell": winner,
        "winning_cell_chronological_blocks": block_rows,
        "interpretation": "A rejection indicates historical pair-conditioned transition structure only; it does not establish causality or prospective advantage.",
        "warning": "Historical discovery only; Monte Carlo max calibration accounts for cell dependence. No prospective custody or predictive edge."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--simulations", type=int, default=1999)
    parser.add_argument("--seed", type=int, default=3152026)
    args = parser.parse_args()
    rows, digest = read_history(args.history)
    labelled, _ = assign_modality(rows)
    report = run_v315(labelled, digest, args.simulations, args.seed)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "v315_pair_transition_report.json").write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
