"""Research-only score test for preregistered physical ball covariates.

This module tests association under an independent uniform 5-of-28 null. It does
not authenticate source records, identify physical balls, or generate predictions.
All observed evidence must pass a separate provenance gate before use.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math
from typing import Mapping, Sequence

import numpy as np

N_NUMBERS = 28
PICKS_PER_DRAW = 5
OUTCOME_COUNT = math.comb(N_NUMBERS, PICKS_PER_DRAW)
REQUIRED_FEATURES = (
    "diameter_mm",
    "mass_g",
    "sphericity_index",
    "surface_roughness_um",
)
NULL_MODEL = "INDEPENDENT_UNIFORM_5_OF_28_PER_CLASSIC_DRAW"


@dataclass(frozen=True, slots=True)
class CovariateScore:
    feature: str
    z_score: float
    monte_carlo_p: float
    holm_adjusted_p: float


@dataclass(frozen=True, slots=True)
class PhysicalCovariateFamilyResult:
    modality: str
    scheduled_time_local: str
    null_model: str
    draw_count: int
    epoch_count: int
    simulations: int
    seed: int
    family_max_statistic: float
    familywise_monte_carlo_p: float
    feature_scores: tuple[CovariateScore, ...]


def _require_text(value: object, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _validated_epoch(epoch: Mapping[str, object], index: int):
    if not isinstance(epoch, Mapping):
        raise TypeError(f"epochs[{index}] must be a mapping")
    epoch_id = _require_text(epoch.get("epoch_id"), f"epochs[{index}].epoch_id")
    _require_text(epoch.get("machine_id"), f"epochs[{index}].machine_id")
    _require_text(epoch.get("ball_set_id"), f"epochs[{index}].ball_set_id")

    features = epoch.get("features_by_number")
    if not isinstance(features, Mapping) or set(features) != set(REQUIRED_FEATURES):
        raise ValueError(
            f"epochs[{index}].features_by_number must contain exactly "
            f"{', '.join(REQUIRED_FEATURES)}"
        )
    columns = []
    for name in REQUIRED_FEATURES:
        values = np.asarray(features[name], dtype=np.float64)
        if values.shape != (N_NUMBERS,) or not np.isfinite(values).all():
            raise ValueError(f"{name} must contain exactly 28 finite measurements")
        columns.append(values)
    matrix = np.column_stack(columns)
    if any(float(np.ptp(matrix[:, j])) == 0.0 for j in range(matrix.shape[1])):
        raise ValueError("each preregistered physical feature must vary within an epoch")

    draws = epoch.get("draws")
    contest_ids = epoch.get("contest_ids")
    if not isinstance(draws, Sequence) or isinstance(draws, (str, bytes)):
        raise TypeError(f"epochs[{index}].draws must be a sequence")
    if not isinstance(contest_ids, Sequence) or isinstance(contest_ids, (str, bytes)):
        raise TypeError(f"epochs[{index}].contest_ids must be a sequence")
    if len(draws) == 0 or len(draws) != len(contest_ids):
        raise ValueError("each epoch requires one contest_id per draw")

    ids = []
    draw_indices = []
    for row_index, row in enumerate(draws):
        contest_id = contest_ids[row_index]
        if type(contest_id) is not int or contest_id <= 0:
            raise ValueError("contest_ids must be positive integers")
        ids.append(contest_id)
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)) or len(row) != PICKS_PER_DRAW:
            raise ValueError("every draw must contain exactly five numbers")
        if any(type(number) is not int or not 1 <= number <= N_NUMBERS for number in row):
            raise ValueError("draw numbers must be integers from 1 through 28")
        if len(set(row)) != PICKS_PER_DRAW:
            raise ValueError("a draw cannot contain duplicate numbers")
        draw_indices.append([number - 1 for number in row])

    return epoch_id, matrix, np.asarray(draw_indices, dtype=np.int16), ids


def evaluate_physical_covariate_family(
    epochs: Sequence[Mapping[str, object]],
    *,
    modality: str,
    scheduled_time_local: str,
    simulations: int = 9_999,
    seed: int = 20261125,
    batch_size: int = 128,
) -> PhysicalCovariateFamilyResult:
    """Evaluate four preregistered physical features against uniform 5-of-28.

    Each epoch represents one unchanged machine + ball-set + number mapping +
    measurement snapshot. If any of these changes, a new epoch is mandatory.
    The function requires >=100 Classic draws in total. It cannot verify that
    records are prospective, official, signed, pre-close, or independently held.

    The null is calibrated by sampling from all C(28,5)=98,280 outcomes for
    every draw and epoch. The primary family statistic is the maximum absolute
    standardized score across the four features. Raw Monte Carlo p-values are
    also Holm-adjusted. This is an association test, not a forecast.
    """
    if modality != "CLASSIC" or scheduled_time_local != "21:00":
        raise ValueError("this preregistration accepts CLASSIC at 21:00 only")
    if type(simulations) is not int or simulations < 999:
        raise ValueError("simulations must be an integer >= 999")
    if type(seed) is not int or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if type(batch_size) is not int or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    if not isinstance(epochs, Sequence) or isinstance(epochs, (str, bytes)) or not epochs:
        raise ValueError("at least one physical epoch is required")

    validated = []
    seen_epoch_ids = set()
    seen_contests = set()
    total_draws = 0
    for index, epoch in enumerate(epochs):
        epoch_id, matrix, draw_indices, contest_ids = _validated_epoch(epoch, index)
        if epoch_id in seen_epoch_ids:
            raise ValueError("epoch_id values must be unique")
        seen_epoch_ids.add(epoch_id)
        for contest_id in contest_ids:
            if contest_id in seen_contests:
                raise ValueError("contest_ids must be unique across all epochs")
            seen_contests.add(contest_id)
        total_draws += len(draw_indices)
        validated.append((matrix, draw_indices))

    if total_draws < 100:
        raise ValueError("at least 100 untouched Classic draws are required")

    outcomes = np.asarray(
        list(combinations(range(N_NUMBERS), PICKS_PER_DRAW)), dtype=np.int16
    )
    if outcomes.shape != (OUTCOME_COUNT, PICKS_PER_DRAW):
        raise RuntimeError("internal 5-of-28 outcome-space construction failed")

    epoch_score_spaces = []
    observed = np.zeros(len(REQUIRED_FEATURES), dtype=np.float64)
    null_variance = np.zeros(len(REQUIRED_FEATURES), dtype=np.float64)
    for matrix, draw_indices in validated:
        centered = matrix - matrix.mean(axis=0, keepdims=True)
        outcome_scores = centered[outcomes].sum(axis=1, dtype=np.float64)
        outcome_scores -= outcome_scores.mean(axis=0, keepdims=True)
        observed += centered[draw_indices].sum(axis=(0, 1), dtype=np.float64)
        null_variance += len(draw_indices) * np.mean(
            outcome_scores * outcome_scores, axis=0
        )
        epoch_score_spaces.append((outcome_scores, len(draw_indices)))

    if np.any(null_variance <= 0.0) or not np.isfinite(null_variance).all():
        raise ValueError("physical feature family has a degenerate null variance")
    null_sd = np.sqrt(null_variance)
    observed_z = observed / null_sd

    rng = np.random.Generator(np.random.PCG64(seed))
    raw_extreme = np.zeros(len(REQUIRED_FEATURES), dtype=np.int64)
    family_extreme = 0
    completed = 0
    while completed < simulations:
        size = min(batch_size, simulations - completed)
        simulated_total = np.zeros((size, len(REQUIRED_FEATURES)), dtype=np.float64)
        for score_space, draws_in_epoch in epoch_score_spaces:
            selected = rng.integers(
                0, OUTCOME_COUNT, size=(size, draws_in_epoch), endpoint=False
            )
            simulated_total += score_space[selected].sum(axis=1, dtype=np.float64)
        simulated_z = simulated_total / null_sd
        absolute = np.abs(simulated_z)
        raw_extreme += np.sum(
            absolute >= np.abs(observed_z)[None, :], axis=0
        )
        maxima = absolute.max(axis=1)
        family_extreme += int(np.sum(maxima >= float(np.max(np.abs(observed_z)))))
        completed += size

    raw_p = (raw_extreme + 1) / (simulations + 1)
    order = np.argsort(raw_p, kind="stable")
    adjusted = np.empty_like(raw_p)
    running = 0.0
    feature_count = len(REQUIRED_FEATURES)
    for rank, feature_index in enumerate(order):
        candidate = min(1.0, (feature_count - rank) * float(raw_p[feature_index]))
        running = max(running, candidate)
        adjusted[feature_index] = running

    family_p = (family_extreme + 1) / (simulations + 1)
    scores = tuple(
        CovariateScore(
            feature=name,
            z_score=float(observed_z[index]),
            monte_carlo_p=float(raw_p[index]),
            holm_adjusted_p=float(adjusted[index]),
        )
        for index, name in enumerate(REQUIRED_FEATURES)
    )
    return PhysicalCovariateFamilyResult(
        modality=modality,
        scheduled_time_local=scheduled_time_local,
        null_model=NULL_MODEL,
        draw_count=total_draws,
        epoch_count=len(validated),
        simulations=simulations,
        seed=seed,
        family_max_statistic=float(np.max(np.abs(observed_z))),
        familywise_monte_carlo_p=float(family_p),
        feature_scores=scores,
    )
