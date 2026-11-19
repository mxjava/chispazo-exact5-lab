"""V322 hierarchical partition-and-divide Exact5 diagnostic.

Every target is scored using only earlier Classic observations. Each fixed
partition tree assigns posterior mass to disjoint cells, then divides that
mass uniformly among combinations inside the cell. A fixed equal-weight
mixture of three trees remains a normalized PMF over all C(28,5) outcomes.
This is retrospective prequential research, not a certified forecast.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from origen.exact5_modalities import assign_modality, read_history

UNIVERSE_SIZE = math.comb(28, 5)
ALPHA = 200.0
WARMUP_CLASSIC = 800
TOP_K = (1, 5, 10, 30, 100)

# Fixed, disjoint category definitions. No cut point is selected from target outcomes.
TREE_ORDERS = (
    ("sum_bin", "range_bin", "odd_count", "prime_count", "adjacent_count"),
    ("band_profile", "sum_bin", "max_gap_bin", "odd_count", "adjacent_count"),
    ("range_bin", "band_profile", "prime_count", "sum_bin", "max_gap_bin"),
)


def candidate_features(combo: tuple[int, ...]) -> dict:
    n = tuple(sorted(combo))
    if len(n) != 5 or len(set(n)) != 5 or any(x < 1 or x > 28 for x in n):
        raise ValueError("invalid_five_of_28_set")
    gaps = tuple(n[i + 1] - n[i] for i in range(4))
    total = sum(n)
    span = n[-1] - n[0]
    primes = {2, 3, 5, 7, 11, 13, 17, 19, 23}
    return {
        "sum_bin": sum(total > edge for edge in (55, 65, 75, 85, 95)),
        "range_bin": sum(span > edge for edge in (10, 15, 20, 24)),
        "odd_count": sum(x % 2 for x in n),
        "prime_count": sum(x in primes for x in n),
        "adjacent_count": sum(g == 1 for g in gaps),
        "band_profile": (
            sum(x <= 9 for x in n),
            sum(10 <= x <= 18 for x in n),
            sum(x >= 19 for x in n),
        ),
        "max_gap_bin": sum(max(gaps) > edge for edge in (3, 5, 8, 12)),
    }


class _PartitionTree:
    def __init__(self, paths: list[tuple]):
        self.depth = len(TREE_ORDERS[0])  # all trees have equal depth
        self.leaves = sorted(set(paths))
        self.leaf_index = {path: i for i, path in enumerate(self.leaves)}
        self.candidate_leaf_ids = np.asarray(
            [self.leaf_index[path] for path in paths], dtype=np.int32
        )
        path_counts = Counter(paths)
        self.leaf_sizes = np.asarray(
            [path_counts[leaf] for leaf in self.leaves],
            dtype=np.float64,
        )
        self.universe_prefix_counts = []
        self.training_prefix_counts = []
        for depth in range(1, self.depth + 1):
            self.universe_prefix_counts.append(
                Counter(path[:depth] for path in paths)
            )
            self.training_prefix_counts.append(Counter())

    def update(self, path: tuple) -> None:
        for depth in range(1, self.depth + 1):
            self.training_prefix_counts[depth - 1][path[:depth]] += 1

    def leaf_probabilities(self, draws_seen: int, alpha: float) -> np.ndarray:
        probs = np.ones(len(self.leaves), dtype=np.float64)
        for leaf_id, leaf in enumerate(self.leaves):
            for depth in range(1, self.depth + 1):
                child = leaf[:depth]
                parent = leaf[: depth - 1]
                child_train = self.training_prefix_counts[depth - 1].get(child, 0)
                parent_train = (
                    draws_seen if depth == 1
                    else self.training_prefix_counts[depth - 2].get(parent, 0)
                )
                child_universe = self.universe_prefix_counts[depth - 1][child]
                parent_universe = (
                    UNIVERSE_SIZE if depth == 1
                    else self.universe_prefix_counts[depth - 2][parent]
                )
                base_conditional = child_universe / parent_universe
                probs[leaf_id] *= (
                    child_train + alpha * base_conditional
                ) / (parent_train + alpha)
        return probs


class HierarchicalPartitionModel:
    """Equal-weight mixture of three exact, hierarchical partition PMFs."""

    def __init__(self, alpha: float = ALPHA):
        if not isinstance(alpha, (int, float)) or not math.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha_must_be_finite_positive")
        self.alpha = float(alpha)
        self.combinations = list(combinations(range(1, 29), 5))
        if len(self.combinations) != UNIVERSE_SIZE:
            raise RuntimeError("universe_cardinality_failure")
        self.combo_index = {combo: i for i, combo in enumerate(self.combinations)}
        self.features = [candidate_features(combo) for combo in self.combinations]
        self.paths_by_tree = [
            [tuple(f[name] for name in order) for f in self.features]
            for order in TREE_ORDERS
        ]
        self.trees = [_PartitionTree(paths) for paths in self.paths_by_tree]
        self.draws_seen = 0

    def update(self, draw: list[int] | tuple[int, ...]) -> None:
        combo = tuple(sorted(draw))
        if combo not in self.combo_index:
            raise ValueError("invalid_training_draw")
        idx = self.combo_index[combo]
        for tree, paths in zip(self.trees, self.paths_by_tree):
            tree.update(paths[idx])
        self.draws_seen += 1

    def probabilities(self) -> np.ndarray:
        if self.draws_seen < 0:
            raise RuntimeError("invalid_draw_count")
        mixture = np.zeros(UNIVERSE_SIZE, dtype=np.float64)
        for tree in self.trees:
            leaf_p = tree.leaf_probabilities(self.draws_seen, self.alpha)
            combo_p = leaf_p[tree.candidate_leaf_ids] / tree.leaf_sizes[tree.candidate_leaf_ids]
            mixture += combo_p / len(self.trees)
        total = float(mixture.sum())
        if not math.isfinite(total) or total <= 0:
            raise RuntimeError("invalid_mixture_normalization")
        mixture /= total
        return mixture

    def score(self, target: list[int] | tuple[int, ...], top_k: tuple[int, ...] = TOP_K) -> dict:
        combo = tuple(sorted(target))
        if combo not in self.combo_index:
            raise ValueError("invalid_target_draw")
        if self.draws_seen == 0:
            raise ValueError("no_preceding_draws")
        pmf = self.probabilities()
        target_p = float(pmf[self.combo_index[combo]])
        greater = int(np.count_nonzero(pmf > target_p))
        tied = int(np.count_nonzero(pmf == target_p))
        rank_low, rank_high = greater + 1, greater + tied
        result = {
            "target_probability": target_p,
            "log_lift_vs_uniform": math.log(target_p * UNIVERSE_SIZE),
            "rank_low": rank_low,
            "rank_high": rank_high,
            "rank_mid": greater + (tied + 1) / 2.0,
            "tie_size": tied,
        }
        for k in top_k:
            if not isinstance(k, int) or isinstance(k, bool) or k < 1 or k > UNIVERSE_SIZE:
                raise ValueError("invalid_top_k")
            result[f"top_{k}_inclusion_probability"] = (
                0.0 if greater >= k else min(1.0, (k - greater) / tied)
            )
        return result


def evaluate_history(history_path: str | Path, output_dir: str | Path,
                     expected_sha256: str | None = None,
                     warmup_classic: int = WARMUP_CLASSIC,
                     alpha: float = ALPHA) -> dict:
    if not isinstance(warmup_classic, int) or isinstance(warmup_classic, bool) or warmup_classic < 1:
        raise ValueError("warmup_classic_must_be_positive_integer")
    rows, digest = read_history(history_path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("canonical_history_sha256_mismatch")
    labelled, modality_audit = assign_modality(rows)
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws")
    model = HierarchicalPartitionModel(alpha=alpha)
    records = []
    # Warmup and scoring are strictly chronological; the target is added only after scoring.
    for row in classic[:warmup_classic]:
        model.update(row["numbers"])
    for target in classic[warmup_classic:]:
        scored = model.score(target["numbers"])
        records.append({
            "contest": target["contest"], "date": target["date"],
            "numbers": "-".join(map(str, target["numbers"])),
            "prior_classic_draws": model.draws_seen,
            **scored,
        })
        model.update(target["numbers"])

    lifts = [r["log_lift_vs_uniform"] for r in records]
    ordered = sorted(lifts)
    def expected_top(k: int) -> float:
        return sum(r[f"top_{k}_inclusion_probability"] for r in records)
    summary = {
        "schema": "EXACT5_V322_HIERARCHICAL_PARTITION_V1",
        "classification": "RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE",
        "source_sha256": digest,
        "source_rows": len(rows),
        "classic_draws": len(classic),
        "first_classic_contest": classic[0]["contest"],
        "last_classic_contest": classic[-1]["contest"],
        "warmup_classic": warmup_classic,
        "scored_targets": len(records),
        "alpha_fixed": alpha,
        "partition_trees": [list(order) for order in TREE_ORDERS],
        "universe_size": UNIVERSE_SIZE,
        "mean_log_lift": sum(lifts) / len(lifts),
        "median_log_lift": (
            ordered[len(ordered)//2] if len(ordered) % 2
            else (ordered[len(ordered)//2-1] + ordered[len(ordered)//2]) / 2
        ),
        "cumulative_log_lift": sum(lifts),
        "positive_log_lift_fraction": sum(x > 0 for x in lifts) / len(lifts),
        "exact_5of5_rank_1_count": sum(r["rank_low"] == 1 and r["rank_high"] == 1 for r in records),
        "expected_top_k_inclusions": {
            str(k): expected_top(k) for k in (1, 5, 10, 30, 100)
        },
        "uniform_expected_top_k_inclusions": {
            str(k): len(records) * k / UNIVERSE_SIZE for k in (1, 5, 10, 30, 100)
        },
        "modality_audit": modality_audit,
        "warnings": [
            "All predictions use only earlier structurally assigned Classic rows; modality remains pending row-level official verification.",
            "Each tree is a complete disjoint partition; posterior cell mass is divided uniformly among combinations in the leaf.",
            "The three-tree mixture is normalized exactly over all 98,280 combinations.",
            "This is a historical prequential diagnostic, not independent prospective evidence or a certified betting edge.",
            "No parameter search, target-informed partitioning, or V294 modification is performed."
        ],
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "v322_hierarchical_partition_scores.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary["scores_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    (out / "v322_hierarchical_partition_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--warmup-classic", type=int, default=WARMUP_CLASSIC)
    args = parser.parse_args()
    result = evaluate_history(args.history, args.out, args.expected_sha256, args.warmup_classic)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
