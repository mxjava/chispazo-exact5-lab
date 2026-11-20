"""V312 fixed-weight Classic-only Exact5 mixture.

Research-only implementation of the frozen preregistration. No posterior
updates, parameter fitting, modality pooling, or writes to canonical data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from collections import Counter
from pathlib import Path

from origen.exact5_modalities import assign_modality, read_history

UNIVERSE = 28
PICK = 5
UNIFORM = 1.0 / math.comb(UNIVERSE, PICK)
WINDOWS = (50, 200, 800)
HALF_LIVES = (16, 32, 64)
BETAS = (0.15, 0.30, 0.60)
FEATURES = tuple(f"freq{w}" for w in WINDOWS) + tuple(f"ewma{h}" for h in HALF_LIVES) + ("hotgap", "duegap", "transition")
EXPERTS = tuple((feature, beta) for feature in FEATURES for beta in BETAS)
assert len(EXPERTS) == 27


def _validate_classic_stream(labelled: list[dict]) -> list[dict]:
    classic = [r for r in labelled if r.get("draw_type") == "CLASSIC"]
    if len(classic) < 2:
        raise ValueError("insufficient_classic_history")
    classic.sort(key=lambda r: int(r["contest"]))
    seen = set()
    previous = 0
    for row in classic:
        contest = int(row["contest"])
        numbers = row.get("numbers")
        if contest in seen or contest <= previous:
            raise ValueError("duplicate_or_nonchronological_classic_contest")
        if not isinstance(numbers, (list, tuple)) or len(numbers) != PICK:
            raise ValueError("invalid_classic_draw_shape")
        if any(type(n) is not int or n < 1 or n > UNIVERSE for n in numbers) or len(set(numbers)) != PICK:
            raise ValueError("invalid_classic_draw_numbers")
        seen.add(contest)
        previous = contest
    return classic


def _zscore(values: list[float]) -> list[float]:
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    sd = math.sqrt(variance)
    if sd < 1e-12:
        sd = 1.0
    return [(x - mean) / sd for x in values]


def _features(draws: list[dict], t: int) -> dict[str, list[float]]:
    """Feature vectors for target index t; only draws[:t] are consulted."""
    if t < 1 or t >= len(draws):
        raise ValueError("feature_target_index_out_of_range")
    out: dict[str, list[float]] = {}
    for window in WINDOWS:
        sub = draws[max(0, t - window):t]
        counts = Counter(n for row in sub for n in row["numbers"])
        out[f"freq{window}"] = [counts[n] / max(1, len(sub)) for n in range(1, UNIVERSE + 1)]
    for half_life in HALF_LIVES:
        sub = draws[max(0, t - 6 * half_life):t]
        values = [0.0] * UNIVERSE
        decay_sum = 0.0
        for age, row in enumerate(reversed(sub)):
            weight = 0.5 ** (age / half_life)
            decay_sum += weight
            for number in row["numbers"]:
                values[number - 1] += weight
        out[f"ewma{half_life}"] = [v / max(decay_sum, 1e-12) for v in values]
    last = [t + 1] * UNIVERSE
    for age, row in enumerate(reversed(draws[max(0, t - 500):t]), start=1):
        for number in row["numbers"]:
            if last[number - 1] > t:
                last[number - 1] = age
    last = [501 if value > t else value for value in last]
    out["hotgap"] = [-float(value) for value in last]
    out["duegap"] = [float(min(value, 100)) for value in last]

    transition = [0.0] * UNIVERSE
    if t >= 2:
        context = set(draws[t - 1]["numbers"])
        start = max(1, t - 800)
        denominator = 0
        # Deliberately stop before t-1: exclude the current context row.
        for j in range(start, t - 1):
            if context.intersection(draws[j - 1]["numbers"]):
                for number in draws[j]["numbers"]:
                    transition[number - 1] += 1.0
                denominator += 1
        transition = [v / max(1, denominator) for v in transition]
    out["transition"] = transition
    return out


def _expert_probability(feature_values: list[float], beta: float, chosen: list[int]) -> float:
    standardized = _zscore(feature_values)
    logits = [beta * value for value in standardized]
    maximum = max(logits)
    weights = [math.exp(value - maximum) for value in logits]
    elementary = [1.0] + [0.0] * PICK
    for weight in weights:
        for k in range(PICK, 0, -1):
            elementary[k] += weight * elementary[k - 1]
    denominator = elementary[PICK]
    numerator = math.prod(weights[n - 1] for n in chosen)
    probability = numerator / denominator
    if not math.isfinite(probability) or probability <= 0.0:
        raise ArithmeticError("invalid_expert_probability")
    return probability


def _mixture_probability(feature_map: dict[str, list[float]], chosen: list[int]) -> tuple[float, list[float]]:
    expert_probs = [_expert_probability(feature_map[feature], beta, chosen) for feature, beta in EXPERTS]
    probability = 0.5 * UNIFORM + 0.5 * (sum(expert_probs) / len(expert_probs))
    if not math.isfinite(probability) or probability < 0.5 * UNIFORM:
        raise ArithmeticError("invalid_v312_mixture_probability")
    return probability, expert_probs


def evaluate_v312(labelled: list[dict], warmup_classic: int = 800, source_sha256: str = "UNSPECIFIED", code_commit: str = "UNSPECIFIED") -> tuple[dict, list[dict]]:
    """Chronological retrospective replay; output is diagnostic, never edge certification."""
    if type(warmup_classic) is not int or warmup_classic < 1:
        raise ValueError("warmup_must_be_positive_integer")
    classic = _validate_classic_stream(labelled)
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws_after_warmup")
    records = []
    for t in range(warmup_classic, len(classic)):
        target = classic[t]
        features = _features(classic, t)
        probability, expert_probs = _mixture_probability(features, target["numbers"])
        log_lift = math.log(probability) - math.log(UNIFORM)
        records.append({
            "target_contest": int(target["contest"]),
            "feature_cutoff_contest": int(classic[t - 1]["contest"]),
            "log_lift_vs_uniform": log_lift,
            "mixture_probability": probability,
            "uniform_probability": UNIFORM,
            "minimum_probability_floor": 0.5 * UNIFORM,
            "expert_probability_mean": sum(expert_probs) / len(expert_probs),
            "expert_count": len(expert_probs),
        })
    values = [r["log_lift_vs_uniform"] for r in records]
    report = {
        "schema": "EXACT5_V312_STATIC_MIXTURE_V1",
        "candidate": "V312",
        "classification": "RESEARCH_ONLY_RETROSPECTIVE_NOT_EDGE_EVIDENCE",
        "source_sha256": source_sha256,
        "code_commit": code_commit,
        "classic_draws": len(classic),
        "warmup_classic_draws": warmup_classic,
        "scored_targets": len(records),
        "first_target_contest": records[0]["target_contest"],
        "last_target_contest": records[-1]["target_contest"],
        "expert_count": len(EXPERTS),
        "expert_features": list(FEATURES),
        "betas": list(BETAS),
        "fixed_weights": {"uniform": 0.5, "nonuniform_expert_mean": 0.5},
        "mean_log_lift": sum(values) / len(values),
        "cumulative_log_lift": sum(values),
        "positive_fraction": sum(v > 0 for v in values) / len(values),
        "minimum_probability_floor": 0.5 * UNIFORM,
        "leakage_contract": "feature_cutoff_contest is strictly earlier than target; only Classic rows are supplied to feature generation",
        "prospective_gates_satisfied": False,
        "warning": "Retrospective replay is for implementation integrity only; no prospective confirmation, independent custody, multiplicity-adjusted test, or Exact5 anytime e-value is established."
    }
    return report, records


def run(history_path: str, output_dir: str, warmup: int = 800, code_commit: str = "UNSPECIFIED") -> dict:
    rows, digest = read_history(history_path)
    labelled, _ = assign_modality(rows)
    report, records = evaluate_v312(labelled, warmup, digest, code_commit)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "v312_classic_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (out / "v312_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="V312 frozen Classic-only static mixture replay")
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--warmup", type=int, default=800)
    parser.add_argument("--code-commit", default="UNSPECIFIED")
    args = parser.parse_args()
    print(json.dumps(run(args.history, args.out, args.warmup, args.code_commit), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
