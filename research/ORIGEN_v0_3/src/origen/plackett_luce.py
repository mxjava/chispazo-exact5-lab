"""Exact unordered-set likelihood for sequential weighted sampling without replacement.

The kernel is deliberately separate from fitting/calibration. A signed beta must
be obtained and frozen from an independent physical calibration before use.
"""
from __future__ import annotations

import math
from functools import lru_cache
from itertools import combinations
from typing import Iterable, Sequence

N_SPHERES = 28
DRAW_SIZE = 5


def _logsumexp(values: Iterable[float]) -> float:
    items = tuple(values)
    if not items:
        return float("-inf")
    peak = max(items)
    if not math.isfinite(peak):
        return peak
    return peak + math.log(math.fsum(math.exp(value - peak) for value in items))


def mass_log_weights(masses_g: Sequence[float], beta_per_sd: float) -> tuple[float, ...]:
    """Return log weights exp(beta*z_mass), with z based on all 28 spheres."""
    if len(masses_g) != N_SPHERES:
        raise ValueError("exactly 28 masses are required in printed-number order")
    if any(isinstance(value, bool) for value in masses_g):
        raise ValueError("all masses must be finite and positive numeric values")
    try:
        values = tuple(float(value) for value in masses_g)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("all masses must be finite and positive numeric values") from exc
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("all masses must be finite and positive numeric values")
    if isinstance(beta_per_sd, bool):
        raise ValueError("beta_per_sd must be a finite numeric value")
    try:
        beta = float(beta_per_sd)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("beta_per_sd must be a finite numeric value") from exc
    if not math.isfinite(beta):
        raise ValueError("beta_per_sd must be finite")
    # Center relative to the minimum and scale deviations before squaring.
    # This avoids overflow for finite but widely separated positive inputs.
    minimum = min(values)
    offsets = tuple(value - minimum for value in values)
    mean_offset = math.fsum(offsets) / N_SPHERES
    deviations = tuple(offset - mean_offset for offset in offsets)
    scale = max(abs(value) for value in deviations)
    if scale == 0:
        return (0.0,) * N_SPHERES
    scaled = tuple(value / scale for value in deviations)
    scaled_sd = math.sqrt(math.fsum(value * value for value in scaled) / N_SPHERES)
    standardized = tuple(value / scaled_sd for value in scaled)
    weighted = tuple(beta * value for value in standardized)
    if any(not math.isfinite(value) for value in weighted):
        raise ValueError("beta_per_sd and standardized masses produce non-finite log weights")
    return weighted


def log_plackett_luce_set_probability(
    log_weights: Sequence[float],
    printed_numbers: Sequence[int],
    draw_size: int = DRAW_SIZE,
) -> float:
    """Log probability of an unordered set under sequential Plackett-Luce draws."""
    try:
        raw_logs = tuple(log_weights)
        if any(isinstance(value, bool) for value in raw_logs):
            raise ValueError("log_weights must contain 28 finite numeric values")
        logs = tuple(float(value) for value in raw_logs)
    except (TypeError, OverflowError) as exc:
        raise ValueError("log_weights must contain 28 finite numeric values") from exc
    except ValueError as exc:
        if "log_weights" in str(exc):
            raise
        raise ValueError("log_weights must contain 28 finite numeric values") from exc
    if len(logs) != N_SPHERES or any(not math.isfinite(value) for value in logs):
        raise ValueError("log_weights must contain 28 finite values")
    if not isinstance(draw_size, int) or isinstance(draw_size, bool) or not 1 <= draw_size <= N_SPHERES:
        raise ValueError("draw_size must be an integer from 1 to 28")
    try:
        numbers = tuple(printed_numbers)
    except TypeError as exc:
        raise ValueError("printed_numbers must be a sequence") from exc
    if len(numbers) != draw_size:
        raise ValueError(f"exactly {draw_size} distinct printed numbers are required")
    if any(not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= N_SPHERES for number in numbers):
        raise ValueError("printed numbers must be integers from 1 to 28")
    if len(set(numbers)) != draw_size:
        raise ValueError("printed numbers must be distinct")
    selected = tuple(sorted(number - 1 for number in numbers))
    total = tuple(range(N_SPHERES))

    @lru_cache(maxsize=None)
    def prefix_set_log_probability(prefix: tuple[int, ...]) -> float:
        if not prefix:
            return 0.0
        terms = []
        prefix_set = set(prefix)
        for last in prefix:
            previous = tuple(value for value in prefix if value != last)
            remaining_log_total = _logsumexp(logs[index] for index in total if index not in previous)
            terms.append(prefix_set_log_probability(previous) + logs[last] - remaining_log_total)
        return _logsumexp(terms)

    return prefix_set_log_probability(selected)


def log_uniform_set_probability(draw_size: int = DRAW_SIZE) -> float:
    if not isinstance(draw_size, int) or isinstance(draw_size, bool) or not 1 <= draw_size <= N_SPHERES:
        raise ValueError("draw_size must be an integer from 1 to 28")
    return -math.log(math.comb(N_SPHERES, draw_size))


def log_likelihood_ratio(
    log_weights: Sequence[float],
    printed_numbers: Sequence[int],
    draw_size: int = DRAW_SIZE,
) -> float:
    """Per-contest log(q_model / q_uniform); valid only for frozen pre-close inputs."""
    return (
        log_plackett_luce_set_probability(log_weights, printed_numbers, draw_size)
        - log_uniform_set_probability(draw_size)
    )


def enumerate_set_log_probabilities(
    log_weights: Sequence[float], draw_size: int = DRAW_SIZE
) -> dict[tuple[int, ...], float]:
    """Enumerate all unordered draw sets; useful for normalization/oracle audits."""
    logs = tuple(float(value) for value in log_weights)
    if len(logs) != N_SPHERES or any(not math.isfinite(value) for value in logs):
        raise ValueError("log_weights must contain 28 finite values")
    if not isinstance(draw_size, int) or isinstance(draw_size, bool) or not 1 <= draw_size <= N_SPHERES:
        raise ValueError("draw_size must be an integer from 1 to 28")
    dp: dict[tuple[int, ...], float] = {(): 0.0}
    for size in range(1, draw_size + 1):
        for subset in combinations(range(N_SPHERES), size):
            subset_set = set(subset)
            terms = []
            for last in subset:
                previous = tuple(value for value in subset if value != last)
                denominator = _logsumexp(logs[index] for index in range(N_SPHERES) if index not in previous)
                terms.append(dp[previous] + logs[last] - denominator)
            dp[subset] = _logsumexp(terms)
    return {
        tuple(index + 1 for index in subset): probability
        for subset, probability in dp.items() if len(subset) == draw_size
    }


def prequential_e_process(log_likelihood_ratios: Sequence[float]) -> dict[str, object]:
    """Accumulate log(q_model/q_uniform) and Ville's anytime-valid p-value.

    Inputs must be generated in chronological order from features frozen before
    each corresponding draw close. This function does not verify that provenance.
    """
    cumulative = 0.0
    log_e_values: list[float] = []
    for index, value in enumerate(log_likelihood_ratios, start=1):
        increment = float(value)
        if not math.isfinite(increment):
            raise ValueError(f"log likelihood ratio {index} must be finite")
        cumulative += increment
        if not math.isfinite(cumulative):
            raise ValueError("cumulative log e-value overflowed")
        log_e_values.append(cumulative)
    maximum = max([0.0, *log_e_values])
    anytime_p = math.exp(-maximum) if maximum < 746 else 0.0
    return {
        "n_observations": len(log_e_values),
        "log_e_values": log_e_values,
        "final_log_e_value": cumulative,
        "maximum_log_e_value": maximum,
        "anytime_p_value": min(1.0, anytime_p),
        "threshold_20_crossed": maximum >= math.log(20.0),
    }
