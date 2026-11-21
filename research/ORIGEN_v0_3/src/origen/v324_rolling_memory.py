"""V324: fixed rolling-memory ablation for the V322 partition PMF.

Runs one predeclared memory horizon at a time. Every target is scored before
update; alpha, partitions, universe and target sequence are held fixed.
This is retrospective prequential diagnostics, not prospective evidence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import deque
from pathlib import Path

from origen.exact5_modalities import assign_modality, read_history
from origen.v322_hierarchical_partition import (
    ALPHA, TOP_K, UNIVERSE_SIZE, HierarchicalPartitionModel,
)

WINDOWS = (400, 800, 1600)
WARMUP = 800
EXPECTED_HISTORY_SHA256 = "5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a"


class RollingPartitionModel(HierarchicalPartitionModel):
    """V322 PMF with exact FIFO removal of observations outside a fixed window."""

    def remove(self, draw: list[int] | tuple[int, ...]) -> None:
        if len(draw) != 5 or any(not isinstance(x, int) or isinstance(x, bool) for x in draw):
            raise ValueError("invalid_training_draw")
        combo = tuple(sorted(draw))
        if combo not in self.combo_index or self.draws_seen <= 0:
            raise ValueError("cannot_remove_unknown_or_empty_draw")
        idx = self.combo_index[combo]
        paths = [tree_path[idx] for tree_path in self.paths_by_tree]
        # Preflight all counters before mutating any tree.
        for tree, path in zip(self.trees, paths):
            for depth in range(1, tree.depth + 1):
                prefix_id = tree.prefix_indices[depth - 1][path[:depth]]
                if tree.training_prefix_counts[depth - 1][prefix_id] <= 0:
                    raise RuntimeError("rolling_count_underflow")
        for tree, path in zip(self.trees, paths):
            for depth in range(1, tree.depth + 1):
                prefix_id = tree.prefix_indices[depth - 1][path[:depth]]
                tree.training_prefix_counts[depth - 1][prefix_id] -= 1
        self.draws_seen -= 1


def evaluate_window(history_path: str | Path, output_dir: str | Path,
                    window_classic: int, expected_sha256: str | None = EXPECTED_HISTORY_SHA256,
                    warmup_classic: int = WARMUP, alpha: float = ALPHA) -> dict:
    if window_classic not in WINDOWS:
        raise ValueError("window_must_be_one_of_400_800_1600")
    if not isinstance(warmup_classic, int) or isinstance(warmup_classic, bool) or warmup_classic < 1:
        raise ValueError("warmup_must_be_positive_integer")
    rows, digest = read_history(history_path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("canonical_history_sha256_mismatch")
    labelled, modality_audit = assign_modality(rows)
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws")

    model = RollingPartitionModel(alpha=alpha)
    fifo = deque()
    for row in classic[:warmup_classic]:
        model.update(row["numbers"])
        fifo.append(tuple(row["numbers"]))
        while len(fifo) > window_classic:
            model.remove(fifo.popleft())

    records = []
    for target in classic[warmup_classic:]:
        scored = model.score(target["numbers"])
        records.append({
            "contest": target["contest"], "date": target["date"],
            "numbers": "-".join(map(str, target["numbers"])),
            "window_classic": window_classic,
            "prior_window_draws": model.draws_seen,
            **scored,
        })
        model.update(target["numbers"])
        fifo.append(tuple(target["numbers"]))
        if len(fifo) > window_classic:
            model.remove(fifo.popleft())

    lifts = [r["log_lift_vs_uniform"] for r in records]
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"v324_window_{window_classic}_scores.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    summary = {
        "schema": "EXACT5_V324_ROLLING_MEMORY_ABLATION_V1",
        "classification": "RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE",
        "source_sha256": digest, "source_rows": len(rows),
        "classic_draws": len(classic),
        "first_classic_contest": classic[0]["contest"],
        "last_classic_contest": classic[-1]["contest"],
        "warmup_classic": warmup_classic, "scored_targets": len(records),
        "window_classic": window_classic, "alpha_fixed": alpha,
        "universe_size": UNIVERSE_SIZE,
        "mean_log_lift": sum(lifts) / len(lifts),
        "median_log_lift": sorted(lifts)[len(lifts)//2],
        "cumulative_log_lift": sum(lifts),
        "positive_log_lift_fraction": sum(x > 0 for x in lifts) / len(lifts),
        "exact_rank_1_count": sum(r["rank_low"] == r["rank_high"] == 1 for r in records),
        "expected_top_k_inclusions": {
            str(k): sum(r[f"top_{k}_inclusion_probability"] for r in records)
            for k in TOP_K
        },
        "uniform_expected_top_k_inclusions": {
            str(k): len(records) * k / UNIVERSE_SIZE for k in TOP_K
        },
        "scores_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "modality_audit": modality_audit,
        "warnings": [
            "Strict chronological scoring: each target is scored before model update.",
            "Rolling FIFO removes the oldest observation exactly; no future draw enters the PMF.",
            "Partitions and alpha=200 are frozen from V322; only memory horizon varies.",
            "All windows share the same warmup and scored target sequence.",
            "Structural modality assignment is not independent official row-level verification.",
            "Retrospective prequential replay is not authenticated pre-close forecasting or edge evidence.",
            "No parameter search, V294 modification, canonical-history write, or model promotion."
        ],
    }
    (out / f"v324_window_{window_classic}_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--window-classic", type=int, choices=WINDOWS, required=True)
    parser.add_argument("--expected-sha256", default=EXPECTED_HISTORY_SHA256)
    parser.add_argument("--warmup-classic", type=int, default=WARMUP)
    args = parser.parse_args()
    print(json.dumps(evaluate_window(
        args.history, args.out, args.window_classic,
        args.expected_sha256, args.warmup_classic
    ), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
