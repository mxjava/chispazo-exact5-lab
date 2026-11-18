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

def _binomial_upper_tail(n: int, k: int) -> float:
    if n==0: return 1.0
    return sum(__import__("math").comb(n,i) for i in range(k,n+1))/(2**n)

def evaluate_log_scores(observations: Iterable[dict], *, protocol_status: str,
                        family_p_values: dict[str,float], primary_test_id: str,
                        gates: dict, min_observations: int=100, alpha: float=0.05) -> dict:
    """Evaluate log scores; never self-certify EDGE_SUPPORTED."""
    rows=list(observations)
    if not rows: raise ValueError("no_observations")
    if min_observations<1: raise ValueError("min_observations_must_be_positive")
    if primary_test_id not in family_p_values: raise ValueError("primary_test_missing_from_full_hypothesis_family")
    lifts=[]
    for i,row in enumerate(rows):
        try: pa,pn=float(row["p_alt"]),float(row["p_null"])
        except (KeyError,TypeError,ValueError) as exc: raise ValueError(f"invalid_probability_at_row_{i}") from exc
        if not (isfinite(pa) and isfinite(pn) and 0<pa<=1 and 0<pn<=1): raise ValueError(f"probabilities_must_be_finite_and_in_(0,1]_at_row_{i}")
        lifts.append(log(pa)-log(pn))
    n=len(lifts); positive=sum(x>0 for x in lifts); negative=sum(x<0 for x in lifts); nonzero=positive+negative
    sign_p=_binomial_upper_tail(nonzero,positive) if nonzero else 1.0
    mean_lift=sum(lifts)/n; ordered=sorted(lifts)
    median_lift=ordered[n//2] if n%2 else (ordered[n//2-1]+ordered[n//2])/2
    if "__origen_sign_test__" in family_p_values: raise ValueError("reserved_test_id_in_hypothesis_family")
    complete_family=dict(family_p_values); complete_family["__origen_sign_test__"]=sign_p
    adjusted=holm_bonferroni(complete_family,alpha); primary=adjusted["results"][primary_test_id]; sign_adjusted=adjusted["results"]["__origen_sign_test__"]
    required={"preregistered","untouched_prospective","independent_custody","data_integrity_pass","two_prospective_outputs"}
    missing_gates=sorted(required-set(gates)); failed_gates=sorted(k for k in required if gates.get(k) is not True)
    statistical_candidate=(n>=min_observations and mean_lift>0 and primary["reject"] and sign_adjusted["reject"]
                           and not missing_gates and not failed_gates and protocol_status=="PREREGISTERED")
    if not gates.get("independent_custody",False) or not gates.get("data_integrity_pass",False):
        state="BLOCKED_PROVENANCE"
    elif statistical_candidate:
        state="STATISTICAL_SIGNAL_REQUIRES_EXTERNAL_AUDIT"
    else:
        state="NO_EDGE_EVIDENCE"
    return {"state":state,"edge_certified":False,"promotion_authorized":False,"n":n,
            "min_observations":min_observations,"mean_log_lift":mean_lift,"median_log_lift":median_lift,
            "positive_log_lift_rate":positive/n,"positive_count":positive,"negative_count":negative,"ties":n-nonzero,
            "sign_test_one_sided_p":sign_p,"primary_holm":primary,"sign_test_holm":sign_adjusted,"multiplicity":adjusted,
            "gates_missing":missing_gates,"gates_failed":failed_gates,"protocol_status":protocol_status,
            "interpretation":"This evaluator can identify a statistical candidate only. EDGE_SUPPORTED requires a separate independent audit of raw prospective outputs, protocol chronology, custody, and source provenance; caller-supplied booleans are not proof."}
