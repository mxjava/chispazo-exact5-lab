import numpy as np
import pandas as pd
import pytest

from src.v323.adaptive_expert_mixture import (
    evaluate_grid, load_expert_scores, prequential_mixture_log_lift,
)


def test_uniform_expert_only_has_zero_log_lift():
    x = np.zeros((50, 3))
    ll, weights = prequential_mixture_log_lift(x, window=10, temperature=0.5)
    assert np.allclose(ll, 0.0)
    assert np.allclose(weights.sum(axis=1), 1.0)


def test_weights_at_target_do_not_use_target_or_future():
    x = np.array([
        [0.0, 0.2, -0.2],
        [0.0, -0.1, 0.1],
        [0.0, 0.3, -0.3],
        [0.0, -0.2, 0.2],
    ])
    _, w1 = prequential_mixture_log_lift(x, window=2, temperature=0.5)
    changed = x.copy()
    changed[2:] = 999.0
    _, w2 = prequential_mixture_log_lift(changed, window=2, temperature=0.5)
    assert np.allclose(w1[:2], w2[:2])


def test_rolling_window_forgets_old_scores_but_static_bayes_does_not():
    x = np.zeros((8, 2))
    x[0] = [0.0, -20.0]
    _, rolling = prequential_mixture_log_lift(x, window=2, temperature=1.0)
    _, static = prequential_mixture_log_lift(x, window=None, temperature=1.0)
    assert rolling[-1, 1] > static[-1, 1]


def test_weights_are_normalized_and_finite_for_grid():
    x = np.random.default_rng(7).normal(0, 0.1, size=(80, 4))
    _, weights = prequential_mixture_log_lift(x, window=20, temperature=0.25)
    assert np.isfinite(weights).all()
    assert np.allclose(weights.sum(axis=1), 1.0)
    report = evaluate_grid(x, windows=(10,), temperatures=(0.25, 1.0), resamples=100)
    assert report["classification"] == "PREDECLARED_RESEARCH_COMPARISON_NO_PROMOTION"
    assert len(report["candidates"]) == 3


def test_expert_score_loader_rejects_incomplete_matrix(tmp_path):
    path = tmp_path / "scores.csv"
    pd.DataFrame([
        {"CONCURSO": 1, "expert": "uniform", "log_lift": 0.0},
        {"CONCURSO": 1, "expert": "A", "log_lift": 0.1},
        {"CONCURSO": 2, "expert": "uniform", "log_lift": 0.0},
    ]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="incomplete"):
        load_expert_scores(path)
