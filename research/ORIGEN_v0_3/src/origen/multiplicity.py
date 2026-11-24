"""Multiplicity correction utilities. Pure standard-library implementation."""
from __future__ import annotations


def holm_bonferroni(p_values: dict[str, float], alpha: float = 0.05) -> dict:
    """Apply Holm-Bonferroni to exact built-in numeric probabilities.

    Booleans are deliberately rejected even though bool subclasses int in Python:
    accepting False as a p-value silently turns a type error into p=0.
    """
    if type(p_values) is not dict:
        raise ValueError("p_values_must_be_exact_dict")
    if type(alpha) not in (int, float) or not 0 < alpha < 1:
        raise ValueError("alpha_must_be_between_0_and_1")
    if not p_values:
        raise ValueError("empty_hypothesis_family")
    for key, p in p_values.items():
        if (
            type(key) is not str
            or not key
            or type(p) not in (int, float)
            or not 0 <= p <= 1
        ):
            raise ValueError(f"invalid_p_value:{key}")
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    family_size = len(ordered)
    adjusted = {}
    running_max = 0.0
    for rank, (name, p_value) in enumerate(ordered):
        value = min(1.0, (family_size - rank) * p_value)
        running_max = max(running_max, value)
        adjusted[name] = running_max
    return {
        "method": "Holm-Bonferroni",
        "family_size": family_size,
        "alpha": alpha,
        "results": {
            name: {
                "p_raw": p_values[name],
                "p_adjusted": adjusted[name],
                "reject": adjusted[name] < alpha,
            }
            for name in p_values
        },
    }
