"""Reproducible uniform 5-of-28 portfolio generator.

This is a coverage/control mode, not a predictive model. It deliberately does
not read or modify the canonical history, V294, rankings, or prospective ledger.
"""
from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from pathlib import Path
from typing import Iterable

N = 28
R = 5
UNIVERSE = math.comb(N, R)


def unrank_combination(index: int, n: int = N, r: int = R) -> tuple[int, ...]:
    """Map a zero-based lexicographic rank to one r-combination of 1..n."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("index must be an integer")
    total = math.comb(n, r)
    if not 0 <= index < total:
        raise ValueError(f"index must be in [0, {total})")
    result: list[int] = []
    next_value = 1
    remaining_rank = index
    for position in range(r):
        remaining_slots = r - position - 1
        last_value = n - remaining_slots
        for candidate in range(next_value, last_value + 1):
            block = math.comb(n - candidate, remaining_slots)
            if remaining_rank < block:
                result.append(candidate)
                next_value = candidate + 1
                break
            remaining_rank -= block
    return tuple(result)


def generate_uniform_portfolio(seed: int, lines: int = 30) -> list[tuple[int, ...]]:
    """Sample distinct exact sets uniformly without replacement."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(lines, bool) or not isinstance(lines, int):
        raise TypeError("lines must be an integer")
    if not 1 <= lines <= UNIVERSE:
        raise ValueError(f"lines must be between 1 and {UNIVERSE}")
    rng = random.Random(seed)
    ranks = rng.sample(range(UNIVERSE), k=lines)
    return [unrank_combination(rank) for rank in ranks]


def format_combo(combo: Iterable[int]) -> str:
    values = tuple(combo)
    if len(values) != R or tuple(sorted(values)) != values or len(set(values)) != R:
        raise ValueError("combo must be five distinct ascending numbers")
    if any(value < 1 or value > N for value in values):
        raise ValueError("combo values must be in 1..28")
    return "-".join(f"{value:02d}" for value in values)


def write_portfolio(rows: list[tuple[int, ...]], seed: int, stream) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["rank", "combo", "mode", "seed"])
    for rank, combo in enumerate(rows, start=1):
        writer.writerow([rank, format_combo(combo), "UNIFORM_COVERAGE_NOT_PREDICTIVE", seed])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a reproducible uniform 5-of-28 coverage portfolio; not a prediction."
    )
    parser.add_argument("--seed", type=int, required=True, help="integer seed for exact reproducibility")
    parser.add_argument("--lines", type=int, default=30, help="number of distinct lines (default: 30)")
    parser.add_argument("--out", help="CSV output path; defaults to stdout")
    args = parser.parse_args()
    rows = generate_uniform_portfolio(args.seed, args.lines)
    if args.out:
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as stream:
            write_portfolio(rows, args.seed, stream)
        print(f"mode=UNIFORM_COVERAGE_NOT_PREDICTIVE lines={len(rows)} seed={args.seed} out={destination}")
    else:
        write_portfolio(rows, args.seed, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
