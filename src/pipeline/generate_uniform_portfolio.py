"""Reproducible uniform 5-of-28 portfolio generator.

This is a coverage/control mode, not a predictive model. It deliberately does
not read or modify the canonical history, V294, rankings, or prospective ledger.
The rank sampler is versioned and uses SHA-256 counter expansion plus rejection
sampling, so a seed maps to the same ordered portfolio across Python versions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sys
from pathlib import Path
from typing import Iterable

N = 28
R = 5
UNIVERSE = math.comb(N, R)
_SAMPLER_DOMAIN = b"Exact5UniformPortfolio/v1\0"


class _DeterministicRankSampler:
    """Versioned deterministic stream with unbiased bounded-integer sampling."""

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        self._seed = str(seed).encode("ascii")
        self._counter = 0

    def randbelow(self, upper: int) -> int:
        if isinstance(upper, bool) or not isinstance(upper, int):
            raise TypeError("upper must be an integer")
        if upper <= 0:
            raise ValueError("upper must be positive")
        bits = upper.bit_length()
        byte_count = (bits + 7) // 8
        mask = (1 << bits) - 1
        while True:
            message = (
                _SAMPLER_DOMAIN
                + len(self._seed).to_bytes(4, "big")
                + self._seed
                + self._counter.to_bytes(16, "big")
            )
            self._counter += 1
            block = hashlib.sha256(message).digest()
            candidate = int.from_bytes(block[:byte_count], "big") & mask
            if candidate < upper:
                return candidate


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
    """Sample distinct exact sets uniformly without replacement.

    Floyd's algorithm chooses an ordered uniform sample of distinct ranks.
    Each bounded draw uses rejection sampling, avoiding modulo bias.
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(lines, bool) or not isinstance(lines, int):
        raise TypeError("lines must be an integer")
    if not 1 <= lines <= UNIVERSE:
        raise ValueError(f"lines must be between 1 and {UNIVERSE}")
    sampler = _DeterministicRankSampler(seed)
    selected: set[int] = set()
    ranks: list[int] = []
    for upper in range(UNIVERSE - lines + 1, UNIVERSE + 1):
        candidate = sampler.randbelow(upper)
        rank = upper - 1 if candidate in selected else candidate
        selected.add(rank)
        ranks.append(rank)
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
