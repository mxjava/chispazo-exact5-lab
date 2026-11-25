"""Multiplicity correction utilities. Pure standard-library implementation."""
from __future__ import annotations
from math import isfinite

def holm_bonferroni(p_values: dict[str, float], alpha: float = 0.05) -> dict:
    if not 0 < alpha < 1: raise ValueError("alpha_must_be_between_0_and_1")
    if not p_values: raise ValueError("empty_hypothesis_family")
    for key,p in p_values.items():
        if not key or not isinstance(p,(int,float)) or not isfinite(p) or not 0 <= p <= 1: raise ValueError(f"invalid_p_value:{key}")
    ordered=sorted(p_values.items(),key=lambda item:(item[1],item[0])); m=len(ordered); adjusted={}; running_max=0.0
    for rank,(name,p) in enumerate(ordered):
        value=min(1.0,(m-rank)*p); running_max=max(running_max,value); adjusted[name]=running_max
    return {"method":"Holm-Bonferroni","family_size":m,"alpha":alpha,
            "results":{name:{"p_raw":p_values[name],"p_adjusted":adjusted[name],"reject":adjusted[name]<alpha} for name in p_values}}
