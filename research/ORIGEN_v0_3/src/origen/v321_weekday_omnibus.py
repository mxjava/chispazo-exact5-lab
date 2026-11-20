"""V321 preregistered weekday omnibus; historical association only."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

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
    parsed, seen = [], set()
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
    values = np.asarray(values, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int8)
    if values.ndim != 1 or labels.ndim != 1 or len(values) != len(labels) or len(values) < 2:
        raise ValueError("invalid_sample")
    grand = float(values.mean())
    total = float(np.square(values - grand).sum())
    if total == 0.0:
        return 0.0
    between = 0.0
    for label in np.unique(labels):
        group = values[labels == label]
        between += len(group) * float(group.mean() - grand) ** 2
    return between / total


def analyze(rows, permutations=DEFAULT_PERMUTATIONS, seed=DEFAULT_SEED):
    if permutations < 1:
        raise ValueError("permutations_must_be_positive")
    labels = np.asarray([row[1] for row in rows], dtype=np.int8)
    values = {feature: np.asarray([row[2][feature] for row in rows], dtype=np.float64)
              for feature in FEATURES}
    observed = {feature: eta_squared(values[feature], labels) for feature in FEATURES}
    observed_max = max(observed.values())
    rng = np.random.Generator(np.random.PCG64(seed))
    null_maxima = np.empty(permutations, dtype=np.float64)
    for index in range(permutations):
        permuted_labels = rng.permutation(labels)
        null_maxima[index] = max(eta_squared(values[feature], permuted_labels)
                                 for feature in FEATURES)
    exceedances = int(np.count_nonzero(null_maxima >= observed_max))
    global_p = (exceedances + 1) / (permutations + 1)
    adjusted = {
        feature: (int(np.count_nonzero(null_maxima >= observed[feature])) + 1)
                 / (permutations + 1)
        for feature in FEATURES
    }
    return {
        "candidate": "V321_WEEKDAY_OMNIBUS",
        "classification": "HISTORICAL_ASSOCIATION_ONLY_NOT_PREDICTIVE",
        "n_classic_draws": len(rows),
        "weekday_counts": {str(day): int(np.count_nonzero(labels == day)) for day in WEEKDAYS},
        "features": list(FEATURES),
        "observed_eta_squared": observed,
        "familywise_adjusted_p": adjusted,
        "global_max_eta_squared": observed_max,
        "global_p_value": global_p,
        "global_exceedances": exceedances,
        "permutations": permutations,
        "rng": "numpy.random.Generator(PCG64)",
        "seed": seed,
        "decision": "HISTORICAL_ASSOCIATION_DETECTED" if global_p <= 0.05 else "NO_HISTORICAL_ASSOCIATION_DETECTED",
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
