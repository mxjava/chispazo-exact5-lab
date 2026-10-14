import importlib.util
import math
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"
spec = importlib.util.spec_from_file_location("v274_eval", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_one_sided_t_probability_matches_exact_df1_case():
    # [0, 2] has mean=1, sample SD=sqrt(2), t=1 with df=1; p(T_1 >= 1)=1/4.
    t_stat, p = mod.one_sided_ttest_greater([0.0, 2.0])
    assert math.isclose(t_stat, 1.0, rel_tol=1e-12)
    assert math.isclose(p, 0.25, rel_tol=1e-12)


def test_negative_mean_returns_upper_tail_probability():
    t_stat, p = mod.one_sided_ttest_greater([-2.0, 0.0])
    assert math.isclose(t_stat, -1.0, rel_tol=1e-12)
    assert math.isclose(p, 0.75, rel_tol=1e-12)


def test_nan_policy_omits_nan_values():
    t_stat, p = mod.one_sided_ttest_greater([0.0, 2.0, float("nan")])
    assert math.isclose(t_stat, 1.0, rel_tol=1e-12)
    assert math.isclose(p, 0.25, rel_tol=1e-12)


def test_zero_variance_edges_match_one_sided_test_convention():
    assert mod.one_sided_ttest_greater([1.0, 1.0])[1] == 0.0
    assert mod.one_sided_ttest_greater([-1.0, -1.0])[1] == 1.0
    assert math.isnan(mod.one_sided_ttest_greater([0.0, 0.0])[1])


def test_nonfinite_infinite_sample_fails_to_nan_instead_of_false_edge():
    t_stat, p = mod.one_sided_ttest_greater([0.0, float("inf")])
    assert math.isnan(t_stat)
    assert math.isnan(p)
