"""V323: context-conditioned hierarchical partition-and-divide replay.

The outcome partition is fixed (V322). The novel conditioning variable is a
pre-target 20-draw regime: mean overlap between consecutive Classic draws.
Each regime owns an independent, uniform-shrunk V322 partition model. The
target is scored before being added to the model for its own regime.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from statistics import median
from collections import Counter
from pathlib import Path

from origen.exact5_modalities import assign_modality, read_history
from origen.v322_hierarchical_partition import (
    ALPHA, TOP_K, UNIVERSE_SIZE, HierarchicalPartitionModel,
)

WINDOW = 20
LOW_OVERLAP = 0.75
HIGH_OVERLAP = 1.05
REGIMES = ("LOW_REPEAT", "TYPICAL_REPEAT", "HIGH_REPEAT")


def context_regime(prior_draws: list[list[int]]) -> tuple[str, float]:
    """Classify only the preceding 20 Classic draws; no target is accepted."""
    if len(prior_draws) != WINDOW:
        raise ValueError("context_requires_exactly_20_prior_draws")
    overlaps = [
        len(set(prior_draws[i]).intersection(prior_draws[i + 1]))
        for i in range(WINDOW - 1)
    ]
    mean_overlap = sum(overlaps) / len(overlaps)
    if mean_overlap < LOW_OVERLAP:
        return REGIMES[0], mean_overlap
    if mean_overlap > HIGH_OVERLAP:
        return REGIMES[2], mean_overlap
    return REGIMES[1], mean_overlap


def evaluate_history(
    history_path: str | Path,
    output_dir: str | Path,
    expected_sha256: str | None = None,
    warmup_classic: int = 800,
    alpha: float = ALPHA,
) -> dict:
    if not isinstance(warmup_classic, int) or isinstance(warmup_classic, bool) or warmup_classic < WINDOW:
        raise ValueError("warmup_must_be_integer_at_least_20")
    rows, digest = read_history(history_path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("canonical_history_sha256_mismatch")
    labelled, modality_audit = assign_modality(rows)
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws")

    models = {
        regime: HierarchicalPartitionModel(alpha=alpha)
        for regime in REGIMES
    }
    regime_counts = Counter()
    records = []

    # Prime regime-specific models using only pre-target context from warmup.
    for i in range(WINDOW, warmup_classic):
        regime, _ = context_regime([r["numbers"] for r in classic[i - WINDOW:i]])
        models[regime].update(classic[i]["numbers"])
        regime_counts[regime] += 1

    # Strict prequential scoring: select regime from prior 20, score, then update.
    for i in range(warmup_classic, len(classic)):
        prior = [r["numbers"] for r in classic[i - WINDOW:i]]
        regime, mean_overlap = context_regime(prior)
        model = models[regime]
        target = classic[i]
        if model.draws_seen:
            scored = model.score(target["numbers"])
        else:
            # Empty regime: exact-uniform fallback, tied over the full universe.
            scored = {
                "target_probability": 1.0 / UNIVERSE_SIZE,
                "log_lift_vs_uniform": 0.0,
                "rank_low": 1,
                "rank_high": UNIVERSE_SIZE,
                "rank_mid": (UNIVERSE_SIZE + 1) / 2,
                "tie_size": UNIVERSE_SIZE,
                **{f"top_{k}_inclusion_probability": k / UNIVERSE_SIZE for k in TOP_K},
            }
        records.append({
            "contest": target["contest"],
            "date": target["date"],
            "numbers": "-".join(map(str, target["numbers"])),
            "context_regime": regime,
            "prior_20_mean_consecutive_overlap": mean_overlap,
            "prior_regime_draws": model.draws_seen,
            **scored,
        })
        model.update(target["numbers"])
        regime_counts[regime] += 1

    lifts = [r["log_lift_vs_uniform"] for r in records]
    top_k = {
        str(k): sum(r[f"top_{k}_inclusion_probability"] for r in records)
        for k in TOP_K
    }
    uniform_top_k = {
        str(k): len(records) * k / UNIVERSE_SIZE for k in TOP_K
    }
    regime_summary = {}
    for regime in REGIMES:
        subset = [r for r in records if r["context_regime"] == regime]
        regime_summary[regime] = {
            "scored_targets": len(subset),
            "training_observations_available_at_end": models[regime].draws_seen,
            "mean_log_lift": (
                sum(r["log_lift_vs_uniform"] for r in subset) / len(subset)
                if subset else None
            ),
            "cumulative_log_lift": sum(r["log_lift_vs_uniform"] for r in subset),
            "positive_fraction": (
                sum(r["log_lift_vs_uniform"] > 0 for r in subset) / len(subset)
                if subset else None
            ),
        }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "v323_context_partition_scores.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    report = {
        "schema": "EXACT5_V323_CONTEXT_CONDITIONED_PARTITION_V1",
        "classification": "RETROSPECTIVE_PREQUENTIAL_DIAGNOSTIC_NO_EDGE",
        "source_sha256": digest,
        "source_rows": len(rows),
        "classic_draws": len(classic),
        "first_classic_contest": classic[0]["contest"],
        "last_classic_contest": classic[-1]["contest"],
        "warmup_classic": warmup_classic,
        "scored_targets": len(records),
        "universe_size": UNIVERSE_SIZE,
        "fixed_alpha": alpha,
        "context": {
            "window_classic_draws": WINDOW,
            "statistic": "mean set overlap between consecutive draws in preceding 20 Classic draws",
            "low_repeat_if_below": LOW_OVERLAP,
            "high_repeat_if_above": HIGH_OVERLAP,
            "regimes": list(REGIMES),
        },
        "mean_log_lift": sum(lifts) / len(lifts),
        "median_log_lift": median(lifts),
        "cumulative_log_lift": sum(lifts),
        "positive_log_lift_fraction": sum(x > 0 for x in lifts) / len(lifts),
        "exact_rank_1_count": sum(r["rank_low"] == r["rank_high"] == 1 for r in records),
        "expected_top_k_inclusions": top_k,
        "uniform_expected_top_k_inclusions": uniform_top_k,
        "regime_results": regime_summary,
        "modality_audit": modality_audit,
        "scores_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "warnings": [
            "Context regime is computed only from the preceding 20 structurally assigned Classic draws.",
            "Each regime has a separate fixed V322 model; the target is scored before updating its regime model.",
            "This is retrospective prequential reconstruction, not authenticated pre-close forecasting.",
            "Modality is structurally assigned and pending row-level official verification.",
            "No parameter search, threshold retuning, model promotion, or V294 change.",
            "No subgroup result is edge evidence without multiplicity correction and independent prospective confirmation.",
        ],
    }
    (out / "v323_context_partition_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--expected-sha256")
    parser.add_argument("--warmup-classic", type=int, default=800)
    args = parser.parse_args()
    print(json.dumps(evaluate_history(
        args.history, args.out, args.expected_sha256, args.warmup_classic
    ), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
