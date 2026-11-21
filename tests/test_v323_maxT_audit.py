import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_v323_maxT.py"
SPEC = importlib.util.spec_from_file_location("audit_v323_maxT", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _scores(tmp_path, rows):
    path = tmp_path / "scores.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _valid_rows():
    rng = np.random.default_rng(41)
    rows = []
    for contest in range(1, 46):
        for expert in ("uniform", "expert_a", "expert_b"):
            rows.append({
                "CONCURSO": contest,
                "expert": expert,
                "log_lift": float(rng.normal(0, 0.05)),
            })
    return rows


def test_audit_is_reproducible_and_reports_complete_candidate_family(tmp_path):
    path = _scores(tmp_path, _valid_rows())
    first = MODULE.audit(str(path), resamples=40, seed=123)
    second = MODULE.audit(str(path), resamples=40, seed=123)

    assert first == second
    assert first["n_targets"] == 45
    assert first["n_experts"] == 3
    assert len(first["results"]) == 10
    assert all(np.isfinite(row["mean_log_lift"]) for row in first["results"])
    assert all(0 <= row["maxT_one_sided_p_adjusted"] <= 1 for row in first["results"])


def test_audit_rejects_missing_required_columns(tmp_path):
    path = _scores(tmp_path, [{"CONCURSO": 1, "expert": "u"}])
    with pytest.raises(ValueError, match="missing columns"):
        MODULE.audit(str(path), resamples=10)


def test_audit_rejects_duplicate_contest_expert_rows(tmp_path):
    rows = _valid_rows()
    rows.append(rows[0].copy())
    path = _scores(tmp_path, rows)
    with pytest.raises(ValueError, match="duplicate contest/expert"):
        MODULE.audit(str(path), resamples=10)


def test_audit_rejects_incomplete_expert_matrix(tmp_path):
    rows = _valid_rows()
    rows.pop()
    path = _scores(tmp_path, rows)
    with pytest.raises(ValueError, match="incomplete expert matrix"):
        MODULE.audit(str(path), resamples=10)


def test_audit_rejects_non_finite_scores(tmp_path):
    rows = _valid_rows()
    rows[0]["log_lift"] = float("nan")
    path = _scores(tmp_path, rows)
    with pytest.raises(ValueError, match="non-finite"):
        MODULE.audit(str(path), resamples=10)
