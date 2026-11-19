"""Causal adaptive mixtures over prequential expert log-likelihood ratios.

Every candidate uses only scores observed before the target being predicted.
This is an evaluation harness, not a claim of predictive edge.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp


def _validate_matrix(log_lr: np.ndarray, prior: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(log_lr, dtype=float)
    p = np.asarray(prior, dtype=float)
    if x.ndim != 2 or x.shape[0] < 1 or x.shape[1] < 1:
        raise ValueError("log_lr must be a non-empty 2D matrix")
    if p.shape != (x.shape[1],) or not np.isfinite(p).all() or np.any(p <= 0):
        raise ValueError("prior must be a finite positive vector matching experts")
    if not np.isfinite(x).all():
        raise ValueError("log_lr must contain only finite values")
    p = p / p.sum()
    return x, p


def prequential_mixture_log_lift(
    log_lr: np.ndarray, *, window: int | None = 250, temperature: float = 0.25,
    prior: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return per-target mixture log-lift and predictable weights.

    At row t, weights use rows strictly before t. With window=None all past
    rows are used. Temperature scales cumulative historical log-likelihood
    ratios; it is not fitted on future outcomes.
    """
    x = np.asarray(log_lr, dtype=float)
    if x.ndim != 2:
        raise ValueError("log_lr must be a 2D matrix")
    p0 = np.ones(x.shape[1], dtype=float) if prior is None else np.asarray(prior, dtype=float)
    x, p0 = _validate_matrix(x, p0)
    if window is not None and (not isinstance(window, int) or window < 1):
        raise ValueError("window must be a positive integer or None")
    if not np.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be finite and positive")

    log_prior = np.log(p0)
    weights = np.empty((len(x), x.shape[1]), dtype=float)
    mixed = np.empty(len(x), dtype=float)
    for t in range(len(x)):
        start = 0 if window is None else max(0, t - window)
        history_score = x[start:t].sum(axis=0)
        logw = log_prior + temperature * history_score
        logw -= logsumexp(logw)
        weights[t] = np.exp(logw)
        mixed[t] = logsumexp(logw + x[t])
    return mixed, weights


def load_expert_scores(path: str | Path) -> tuple[pd.DataFrame, list[str], np.ndarray]:
    frame = pd.read_csv(path)
    required = {"CONCURSO", "expert", "log_lift"}
    if required - set(frame.columns):
        raise ValueError(f"expert score file missing columns: {sorted(required - set(frame.columns))}")
    if frame.duplicated(["CONCURSO", "expert"]).any():
        raise ValueError("duplicate contest/expert rows")
    frame["log_lift"] = pd.to_numeric(frame["log_lift"], errors="raise")
    if not np.isfinite(frame["log_lift"].to_numpy(float)).all():
        raise ValueError("non-finite expert log-lift")
    pivot = frame.pivot(index="CONCURSO", columns="expert", values="log_lift").sort_index()
    if pivot.isna().any().any():
        raise ValueError("expert score matrix is incomplete")
    return frame, [str(c) for c in pivot.columns], pivot.to_numpy(float)


def moving_block_ci(values: np.ndarray, *, block_length: int = 30,
                    resamples: int = 3000, seed: int = 20261119) -> dict:
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < block_length or block_length < 1 or resamples < 1:
        raise ValueError("invalid bootstrap dimensions")
    blocks = np.asarray([x[i:i + block_length] for i in range(len(x) - block_length + 1)])
    rng = np.random.default_rng(seed)
    nblocks = int(np.ceil(len(x) / block_length))
    sampled = rng.integers(0, len(blocks), size=(resamples, nblocks))
    means = blocks[sampled].sum(axis=(1, 2)) / (nblocks * block_length)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"ci95_low": float(lo), "ci95_high": float(hi),
            "bootstrap_fraction_nonnegative": float(np.mean(means >= 0))}


def evaluate_grid(log_lr: np.ndarray, *, windows=(100, 250, 500),
                  temperatures=(0.25, 0.5, 1.0), resamples=3000,
                  seed=20261119) -> dict:
    x = np.asarray(log_lr, dtype=float)
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("log_lr must be a finite 2D matrix")
    results = {}
    candidates = [("static_full_bayes", None, 1.0)]
    candidates.extend(
        (f"rolling_w{w}_eta{eta:g}", w, eta)
        for w in windows for eta in temperatures
    )
    for i, (name, window, eta) in enumerate(candidates):
        ll, weights = prequential_mixture_log_lift(
            x, window=window, temperature=eta
        )
        summary = {
            "n": int(len(ll)),
            "mean_log_lift": float(ll.mean()),
            "median_log_lift": float(np.median(ll)),
            "positive_fraction": float(np.mean(ll > 0)),
            "cumulative_log_lift": float(ll.sum()),
            "final_weight_max": float(weights[-1].max()),
            "final_weight_entropy": float(-(weights[-1] * np.log(weights[-1])).sum()),
        }
        if len(ll) >= 30:
            summary.update(moving_block_ci(ll, resamples=resamples, seed=seed + i))
        quartiles = {}
        labels = ("oldest_quartile", "second_quartile", "third_quartile", "newest_quartile")
        for q, idx in enumerate(np.array_split(np.arange(len(ll)), 4)):
            part = ll[idx]
            quartiles[labels[q]] = {
                "n": int(len(part)),
                "mean_log_lift": float(part.mean()),
                "positive_fraction": float(np.mean(part > 0)),
                "cumulative_log_lift": float(part.sum()),
            }
        summary["chronological_quartiles"] = quartiles
        results[name] = summary
    return {
        "schema": "EXACT5_V323_ADAPTIVE_MIXTURE_GRID_V1",
        "classification": "PREDECLARED_RESEARCH_COMPARISON_NO_PROMOTION",
        "targets": int(len(x)),
        "experts": int(x.shape[1]),
        "grid": {"windows": list(windows), "temperatures": list(temperatures)},
        "candidates": results,
        "decision_rule": "No candidate is selected or promoted from this report; require a separate untouched prospective holdout.",
        "limitations": [
            "All candidates are diagnostic until evaluated on a genuinely prospective holdout.",
            "Grid comparisons are multiple and exploratory; intervals are not multiplicity-adjusted.",
            "The uniform expert, if present, is a safeguard but does not itself prove calibration."
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scores", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--resamples", type=int, default=3000)
    args = parser.parse_args()
    _, experts, matrix = load_expert_scores(args.scores)
    report = evaluate_grid(matrix, resamples=args.resamples)
    report["expert_names"] = experts
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
