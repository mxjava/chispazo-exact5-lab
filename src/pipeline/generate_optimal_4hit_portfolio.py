"""Deterministic 30-line portfolio maximizing 4-of-5 coverage (not predictive).

Exhaustively optimizes coverage over all C(28,5)=98,280 possible winning sets.
The objective is combinatorial coverage only; it does not estimate which draw is
more likely and must never enter the predictive registration pipeline.

The hot path is vectorized with NumPy. Integer score arithmetic and ascending
candidate indices preserve the v1 greedy/tie-breaking semantics exactly.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import math
import sys
from pathlib import Path

import numpy as np

N = 28
R = 5
LINES = 30
UNIVERSE = math.comb(N, R)
MODE = "COMBINATORIAL_4HIT_COVERAGE_NOT_PREDICTIVE"
_DOMAIN = b"Exact5Combinatorial4HitCoverage/v1\0"


class _TieSampler:
    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        self.seed = str(seed).encode("ascii")
        self.counter = 0

    def randbelow(self, upper: int) -> int:
        bits = upper.bit_length()
        byte_count = (bits + 7) // 8
        mask = (1 << bits) - 1
        while True:
            message = (
                _DOMAIN
                + len(self.seed).to_bytes(4, "big")
                + self.seed
                + self.counter.to_bytes(16, "big")
            )
            self.counter += 1
            candidate = int.from_bytes(hashlib.sha256(message).digest()[:byte_count], "big") & mask
            if candidate < upper:
                return candidate


def _coverage_space():
    """Build compact integer index arrays once for the complete 5-of-28 space."""
    draws = list(itertools.combinations(range(1, N + 1), R))
    draw_index = {draw: i for i, draw in enumerate(draws)}
    quads = list(itertools.combinations(range(1, N + 1), R - 1))
    quad_index = {quad: i for i, quad in enumerate(quads)}

    quad_to_draws = np.asarray(
        [
            [
                draw_index[tuple(sorted((*quad, value)))]
                for value in range(1, N + 1)
                if value not in quad
            ]
            for quad in quads
        ],
        dtype=np.int32,
    )
    ticket_quads = np.asarray(
        [
            [quad_index[quad] for quad in itertools.combinations(draw, R - 1)]
            for draw in draws
        ],
        dtype=np.int32,
    )
    return draws, quad_to_draws, ticket_quads


def generate_portfolio(seed: int) -> tuple[list[tuple[int, ...]], list[int]]:
    """Return a deterministic balanced portfolio and per-line marginal coverage.

    Greedy marginal gain is exact: each ticket contributes the union of its five
    four-number subsets extended by one outside number. Its own five-number set
    is counted five times in those subsets, so four duplicate counts are removed.
    Ties first minimize number-frequency imbalance, then use the SHA-256 tie stream.

    NumPy evaluates all 98,280 candidate gains in one vectorized operation per
    iteration. This preserves the v1 candidate order and tie semantics.
    """
    sampler = _TieSampler(seed)
    draws, quad_to_draws, ticket_quads = _coverage_space()
    covered = np.zeros(len(draws), dtype=np.bool_)
    used = np.zeros(len(draws), dtype=np.bool_)
    draw_values = np.asarray(draws, dtype=np.int8)
    frequencies = np.zeros(N + 1, dtype=np.int64)
    selected: list[tuple[int, ...]] = []
    marginal_gains: list[int] = []

    for _ in range(LINES):
        # Each four-subset has 24 possible extensions. Count uncovered outcomes.
        quad_gains = (~covered[quad_to_draws]).sum(axis=1, dtype=np.int32)

        # Sum the five subset gains for every possible ticket simultaneously.
        gains = quad_gains[ticket_quads].sum(axis=1, dtype=np.int32)
        gains -= np.where(covered, 0, R - 1).astype(np.int32)
        gains[used] = -1

        best_gain = int(gains.max())
        candidates = np.flatnonzero(gains == best_gain)

        # Preserve the original secondary objective: minimum frequency-square
        # increment, then deterministic SHA-256 selection among exact ties.
        balance = (2 * frequencies[draw_values[candidates]] + 1).sum(axis=1)
        candidates = candidates[balance == balance.min()]
        chosen_id = int(candidates[sampler.randbelow(len(candidates))])

        chosen = draws[chosen_id]
        selected.append(chosen)
        marginal_gains.append(best_gain)
        used[chosen_id] = True
        frequencies[list(chosen)] += 1
        covered[quad_to_draws[ticket_quads[chosen_id]]] = True

    return selected, marginal_gains


def count_covered_draws(portfolio: list[tuple[int, ...]]) -> int:
    """Count all 5-number outcomes with at least four hits in any portfolio line."""
    covered: set[tuple[int, ...]] = set()
    for ticket in portfolio:
        for quad in itertools.combinations(ticket, R - 1):
            members = set(quad)
            for value in range(1, N + 1):
                if value not in members:
                    covered.add(tuple(sorted((*quad, value))))
    return len(covered)


def write_portfolio(portfolio: list[tuple[int, ...]], seed: int, stream) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["rank", "combo", "mode", "seed"])
    for rank, combo in enumerate(portfolio, start=1):
        writer.writerow([
            rank,
            "-".join(f"{value:02d}" for value in combo),
            MODE,
            seed,
        ])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a 30-line combinatorial 4-hit coverage portfolio; not a prediction."
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", help="CSV output path; defaults to stdout")
    args = parser.parse_args()
    portfolio, gains = generate_portfolio(args.seed)
    covered = count_covered_draws(portfolio)
    if covered != sum(gains):
        raise SystemExit("internal error: marginal gains do not equal exact coverage")
    if args.out:
        destination = Path(args.out)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as stream:
            write_portfolio(portfolio, args.seed, stream)
        print(
            f"mode={MODE} lines={len(portfolio)} covered_4plus={covered} "
            f"exact5_lines={len(set(portfolio))} seed={args.seed} out={destination}"
        )
    else:
        write_portfolio(portfolio, args.seed, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
