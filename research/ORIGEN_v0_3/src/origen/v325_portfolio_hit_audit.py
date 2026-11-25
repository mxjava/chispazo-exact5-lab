"""V325: frozen top-30 portfolio hit audit for Exact5 candidates.

Uses V322 expanding memory and V324 rolling horizons without changing their
PMFs. Candidate portfolios are generated before scoring each realized target.
Randomized tie-breaking within the cutoff is deterministic under a fixed seed.
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

import numpy as np

from origen.exact5_modalities import assign_modality, read_history
from origen.v322_hierarchical_partition import (
    ALPHA, UNIVERSE_SIZE, HierarchicalPartitionModel,
)
from origen.v324_rolling_memory import RollingPartitionModel, WINDOWS, WARMUP

PORTFOLIO_SIZE = 30
TIE_SEED = 3252026
EXPECTED_HISTORY_SHA256 = "5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a"


def select_top_k(pmf: np.ndarray, k: int, rng: np.random.Generator) -> list[int]:
    if (not isinstance(k, int) or isinstance(k, bool) or k < 1
            or k > len(pmf) or not np.all(np.isfinite(pmf))
            or np.any(pmf < 0)):
        raise ValueError("invalid_top_k_or_pmf")
    threshold = float(np.partition(pmf, len(pmf) - k)[len(pmf) - k])
    greater = np.flatnonzero(pmf > threshold)
    tied = np.flatnonzero(pmf == threshold)
    remaining = k - len(greater)
    if remaining < 0 or remaining > len(tied):
        raise RuntimeError("top_k_cutoff_invariant_failure")
    if remaining:
        chosen_ties = rng.choice(tied, size=remaining, replace=False)
        selected = np.concatenate((greater, chosen_ties))
    else:
        selected = greater
    selected = sorted((int(i) for i in selected), key=lambda i: (-float(pmf[i]), i))
    if len(selected) != k or len(set(selected)) != k:
        raise RuntimeError("portfolio_cardinality_failure")
    return selected


def portfolio_hit_counts(portfolio: list[tuple[int, ...]],
                         target: tuple[int, ...]) -> dict:
    if len(target) != 5 or len(set(target)) != 5:
        raise ValueError("invalid_target")
    overlaps = [len(set(combo).intersection(target)) for combo in portfolio]
    return {
        "hits_3of5": sum(x == 3 for x in overlaps),
        "hits_4of5": sum(x == 4 for x in overlaps),
        "hits_5of5": sum(x == 5 for x in overlaps),
        "hits_at_least_3": sum(x >= 3 for x in overlaps),
        "hits_at_least_4": sum(x >= 4 for x in overlaps),
        "best_match": max(overlaps, default=0),
    }


def random_portfolio_expectations(targets: int, portfolio_size: int) -> dict:
    counts = {
        "3of5": math.comb(5, 3) * math.comb(23, 2),
        "4of5": math.comb(5, 4) * math.comb(23, 1),
        "5of5": 1,
    }
    counts["at_least_3"] = sum(counts.values())
    counts["at_least_4"] = counts["4of5"] + counts["5of5"]
    result = {}
    for label, count in counts.items():
        probability_line = count / UNIVERSE_SIZE
        probability_any = 1.0 - math.comb(
            UNIVERSE_SIZE - count, portfolio_size
        ) / math.comb(UNIVERSE_SIZE, portfolio_size)
        result[label] = {
            "expected_hit_lines": targets * portfolio_size * probability_line,
            "expected_targets_with_at_least_one": targets * probability_any,
        }
    return result


def evaluate(history_path: str | Path, output_dir: str | Path,
             mode: str, window_classic: int | None = None,
             expected_sha256: str | None = EXPECTED_HISTORY_SHA256,
             warmup_classic: int = WARMUP, alpha: float = ALPHA,
             portfolio_size: int = PORTFOLIO_SIZE) -> dict:
    if mode not in ("expanding", "rolling"):
        raise ValueError("mode_must_be_expanding_or_rolling")
    if mode == "expanding" and window_classic is not None:
        raise ValueError("expanding_mode_has_no_window")
    if mode == "rolling" and window_classic not in WINDOWS:
        raise ValueError("rolling_window_must_be_400_800_1600")
    if portfolio_size != PORTFOLIO_SIZE:
        raise ValueError("portfolio_size_is_frozen_at_30")
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

    rng = np.random.Generator(np.random.PCG64(TIE_SEED))
    records = []
    combinations_universe = model.combinations
    for target in classic[warmup_classic:]:
        # Portfolio generation is completed before target overlap is inspected.
        pmf = model.probabilities()
        selected_ids = select_top_k(pmf, portfolio_size, rng)
        portfolio = [combinations_universe[i] for i in selected_ids]
        hits = portfolio_hit_counts(portfolio, tuple(target["numbers"]))
        records.append({
            "contest": target["contest"],
            "date": target["date"],
            "target": "-".join(map(str, target["numbers"])),
            "mode": mode,
            "window_classic": window_classic or "EXPANDING",
            "portfolio_size": portfolio_size,
            "portfolio": json.dumps([list(c) for c in portfolio], separators=(",", ":")),
            **hits,
        })
        model.update(target["numbers"])
        if mode == "rolling":
            fifo.append(tuple(target["numbers"]))
            if len(fifo) > int(window_classic):
                model.remove(fifo.popleft())

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    suffix = "expanding" if mode == "expanding" else f"rolling_{window_classic}"
    csv_path = out / f"v325_top30_{suffix}.csv"
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
        "schema": "EXACT5_V325_TOP30_PORTFOLIO_HIT_AUDIT_V1",
        "classification": "RETROSPECTIVE_PREQUENTIAL_PORTFOLIO_AUDIT_NO_EDGE",
        "source_sha256": digest, "source_rows": len(rows),
        "classic_draws": len(classic),
        "first_classic_contest": classic[0]["contest"],
        "last_classic_contest": classic[-1]["contest"],
        "warmup_classic": warmup_classic, "scored_targets": targets,
        "mode": mode, "window_classic": window_classic,
        "alpha_fixed": alpha, "portfolio_size": portfolio_size,
        "tie_break": "uniform random without replacement within cutoff tie; PCG64 seed 3252026; fixed chronological RNG stream",
        "universe_size": UNIVERSE_SIZE,
        "observed_hit_lines": totals,
        "observed_targets_with_hits": targets_with_hits,
        "uniform_random_portfolio_expectation": random_portfolio_expectations(targets, portfolio_size),
        "scores_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "modality_audit": modality_audit,
        "warnings": [
            "Each top-30 portfolio is generated from the pre-target PMF before inspecting target overlap.",
            "All variants use the same 800-draw warmup and 6,923 target sequence.",
            "Tie-breaking is deterministic and outcome-independent; no target-informed selection.",
            "This is retrospective portfolio reconstruction, not an authenticated pre-close forecast.",
            "Horizons were selected after prior exploratory analysis; results are not confirmatory.",
            "No parameter search, V294 modification, canonical-history write, or promotion."
        ],
    }
    (out / f"v325_top30_{suffix}_report.json").write_text(
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
