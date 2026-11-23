"""Evaluate a uniform-coverage control portfolio after an observed draw.

This evaluator is deliberately separate from predictive registration/evaluation.
It never reads or writes the prospective ledger and labels all outputs as control-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path


MODE = "UNIFORM_COVERAGE_NOT_PREDICTIVE"
FIELDS = ["rank", "combo", "mode", "seed"]


def _parse_combo(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0[1-9]|1\d|2[0-8])(?:-(?:0[1-9]|1\d|2[0-8])){4}", value):
        raise ValueError(f"invalid exact-5 combo encoding: {value!r}")
    nums = tuple(int(part) for part in value.split("-"))
    if tuple(sorted(nums)) != nums or len(set(nums)) != 5:
        raise ValueError(f"combo must contain five distinct ascending values: {value!r}")
    return nums


def evaluate_uniform_portfolio(portfolio_path: str | Path, contest_id: int, result: list[int] | tuple[int, ...]) -> dict:
    """Validate and score a generated uniform CSV against one completed result."""
    if isinstance(contest_id, bool) or not isinstance(contest_id, int) or contest_id <= 0:
        raise ValueError("contest_id must be a positive integer")
    if len(result) != 5 or any(isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 28 for n in result) or len(set(result)) != 5:
        raise ValueError("result must contain exactly five distinct integers in 1..28")

    path = Path(portfolio_path)
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("portfolio must be UTF-8 CSV") from exc
    import csv
    from io import StringIO
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames != FIELDS:
        raise ValueError(f"portfolio columns must be exactly {FIELDS}")
    rows = list(reader)
    if not rows:
        raise ValueError("portfolio must contain at least one line")

    combos: list[tuple[int, ...]] = []
    seed_value: int | None = None
    for expected_rank, row in enumerate(rows, start=1):
        if row.get("mode") != MODE:
            raise ValueError("portfolio is not explicitly marked as uniform non-predictive coverage")
        try:
            rank = int(row["rank"])
            seed = int(row["seed"])
        except (TypeError, ValueError) as exc:
            raise ValueError("rank and seed must be integers") from exc
        if str(rank) != row["rank"] or rank != expected_rank:
            raise ValueError("portfolio ranks must be contiguous, starting at 1")
        if str(seed) != row["seed"]:
            raise ValueError("seed must be a canonical integer")
        if seed_value is None:
            seed_value = seed
        elif seed != seed_value:
            raise ValueError("all portfolio rows must use the same seed")
        combos.append(_parse_combo(row["combo"]))

    if len(set(combos)) != len(combos):
        raise ValueError("portfolio contains duplicate exact-5 combinations")

    winning = set(result)
    hits = [len(set(combo) & winning) for combo in combos]
    distribution = {str(k): hits.count(k) for k in range(6)}
    best_hits = max(hits)
    return {
        "status": "EVALUATED_CONTROL_ONLY",
        "mode": MODE,
        "contest_id": contest_id,
        "seed": seed_value,
        "portfolio_sha256": hashlib.sha256(raw).hexdigest(),
        "line_count": len(combos),
        "result": "-".join(f"{n:02d}" for n in sorted(result)),
        "best_hits": best_hits,
        "exact5_count": hits.count(5),
        "hit_distribution": distribution,
        "lines": [
            {"rank": rank, "combo": "-".join(f"{n:02d}" for n in combo), "hits": hit}
            for rank, (combo, hit) in enumerate(zip(combos, hits), start=1)
        ],
        "predictive_claim": False,
        "prospective_registration_created": False,
    }


def _write_json_atomically(path: str | Path, report: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, destination)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a uniform non-predictive coverage portfolio against a completed draw")
    parser.add_argument("--portfolio", required=True)
    parser.add_argument("--contest-id", type=int, required=True)
    parser.add_argument("--result", type=int, nargs=5, required=True)
    parser.add_argument("--out")
    args = parser.parse_args()
    try:
        report = evaluate_uniform_portfolio(args.portfolio, args.contest_id, args.result)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Cannot evaluate uniform portfolio: {exc}") from exc
    if args.out:
        _write_json_atomically(args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
