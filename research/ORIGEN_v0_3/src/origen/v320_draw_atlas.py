"""V320 deterministic historical draw atlas; descriptive only, no predictive claims."""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from origen.exact5_modalities import assign_modality, read_history

UNIVERSE_SIZE = math.comb(28, 5)
PRIMES = frozenset((2, 3, 5, 7, 11, 13, 17, 19, 23))
SCALARS = ("sum", "range", "odd_count", "prime_count", "consecutive_pairs",
           "low_1_9", "mid_10_18", "high_19_28", "low_1_14", "max_gap")
FIELDS = ("contest", "date", "weekday", "weekday_iso", "numbers", *SCALARS,
          "gap_vector", "cell_id", "cell_size", "cell_probability",
          "sum_percentile", "range_percentile", "odd_count_percentile",
          "prime_count_percentile", "consecutive_pairs_percentile",
          "low_1_9_percentile", "mid_10_18_percentile", "high_19_28_percentile",
          "low_1_14_percentile", "max_gap_percentile", "prior_pair_counts",
          "prior_triple_counts", "draw_type", "mapping_status")


def features(nums):
    n = tuple(sorted(nums))
    if len(n) != 5 or len(set(n)) != 5 or any(x < 1 or x > 28 for x in n):
        raise ValueError("invalid_five_of_28_set")
    gaps = tuple(n[i+1]-n[i] for i in range(4))
    return {
        "sum": sum(n), "range": n[-1]-n[0],
        "odd_count": sum(x % 2 for x in n),
        "prime_count": sum(x in PRIMES for x in n),
        "consecutive_pairs": sum(g == 1 for g in gaps),
        "low_1_9": sum(1 <= x <= 9 for x in n),
        "mid_10_18": sum(10 <= x <= 18 for x in n),
        "high_19_28": sum(19 <= x <= 28 for x in n),
        "low_1_14": sum(x <= 14 for x in n),
        "max_gap": max(gaps), "gap_vector": gaps,
    }


def universe_reference():
    combos = list(itertools.combinations(range(1, 29), 5))
    if len(combos) != UNIVERSE_SIZE or len(set(combos)) != UNIVERSE_SIZE:
        raise RuntimeError("universe_cardinality_or_uniqueness_failure")
    scalar_values = {k: [] for k in SCALARS}
    cell_counts = Counter()
    for combo in combos:
        f = features(combo)
        for k in SCALARS:
            scalar_values[k].append(f[k])
        cell_counts[tuple(f[k] for k in SCALARS)] += 1
    for k in SCALARS:
        scalar_values[k].sort()
    return scalar_values, cell_counts


def _percentile(sorted_values, value):
    # Midrank empirical percentile against all 98,280 equally likely sets.
    import bisect
    left = bisect.bisect_left(sorted_values, value)
    right = bisect.bisect_right(sorted_values, value)
    return (left + right) / (2 * len(sorted_values))


def build_atlas(history_path, output_dir, expected_sha256=None):
    rows, digest = read_history(history_path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("v320_source_hash_mismatch")
    labelled, modality_audit = assign_modality(rows)
    for row in labelled:
        try:
            d = date.fromisoformat(row["date"])
        except Exception as exc:
            raise ValueError(f"invalid_iso_date_contest_{row['contest']}") from exc
        row["weekday"] = d.strftime("%A")
        row["weekday_iso"] = d.isoweekday()
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    if not classic:
        raise ValueError("no_classic_draws")
    scalar_values, cell_counts = universe_reference()
    pair_prior, triple_prior = Counter(), Counter()
    output = []
    weekday_counts = Counter()
    weekday_metrics = defaultdict(lambda: defaultdict(list))
    weekday_cells = defaultdict(Counter)
    for row in classic:
        f = features(row["numbers"])
        cell = tuple(f[k] for k in SCALARS)
        cell_size = cell_counts[cell]
        pairs = list(itertools.combinations(row["numbers"], 2))
        triples = list(itertools.combinations(row["numbers"], 3))
        item = {
            "contest": row["contest"], "date": row["date"],
            "weekday": row["weekday"], "weekday_iso": row["weekday_iso"],
            "numbers": "-".join(map(str, row["numbers"])),
            **{k: f[k] for k in SCALARS},
            "gap_vector": "-".join(map(str, f["gap_vector"])),
            "cell_id": "|".join(map(str, cell)), "cell_size": cell_size,
            "cell_probability": cell_size / UNIVERSE_SIZE,
            **{k + "_percentile": _percentile(scalar_values[k], f[k]) for k in SCALARS},
            "prior_pair_counts": ";".join(f"{a}-{b}:{pair_prior[(a,b)]}" for a,b in pairs),
            "prior_triple_counts": ";".join(f"{a}-{b}-{c}:{triple_prior[(a,b,c)]}" for a,b,c in triples),
            "draw_type": "CLASSIC", "mapping_status": row["mapping_status"],
        }
        output.append(item)
        weekday_counts[row["weekday"]] += 1
        for metric in SCALARS:
            weekday_metrics[row["weekday"]][metric].append(f[metric])
        weekday_cells[row["weekday"]][cell] += 1
        pair_prior.update(pairs)
        triple_prior.update(triples)
    # Independent calendar check: date-only values are never timezone-converted.
    weekday_order = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    weekday_report = {}
    for i, day in enumerate(weekday_order):
        n_day = weekday_counts[day]
        metrics = weekday_metrics[day]
        weekday_report[day] = {
            "iso_weekday": i + 1, "classic_draws": n_day,
            "fraction_of_classic": n_day / len(classic),
            "feature_means": {
                metric: (sum(metrics[metric]) / n_day if n_day else None)
                for metric in SCALARS
            },
            "most_frequent_exact_shape_cells": [
                {"cell_id": "|".join(map(str, cell)), "observed": count,
                 "uniform_expected_within_weekday": n_day * cell_counts[cell] / UNIVERSE_SIZE,
                 "exact_uniform_cell_probability": cell_counts[cell] / UNIVERSE_SIZE}
                for cell, count in weekday_cells[day].most_common(5)
            ],
        }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "v320_classic_draw_atlas.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    manifest = {
        "candidate": "V320_HISTORICAL_DRAW_ATLAS",
        "classification": "DESCRIPTIVE_ATLAS_ONLY_NO_EDGE_TEST",
        "source_sha256": digest, "source_rows": len(rows),
        "classic_draws": len(classic), "classic_first_contest": classic[0]["contest"],
        "classic_last_contest": classic[-1]["contest"],
        "universe_size": UNIVERSE_SIZE, "unique_universe_sets": UNIVERSE_SIZE,
        "feature_scalars": list(SCALARS),
        "weekday_counts": weekday_report,
        "modality_audit": modality_audit,
        "output_csv": csv_path.name,
        "output_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "warnings": [
            "Weekday is computed from the source's ISO calendar date without timezone conversion.",
            "Modality is assigned by the existing structural contest/date rule and remains pending row-level primary-source verification.",
            "Feature-cell probabilities are exact under uniform 5-of-28; observed frequencies and weekday splits are descriptive, not predictive.",
            "Prior pair/triple counts include only earlier Classic draws, never the target or future rows.",
            "This atlas does not test a weekday predictive edge or establish a physical mechanism."
        ],
    }
    (out / "v320_atlas_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--expected-sha256")
    a = p.parse_args()
    print(json.dumps(build_atlas(a.history, a.out, a.expected_sha256), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
