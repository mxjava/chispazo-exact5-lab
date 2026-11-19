"""V321 preregistered weekday omnibus; historical association only."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path

FEATURES = ("sum", "range", "odd_count", "prime_count", "consecutive_pairs",
            "low_1_9", "mid_10_18", "high_19_28", "low_1_14", "max_gap")
WEEKDAYS = tuple(range(1, 8))
DEFAULT_PERMUTATIONS = 1999
DEFAULT_SEED = 3212026


def load_atlas(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("empty_atlas")
    parsed = []
    seen = set()
    for row in rows:
        contest = int(row["contest"])
        weekday = int(row["weekday_iso"])
        if contest in seen:
            raise ValueError("duplicate_contest")
        seen.add(contest)
        if weekday not in WEEKDAYS:
            raise ValueError("invalid_weekday")
        values = {name: float(row[name]) for name in FEATURES}
        if not all(math.isfinite(value) for value in values.values()):
            raise ValueError("non_finite_feature")
        parsed.append((contest, weekday, values))
    parsed.sort(key=lambda item: item[0])
    if set(item[1] for item in parsed) != set(WEEKDAYS):
        raise ValueError("missing_weekday")
    return parsed


def eta_squared(values, labels):
    if len(values) != len(labels) or len(values) < 2:
        raise ValueError("invalid_sample")
    grand = sum(values) / len(values)
    total = sum((value - grand) ** 2 for value in values)
    if total == 0:
        return 0.0
    groups = {}
    for value, label in zip(values, labels):
        groups.setdefault(label, []).append(value)
    between = sum(len(group) * (sum(group) / len(group) - grand) ** 2
                  for group in groups.values())
    return between / total


def analyze(rows, permutations=DEFAULT_PERMUTATIONS, seed=DEFAULT_SEED):
    if permutations < 1:
        raise ValueError("permutations_must_be_positive")
    labels = [row[1] for row in rows]
    observed = {
        feature: eta_squared([row[2][feature] for row in rows], labels)
        for feature in FEATURES
    }
    observed_max = max(observed.values())
    rng = random.Random(seed)
    null_maxima = []
    null_by_feature = {feature: [] for feature in FEATURES}
    shuffled = labels[:]
    for _ in range(permutations):
        rng.shuffle(shuffled)
        stats = {
            feature: eta_squared([row[2][feature] for row in rows], shuffled)
            for feature in FEATURES
        }
        null_maxima.append(max(stats.values()))
        for feature, value in stats.items():
            null_by_feature[feature].append(value)
    global_exceed = sum(value >= observed_max for value in null_maxima)
    adjusted = {
        feature: (sum(maximum >= observed[feature] for maximum in null_maxima) + 1)
                 / (permutations + 1)
        for feature in FEATURES
    }
    return {
        "candidate": "V321_WEEKDAY_OMNIBUS",
        "classification": "HISTORICAL_ASSOCIATION_ONLY_NOT_PREDICTIVE",
        "n_classic_draws": len(rows),
        "weekday_counts": {str(day): labels.count(day) for day in WEEKDAYS},
        "features": list(FEATURES),
        "observed_eta_squared": observed,
        "familywise_adjusted_p": adjusted,
        "global_max_eta_squared": observed_max,
        "global_p_value": (global_exceed + 1) / (permutations + 1),
        "global_exceedances": global_exceed,
        "permutations": permutations,
        "seed": seed,
        "decision": "HISTORICAL_ASSOCIATION_DETECTED" if (global_exceed + 1) / (permutations + 1) <= 0.05 else "NO_HISTORICAL_ASSOCIATION_DETECTED",
        "warning": "Historical weekday association, if detected, is not predictive evidence and does not establish a physical mechanism."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--atlas", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    result = analyze(load_atlas(args.atlas), args.permutations, args.seed)
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
