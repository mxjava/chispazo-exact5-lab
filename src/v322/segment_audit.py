"""Independent segmentation audit for prequential Exact5 score exports.

This is descriptive diagnosis only: it does not tune a model or establish an edge.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SCORE_COLUMNS = {"contest", "date", "numbers", "log_lift_vs_uniform"}


def validate_join(scores: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    missing = SCORE_COLUMNS - set(scores.columns)
    if missing:
        raise ValueError(f"score file missing columns: {sorted(missing)}")
    required_history = {"CONCURSO", "FECHA", "R1", "R2", "R3", "R4", "R5"}
    if required_history - set(history.columns):
        raise ValueError("history file missing required canonical columns")
    s = scores.copy()
    h = history.copy()
    s["contest"] = pd.to_numeric(s["contest"], errors="raise").astype(int)
    h["CONCURSO"] = pd.to_numeric(h["CONCURSO"], errors="raise").astype(int)
    s["date"] = pd.to_datetime(s["date"], errors="raise").dt.date
    h["date_check"] = pd.to_datetime(h["FECHA"], errors="raise").dt.date
    h["numbers_check"] = h[["R1", "R2", "R3", "R4", "R5"]].astype(int).apply(
        lambda row: "-".join(f"{v:02d}" for v in sorted(row)), axis=1
    )
    joined = s.merge(
        h[["CONCURSO", "date_check", "numbers_check"]],
        left_on="contest", right_on="CONCURSO", how="left", validate="one_to_one"
    )
    if joined["date_check"].isna().any():
        raise ValueError("score contests missing from canonical history")
    if not (joined["date"] == joined["date_check"]).all():
        raise ValueError("score dates do not match canonical history")
    if not (joined["numbers"].astype(str) == joined["numbers_check"]).all():
        raise ValueError("score winning combinations do not match canonical history")
    values = pd.to_numeric(joined["log_lift_vs_uniform"], errors="raise").to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("log-lift contains non-finite values")
    return joined.sort_values(["date", "contest"]).reset_index(drop=True)


def block_bootstrap_mean_ci(values, *, block_length=30, resamples=3000, seed=20261119):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < block_length or block_length < 1 or resamples < 1:
        raise ValueError("invalid bootstrap dimensions")
    blocks = np.asarray([x[i:i + block_length] for i in range(len(x) - block_length + 1)])
    rng = np.random.default_rng(seed)
    blocks_per_sample = int(np.ceil(len(x) / block_length))
    indices = rng.integers(0, len(blocks), size=(resamples, blocks_per_sample))
    means = blocks[indices].sum(axis=(1, 2)) / (blocks_per_sample * block_length)
    low, high = np.quantile(means, [0.025, 0.975])
    return {"ci95_low": float(low), "ci95_high": float(high),
            "bootstrap_fraction_nonnegative": float(np.mean(means >= 0))}


def segment_summary(frame: pd.DataFrame, *, block_length=30, resamples=3000, seed=20261119):
    x = frame["log_lift_vs_uniform"].to_numpy(float)
    result = {
        "n": int(len(x)),
        "mean_log_lift": float(np.mean(x)),
        "median_log_lift": float(np.median(x)),
        "positive_fraction": float(np.mean(x > 0)),
        "cumulative_log_lift": float(np.sum(x)),
    }
    if len(x) >= block_length:
        result.update(block_bootstrap_mean_ci(
            x, block_length=block_length, resamples=resamples, seed=seed
        ))
    return result


def build_report(scores: pd.DataFrame, history: pd.DataFrame, *, block_length=30,
                 resamples=3000, seed=20261119):
    joined = validate_join(scores, history)
    joined["weekday"] = pd.to_datetime(joined["date"].astype(str)).dt.day_name()
    weekday = {}
    for i, day in enumerate(WEEKDAYS):
        group = joined[joined["weekday"] == day]
        weekday[day] = segment_summary(
            group, block_length=block_length, resamples=resamples, seed=seed + i
        )
    n = len(joined)
    quartiles = {}
    labels = ["oldest_quartile", "second_quartile", "third_quartile", "newest_quartile"]
    for i, idx in enumerate(np.array_split(np.arange(n), 4)):
        quartiles[labels[i]] = segment_summary(
            joined.iloc[idx], block_length=block_length, resamples=resamples, seed=seed + 20 + i
        )
    overall = segment_summary(joined, block_length=block_length,
                              resamples=resamples, seed=seed + 99)
    return {
        "schema": "EXACT5_V322_SEGMENT_AUDIT_V1",
        "classification": "EXPLORATORY_DIAGNOSTIC_NO_EDGE_CLAIM",
        "source_rows": int(len(history)),
        "scored_rows": n,
        "contest_min": int(joined["contest"].min()),
        "contest_max": int(joined["contest"].max()),
        "join_validation": "PASS_CONTEST_DATE_AND_WINNING_NUMBERS",
        "bootstrap": {"method": "chronological moving-block bootstrap",
                      "block_length": block_length, "resamples": resamples,
                      "seed": seed, "interval": "percentile 95%"},
        "overall": overall,
        "weekday": weekday,
        "chronological_quartiles": quartiles,
        "limitations": [
            "Segments are exploratory and not independent confirmatory tests.",
            "Weekday and period effects are descriptive; no model was retrained.",
            "A positive subgroup mean is not prospective evidence of predictive edge.",
            "The historical score export is retrospective/prequential diagnostic, not a live prospective trial."
        ]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--block-length", type=int, default=30)
    parser.add_argument("--resamples", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=20261119)
    args = parser.parse_args()
    scores = pd.read_csv(args.scores)
    history = pd.read_csv(args.history)
    report = build_report(scores, history, block_length=args.block_length,
                          resamples=args.resamples, seed=args.seed)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
