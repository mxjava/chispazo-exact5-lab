"""V326: diversified top-30 portfolio from a frozen top-100 score pool.

The PMF is unchanged. A greedy maximum-new-pair-coverage rule selects 30
distinct candidates from the 100 highest-probability combinations, using
pre-target information only. This is exploratory retrospective research.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import deque
from itertools import combinations
from pathlib import Path
from statistics import mean

import numpy as np

from origen.exact5_modalities import assign_modality, read_history
from origen.v322_hierarchical_partition import (
    ALPHA, UNIVERSE_SIZE, HierarchicalPartitionModel,
)
from origen.v324_rolling_memory import RollingPartitionModel, WINDOWS, WARMUP
from origen.v325_portfolio_hit_audit import (
    EXPECTED_HISTORY_SHA256, PORTFOLIO_SIZE, portfolio_hit_counts,
    random_portfolio_expectations, select_top_k,
)

POOL_SIZE = 100
DIVERSITY_SEED = 3262026


def pair_mask(combo: tuple[int, ...]) -> int:
    if len(combo) != 5 or len(set(combo)) != 5:
        raise ValueError("invalid_candidate_combination")
    mask = 0
    for a, b in combinations(sorted(combo), 2):
        mask |= 1 << ((a - 1) * 28 + (b - 1))
    return mask


def greedy_diverse_selection(pmf: np.ndarray, combinations_universe: list[tuple[int, ...]],
                             k: int, pool_size: int,
                             rng: np.random.Generator) -> list[int]:
    if (not isinstance(k, int) or isinstance(k, bool) or k < 1
            or not isinstance(pool_size, int) or isinstance(pool_size, bool)
            or pool_size < k or pool_size > len(combinations_universe)):
        raise ValueError("invalid_portfolio_or_pool_size")
    pool = select_top_k(pmf, pool_size, rng)
    masks = {idx: pair_mask(combinations_universe[idx]) for idx in pool}
    rank_order = {idx: pos for pos, idx in enumerate(pool)}
    remaining = set(pool)
    selected = []
    covered = 0
    for _ in range(k):
        best = max(
            remaining,
            key=lambda idx: ((masks[idx] & ~covered).bit_count(), -rank_order[idx]),
        )
        selected.append(best)
        covered |= masks[best]
        remaining.remove(best)
    if len(selected) != k or len(set(selected)) != k:
        raise RuntimeError("diverse_portfolio_cardinality_failure")
    return selected


def portfolio_diversity(portfolio: list[tuple[int, ...]]) -> dict:
    sets = [set(combo) for combo in portfolio]
    union = set().union(*sets) if sets else set()
    pairs = set()
    overlaps = []
    for combo in portfolio:
        pairs.update(combinations(sorted(combo), 2))
    for a, b in combinations(sets, 2):
        overlaps.append(len(a & b))
    return {
        "unique_numbers": len(union),
        "unique_pairs": len(pairs),
        "mean_pairwise_overlap": mean(overlaps) if overlaps else 0.0,
    }


def random_portfolio_diversity_expectation(portfolio_size: int) -> dict:
    universe = UNIVERSE_SIZE
    per_number = math.comb(27, 4)
    per_pair = math.comb(26, 3)
    expected_numbers = 28 * (
        1 - math.comb(universe - per_number, portfolio_size)
        / math.comb(universe, portfolio_size)
    )
    expected_pairs = math.comb(28, 2) * (
        1 - math.comb(universe - per_pair, portfolio_size)
        / math.comb(universe, portfolio_size)
    )
    return {
        "expected_unique_numbers": expected_numbers,
        "expected_unique_pairs": expected_pairs,
        "expected_mean_pairwise_overlap": 25 / 28,
    }


def evaluate(history_path: str | Path, output_dir: str | Path,
             mode: str, window_classic: int | None = None,
             expected_sha256: str | None = EXPECTED_HISTORY_SHA256,
             warmup_classic: int = WARMUP, alpha: float = ALPHA) -> dict:
    if mode not in ("expanding", "rolling"):
        raise ValueError("mode_must_be_expanding_or_rolling")
    if mode == "expanding" and window_classic is not None:
        raise ValueError("expanding_mode_has_no_window")
    if mode == "rolling" and window_classic not in WINDOWS:
        raise ValueError("rolling_window_must_be_400_800_1600")
    rows, digest = read_history(history_path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("canonical_history_sha256_mismatch")
    labelled, modality_audit = assign_modality(rows)
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws")

    model = (HierarchicalPartitionModel(alpha=alpha) if mode == "expanding"
             else RollingPartitionModel(alpha=alpha))
    fifo = deque()
    for row in classic[:warmup_classic]:
        model.update(row["numbers"])
        if mode == "rolling":
            fifo.append(tuple(row["numbers"]))
            while len(fifo) > int(window_classic):
                model.remove(fifo.popleft())

    rng = np.random.Generator(np.random.PCG64(DIVERSITY_SEED))
    records = []
    universe = model.combinations
    for target in classic[warmup_classic:]:
        # Build a score-only pool and diversify it before looking at target.
        pmf = model.probabilities()
        selected_ids = greedy_diverse_selection(
            pmf, universe, PORTFOLIO_SIZE, POOL_SIZE, rng
        )
        portfolio = [universe[i] for i in selected_ids]
        hits = portfolio_hit_counts(portfolio, tuple(target["numbers"]))
        diversity = portfolio_diversity(portfolio)
        records.append({
            "contest": target["contest"],
            "date": target["date"],
            "target": "-".join(map(str, target["numbers"])),
            "mode": mode,
            "window_classic": window_classic or "EXPANDING",
            "portfolio_size": PORTFOLIO_SIZE,
            "candidate_pool_size": POOL_SIZE,
            "portfolio": json.dumps([list(c) for c in portfolio], separators=(",", ":")),
            **hits,
            **diversity,
        })
        model.update(target["numbers"])
        if mode == "rolling":
            fifo.append(tuple(target["numbers"]))
            if len(fifo) > int(window_classic):
                model.remove(fifo.popleft())

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = "expanding" if mode == "expanding" else f"rolling_{window_classic}"
    csv_path = out / f"v326_diverse30_{suffix}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    targets = len(records)
    totals = {
        key: sum(r[key] for r in records)
        for key in ("hits_3of5", "hits_4of5", "hits_5of5",
                    "hits_at_least_3", "hits_at_least_4")
    }
    targets_with_hits = {
        "3of5": sum(r["hits_3of5"] > 0 for r in records),
        "4of5": sum(r["hits_4of5"] > 0 for r in records),
        "5of5": sum(r["hits_5of5"] > 0 for r in records),
        "at_least_3": sum(r["hits_at_least_3"] > 0 for r in records),
        "at_least_4": sum(r["hits_at_least_4"] > 0 for r in records),
    }
    report = {
        "schema": "EXACT5_V326_DIVERSIFIED_TOP30_AUDIT_V1",
        "classification": "RETROSPECTIVE_PREQUENTIAL_PORTFOLIO_AUDIT_NO_EDGE",
        "source_sha256": digest, "source_rows": len(rows),
        "classic_draws": len(classic),
        "first_classic_contest": classic[0]["contest"],
        "last_classic_contest": classic[-1]["contest"],
        "warmup_classic": warmup_classic, "scored_targets": targets,
        "mode": mode, "window_classic": window_classic,
        "alpha_fixed": alpha, "portfolio_size": PORTFOLIO_SIZE,
        "candidate_pool_size": POOL_SIZE,
        "selection": "greedy maximum new unordered-pair coverage; ties resolved by PMF rank within a PCG64-seeded top-100 pool",
        "seed": DIVERSITY_SEED,
        "universe_size": UNIVERSE_SIZE,
        "observed_hit_lines": totals,
        "observed_targets_with_hits": targets_with_hits,
        "uniform_random_portfolio_expectation": random_portfolio_expectations(targets, PORTFOLIO_SIZE),
        "mean_portfolio_diversity": {
            "unique_numbers": mean(r["unique_numbers"] for r in records),
            "unique_pairs": mean(r["unique_pairs"] for r in records),
            "mean_pairwise_overlap": mean(r["mean_pairwise_overlap"] for r in records),
        },
        "uniform_random_portfolio_diversity_expectation": random_portfolio_diversity_expectation(PORTFOLIO_SIZE),
        "scores_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "modality_audit": modality_audit,
        "warnings": [
            "Portfolio is generated from pre-target PMF before target overlap is evaluated.",
            "Candidate pool size 100 and greedy pair-coverage rule are fixed for this exploratory test.",
            "Tie-breaking is deterministic and independent of target values.",
            "This is retrospective portfolio reconstruction, not authenticated pre-close forecasting.",
            "The V326 diversification rule is exploratory and must not be selected as a winner from this same history.",
            "No parameter search, V294 modification, canonical-history write, or promotion."
        ],
    }
    (out / f"v326_diverse30_{suffix}_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=("expanding", "rolling"), required=True)
    parser.add_argument("--window-classic", type=int, choices=WINDOWS)
    parser.add_argument("--expected-sha256", default=EXPECTED_HISTORY_SHA256)
    parser.add_argument("--warmup-classic", type=int, default=WARMUP)
    args = parser.parse_args()
    print(json.dumps(evaluate(
        args.history, args.out, args.mode, args.window_classic,
        args.expected_sha256, args.warmup_classic
    ), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
