from __future__ import annotations
import random
from typing import Iterable

def shuffled_rows(rows: Iterable[Iterable[int]], seed: int) -> list[list[int]]:
    """Preserve each row's composition while destroying row order."""
    data = [list(r) for r in rows]
    random.Random(seed).shuffle(data)
    return data

def within_row_permutation(rows: Iterable[Iterable[int]], seed: int) -> list[list[int]]:
    """Preserve each row's set, randomize column/order representation."""
    rng = random.Random(seed)
    out = []
    for row in rows:
        x = list(row)
        rng.shuffle(x)
        out.append(x)
    return out

def independent_uniform_draws(n: int, universe: int = 28, k: int = 5, seed: int = 0) -> list[list[int]]:
    if n < 0 or universe < k or k < 1:
        raise ValueError("invalid_dimensions")
    rng = random.Random(seed)
    return [sorted(rng.sample(range(1, universe + 1), k)) for _ in range(n)]

def null_suite(rows: Iterable[Iterable[int]], seed: int = 0) -> dict:
    data = [list(r) for r in rows]
    return {
        "row_order_destroyed": shuffled_rows(data, seed),
        "within_row_permuted": within_row_permutation(data, seed + 1),
        "independent_uniform": independent_uniform_draws(len(data), seed=seed + 2)
    }
