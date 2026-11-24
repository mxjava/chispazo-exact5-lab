"""Chronological, paired prequential log-score evaluation.
This module reports statistical candidates only. It cannot certify provenance,
custody, preregistration authenticity, or predictive edge.
"""
from __future__ import annotations
from math import log, isfinite
from typing import Iterable
from .multiplicity import holm_bonferroni

def chronological_split(n: int, warmup: int, evaluation_size: int | None = None) -> dict:
    if n < 0 or warmup < 0 or warmup > n: raise ValueError("invalid_split_dimensions")
    end=n if evaluation_size is None else warmup+evaluation_size
    if end>n or (evaluation_size is not None and evaluation_size<0): raise ValueError("evaluation_window_out_of_range")
    return {"warmup_indices":list(range(warmup)),"evaluation_indices":list(range(warmup,end)),
            "unused_future_indices":list(range(end,n)),"chronology_preserved":True}

def rolling_origin_folds(n: int, initial_train: int, horizon: int, step: int | None = None) -> list[dict]:
    if n<1 or initial_train<1 or horizon<1 or initial_train>=n: raise ValueError("invalid_rolling_origin_dimensions")
    step=horizon if step is None else step
    if step<1: raise ValueError("step_must_be_positive")
    folds=[]; train_end=initial_train
    while train_end<n:
        test_end=min(n,train_end+horizon)
        folds.append({"train_indices":list(range(0,train_end)),"test_indices":list(range(train_end,test_end)),
                      "train_end_exclusive":train_end,"test_end_exclusive":test_end})
        train_end+=step
    return folds

UNIFORM_EXACT5_PROBABILITY = 1.0 / 98280.0
EXACT5_LOG_E_THRESHOLD = log(20.0)


def evaluate_log_scores(
    observations: Iterable[dict],
    *,
    protocol_status: str,
    family_p_values: dict[str, float],
    primary_test_id: str,
    gates: dict,
    exact5_max_log_e_value: float | None = None,
    min_observations: int = 100,
    alpha: float = 0.05,
) -> dict:
    """Evaluate paired Exact5 log scores without a distribution-free sign test.

    Positive-log-lift frequency is descriptive only: for a normalized,
    non-uniform alternative, P_uniform(log(q(S)/p0(S)) > 0) need not equal 1/2.
    This evaluator can return a statistical candidate, never EDGE_SUPPORTED.
    """
    rows = list(observations)
    if not rows:
        raise ValueError("no_observations")
    if type(min_observations) is not int or min_observations < 1:
        raise ValueError("min_observations_must_be_positive_integer")
    if type(gates) is not dict:
        raise ValueError("gates_must_be_an_exact_dict")
    if type(family_p_values) is not dict:
        raise ValueError("family_p_values_must_be_an_exact_dict")
    if type(primary_test_id) is not str or not primary_test_id:
        raise ValueError("primary_test_id_must_be_non_empty_exact_text")
    if type(protocol_status) is not str:
        raise ValueError("protocol_status_must_be_exact_text")
    if primary_test_id not in family_p_values:
        raise ValueError("primary_test_missing_from_full_hypothesis_family")

    lifts = []
    for index, row in enumerate(rows):
        if type(row) is not dict or any(type(key) is not str for key in row):
            raise ValueError(f"observation_must_be_exact_dict_with_text_keys_at_row_{index}")
        try:
            raw_alt = row["p_alt"]
            raw_null = row["p_null"]
        except KeyError as exc:
            raise ValueError(f"invalid_probability_at_row_{index}") from exc
        # bool is a subclass of int, and float(True) == 1.0. Reject booleans,
        # numeric subclasses and text coercions before probability arithmetic.
        if type(raw_alt) not in (int, float) or not 0 < raw_alt <= 1:
            raise ValueError(f"alternative_probability_must_be_finite_and_in_(0,1]_at_row_{index}")
        if type(raw_null) not in (int, float) or not 0 < raw_null <= 1:
            raise ValueError(f"null_probability_must_be_finite_and_in_(0,1]_at_row_{index}")
        p_alt = float(raw_alt)
        p_null = float(raw_null)
        if not (isfinite(p_alt) and 0.0 < p_alt <= 1.0):
            raise ValueError(f"alternative_probability_must_be_finite_and_in_(0,1]_at_row_{index}")
        if not (isfinite(p_null) and p_null > 0.0 and p_null <= 1.0):
            raise ValueError(f"null_probability_must_be_finite_and_in_(0,1]_at_row_{index}")
        if p_null != UNIFORM_EXACT5_PROBABILITY:
            raise ValueError(f"null_probability_must_equal_exact_uniform_1_over_98280_at_row_{index}")
        lifts.append(log(p_alt) - log(UNIFORM_EXACT5_PROBABILITY))

    adjusted = holm_bonferroni(dict(family_p_values), alpha)
    primary = adjusted["results"][primary_test_id]
    n = len(lifts)
    positive = sum(value > 0.0 for value in lifts)
    negative = sum(value < 0.0 for value in lifts)
    ties = n - positive - negative
    mean_lift = sum(lifts) / n
    ordered = sorted(lifts)
    median_lift = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2.0

    required = {
        "preregistered",
        "untouched_prospective",
        "independent_custody",
        "data_integrity_pass",
        "two_prospective_outputs",
        "pmf_custody_verified",
        "complete_target_ledger",
        "official_modality_verified",
        "preclose_snapshot_verified",
    }
    missing_gates = sorted(required - set(gates))
    failed_gates = sorted(key for key in required if gates.get(key) is not True)

    e_value_valid = (
        type(exact5_max_log_e_value) in (int, float)
        and isfinite(exact5_max_log_e_value)
        and exact5_max_log_e_value >= EXACT5_LOG_E_THRESHOLD
    )
    if not e_value_valid:
        failed_gates.append("exact5_anytime_e_value_ge_20")

    statistical_candidate = (
        n >= min_observations
        and mean_lift > 0.0
        and primary["reject"]
        and not missing_gates
        and not failed_gates
        and protocol_status == "PREREGISTERED"
    )
    provenance_gates = {
        "independent_custody",
        "data_integrity_pass",
        "pmf_custody_verified",
        "complete_target_ledger",
        "official_modality_verified",
        "preclose_snapshot_verified",
    }
    provenance_blocked = any(gates.get(key) is not True for key in provenance_gates)
    if provenance_blocked:
        state = "BLOCKED_PROVENANCE"
    elif statistical_candidate:
        state = "STATISTICAL_SIGNAL_REQUIRES_EXTERNAL_AUDIT"
    else:
        state = "NO_EDGE_EVIDENCE"

    return {
        "state": state,
        "edge_certified": False,
        "promotion_authorized": False,
        "n": n,
        "min_observations": min_observations,
        "mean_log_lift": mean_lift,
        "median_log_lift": median_lift,
        "positive_log_lift_rate": positive / n,
        "positive_count": positive,
        "negative_count": negative,
        "ties": ties,
        "primary_holm": primary,
        "multiplicity": adjusted,
        "exact5_max_log_e_value": exact5_max_log_e_value,
        "exact5_log_threshold": EXACT5_LOG_E_THRESHOLD,
        "exact5_threshold_20_crossed": e_value_valid,
        "gates_missing": missing_gates,
        "gates_failed": sorted(set(failed_gates)),
        "protocol_status": protocol_status,
        "interpretation": (
            "Positive-log-lift frequency is descriptive, not a sign-test p-value. "
            "The null is fixed at exactly 1/98280. A statistical candidate still "
            "requires independent audit of sealed PMFs, the complete target ledger, "
            "pre-close chronology, modality, custody and raw outputs. This function "
            "never certifies EDGE_SUPPORTED or authorizes promotion."
        ),
    }
