#!/usr/bin/env python3
"""Independent exhaustive verifier for the 30-line Chispazo coverage portfolio.

This verifies combinatorial coverage only. It does not estimate predictive edge.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import Counter
from pathlib import Path

V = 28
DRAW_SIZE = 5
EXPECTED_LINES = 30
EXPECTED_DRAWS = 98_280


def load_portfolio(path: Path) -> list[tuple[int, ...]]:
    lines: list[tuple[int, ...]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            values = tuple(sorted(int(x) for x in row["combo"].split("-")))
            if len(values) != DRAW_SIZE or len(set(values)) != DRAW_SIZE:
                raise ValueError(f"invalid line: {row['combo']}")
            if min(values) < 1 or max(values) > V:
                raise ValueError(f"out-of-range line: {row['combo']}")
            lines.append(values)
    if len(lines) != EXPECTED_LINES or len(set(lines)) != EXPECTED_LINES:
        raise ValueError(f"expected {EXPECTED_LINES} unique lines, got {len(lines)}")
    return lines


def verify(lines: list[tuple[int, ...]]) -> dict:
    max_pair_overlap = max(
        len(set(a) & set(b)) for a, b in itertools.combinations(lines, 2)
    )
    if max_pair_overlap > 2:
        raise AssertionError(f"4+ coverage can overlap: max line intersection={max_pair_overlap}")

    distribution = Counter()
    for draw in itertools.combinations(range(1, V + 1), DRAW_SIZE):
        draw_set = set(draw)
        best = max(len(draw_set.intersection(line)) for line in lines)
        distribution[best] += 1

    total = sum(distribution.values())
    if total != EXPECTED_DRAWS:
        raise AssertionError(f"enumerated {total}, expected {EXPECTED_DRAWS}")

    covered_3plus = sum(distribution[k] for k in (3, 4, 5))
    covered_4plus = sum(distribution[k] for k in (4, 5))
    return {
        "status": "PASS",
        "scope": "COMBINATORIAL_COVERAGE_ONLY_NOT_PREDICTIVE",
        "universe": {"v": V, "draw_size": DRAW_SIZE, "draws": total},
        "portfolio": {"lines": len(lines), "unique_lines": len(set(lines)),
                      "max_pairwise_intersection": max_pair_overlap},
        "best_hit_distribution": {str(k): distribution[k] for k in range(6)},
        "coverage": {
            "3plus_count": covered_3plus,
            "3plus_rate": covered_3plus / total,
            "4plus_count": covered_4plus,
            "4plus_rate": covered_4plus / total,
            "5of5_count": distribution[5],
            "5of5_rate": distribution[5] / total,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--portfolio",
        type=Path,
        default=Path("runs/optimal_3plus_coverage_20261126.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(load_portfolio(args.portfolio))
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
