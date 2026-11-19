import numpy as np
import pandas as pd
import pytest

from src.v322.segment_audit import build_report, validate_join, block_bootstrap_mean_ci


def fixtures():
    dates = pd.date_range("2024-01-01", periods=28, freq="D")
    history = pd.DataFrame({
        "CONCURSO": np.arange(100, 128),
        "FECHA": dates.strftime("%Y-%m-%d"),
        "R1": [1] * 28, "R2": [2] * 28, "R3": [3] * 28,
        "R4": [4] * 28, "R5": [5] * 28,
    })
    scores = pd.DataFrame({
        "contest": np.arange(100, 128),
        "date": dates.strftime("%Y-%m-%d"),
        "numbers": ["01-02-03-04-05"] * 28,
        "log_lift_vs_uniform": np.linspace(-0.02, 0.01, 28),
    })
    return scores, history


def test_join_checks_contest_date_and_winning_combination():
    scores, history = fixtures()
    assert len(validate_join(scores, history)) == 28
    scores.loc[0, "numbers"] = "01-02-03-04-06"
    with pytest.raises(ValueError, match="combinations"):
        validate_join(scores, history)


def test_join_rejects_date_mismatch():
    scores, history = fixtures()
    scores.loc[0, "date"] = "2024-02-01"
    with pytest.raises(ValueError, match="dates"):
        validate_join(scores, history)


def test_report_labels_exploratory_and_has_all_weekdays():
    scores, history = fixtures()
    report = build_report(scores, history, block_length=7, resamples=100)
    assert report["classification"] == "EXPLORATORY_DIAGNOSTIC_NO_EDGE_CLAIM"
    assert report["join_validation"] == "PASS_CONTEST_DATE_AND_WINNING_NUMBERS"
    assert set(report["weekday"]) == {
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    }
    assert report["overall"]["n"] == 28


def test_block_bootstrap_is_reproducible():
    x = np.linspace(-0.1, 0.1, 100)
    a = block_bootstrap_mean_ci(x, block_length=10, resamples=100, seed=42)
    b = block_bootstrap_mean_ci(x, block_length=10, resamples=100, seed=42)
    assert a == b
