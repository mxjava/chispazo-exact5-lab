"""Empirical comparison against matched adversarial-null statistics."""
from __future__ import annotations
from math import isfinite

def benchmark_nulls(observed_statistic: float, null_statistics: dict[str, list[float]], direction: str = "greater") -> dict:
    if direction not in {"greater", "less", "two-sided"}: raise ValueError("invalid_direction")
    if not isfinite(float(observed_statistic)) or not null_statistics: raise ValueError("invalid_observed_statistic_or_empty_null_suite")
    results = {}
    for name, values in null_statistics.items():
        vals = [float(x) for x in values]
        if not vals or any(not isfinite(x) for x in vals): raise ValueError(f"invalid_null_distribution:{name}")
        if direction == "greater": extreme = sum(x >= observed_statistic for x in vals)
        elif direction == "less": extreme = sum(x <= observed_statistic for x in vals)
        else:
            center = sum(vals) / len(vals)
            extreme = sum(abs(x - center) >= abs(observed_statistic - center) for x in vals)
        p = (extreme + 1) / (len(vals) + 1)
        results[name] = {"replicates": len(vals), "extreme_count": extreme, "empirical_p": p,
                         "null_mean": sum(vals) / len(vals), "null_min": min(vals), "null_max": max(vals)}
    return {"observed_statistic": float(observed_statistic), "direction": direction, "nulls": results,
            "worst_case_empirical_p": max(x["empirical_p"] for x in results.values()),
            "interpretation": "A matched null reproducing the observed statistic weakens the claim; null families must include the full search process."}
