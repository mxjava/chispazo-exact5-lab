"""Aggregate immutable uniform-control evaluation reports across completed contests.

Descriptive only: this does not evaluate predictive registrations or claim model lift.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from src.pipeline.evaluate_uniform_portfolio import MODE


def _load_report(path: str | Path) -> dict:
    try:
        report = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read evaluation report {path}: {exc}") from exc
    required = {
        "status", "mode", "contest_id", "seed", "portfolio_sha256", "line_count",
        "best_hits", "exact5_count", "hit_distribution", "uniform_null",
        "predictive_claim", "prospective_registration_created",
    }
    if not isinstance(report, dict) or not required.issubset(report):
        raise ValueError(f"report {path} is missing required fields")
    if report["status"] != "EVALUATED_CONTROL_ONLY" or report["mode"] != MODE:
        raise ValueError(f"report {path} is not a uniform control evaluation")
    if report["predictive_claim"] is not False or report["prospective_registration_created"] is not False:
        raise ValueError(f"report {path} contains an invalid predictive/registration flag")
    if not isinstance(report["contest_id"], int) or isinstance(report["contest_id"], bool) or report["contest_id"] <= 0:
        raise ValueError(f"report {path} has an invalid contest_id")
    if not isinstance(report["line_count"], int) or isinstance(report["line_count"], bool) or report["line_count"] < 1:
        raise ValueError(f"report {path} has an invalid line_count")
    digest = report["portfolio_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError(f"report {path} has an invalid portfolio SHA-256")
    distribution = report["hit_distribution"]
    if not isinstance(distribution, dict) or set(distribution) != {str(k) for k in range(6)}:
        raise ValueError(f"report {path} has an invalid hit distribution")
    if any(not isinstance(distribution[str(k)], int) or isinstance(distribution[str(k)], bool) or distribution[str(k)] < 0 for k in range(6)):
        raise ValueError(f"report {path} has negative or non-integer hit counts")
    if sum(distribution.values()) != report["line_count"]:
        raise ValueError(f"report {path} hit distribution does not sum to line_count")
    if report["exact5_count"] != distribution["5"]:
        raise ValueError(f"report {path} exact5_count does not match hit distribution")
    if report["best_hits"] != max(k for k in range(6) if distribution[str(k)] > 0):
        raise ValueError(f"report {path} best_hits does not match hit distribution")
    null = report["uniform_null"]
    if not isinstance(null, dict) or null.get("universe_size") != 98280 or null.get("line_count") != report["line_count"]:
        raise ValueError(f"report {path} has incompatible uniform-null calibration")
    return report


def aggregate_control_reports(paths: list[str | Path]) -> dict:
    if not paths:
        raise ValueError("provide at least one completed evaluation report")
    reports = [_load_report(path) for path in paths]
    contests = [r["contest_id"] for r in reports]
    hashes = [r["portfolio_sha256"] for r in reports]
    if len(set(contests)) != len(contests):
        raise ValueError("duplicate contest_id; one control evaluation per contest is allowed")
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicate portfolio hash; do not reuse the same portfolio as an independent control")
    aggregate = {str(k): sum(r["hit_distribution"][str(k)] for r in reports) for k in range(6)}
    total_lines = sum(r["line_count"] for r in reports)
    expected = {str(k): sum(r["uniform_null"]["expected_hit_distribution"][str(k)] for r in reports) for k in range(6)}
    return {
        "status": "AGGREGATED_CONTROL_ONLY",
        "mode": MODE,
        "contest_count": len(reports),
        "contest_ids": contests,
        "portfolio_sha256": hashes,
        "total_lines": total_lines,
        "observed_hit_distribution": aggregate,
        "expected_hit_distribution_under_uniform_null": expected,
        "observed_exact5_count": aggregate["5"],
        "expected_exact5_count_under_uniform_null": expected["5"],
        "predictive_claim": False,
        "prospective_registration_created": False,
        "interpretation": "descriptive aggregation of uniform controls only; not a predictive-edge test",
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
    parser = argparse.ArgumentParser(description="Aggregate completed uniform-control reports (descriptive only)")
    parser.add_argument("--reports", nargs="+", required=True, help="completed control evaluation JSON files")
    parser.add_argument("--out")
    args = parser.parse_args()
    try:
        report = aggregate_control_reports(args.reports)
    except ValueError as exc:
        raise SystemExit(f"Cannot aggregate control reports: {exc}") from exc
    if args.out:
        _write_json_atomically(args.out, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
