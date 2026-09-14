#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
CHISPAZO V262 — CALIBRATED EXACT-MASS DRO
==========================================

V262 changes the optimization target from an arbitrary affine parent-score
quality to a normalized probability distribution over the 98,280 exact 5-number
outcomes.

Core ideas
----------
1) Causal calibration is learned only from previously resolved V261 snapshots.
   For every resolved target, V262 records the exact rank of the winning line.
2) Winner-rank calibration uses disjoint rank buckets with a Dirichlet prior
   proportional to the exact uniform null. This produces a probability mass
   function that sums to 1 over all 98,280 combinations.
3) Model uncertainty is represented by several calibration scenarios spanning
   prior strengths and temporal half-lives (plus a same-parity regime when enough
   evidence exists). Stage 1 maximizes the worst-case exact probability mass of
   the 30 selected lines across those scenarios: a small distributionally robust
   optimization (DRO) MILP.
4) Stage 2 can improve number/pair/triple assembly only if every calibration
   scenario retains at least (1-regret_budget) of Stage-1 exact mass.

This does NOT make lottery draws predictable or guarantee 5/5. Under no validated
ranking edge, the calibrated posterior contracts toward the exact uniform null:
P(line)=1/98,280 and P(any of 30 distinct lines)=30/98,280 ~= 0.030525%.
"""

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import os
import sys
import time
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix
from scipy.stats import t as student_t

V262_SCHEMA = 262
V262_ENGINE = "CHISPAZO_V262_EXACT_MASS_DRO"
UNIVERSE_SIZE = math.comb(28, 5)
UNIFORM_LINE_PROB = 1.0 / UNIVERSE_SIZE
PAIR_COUNT = math.comb(28, 2)
TRIPLE_COUNT = math.comb(28, 3)


@dataclass(frozen=True)
class V262Config:
    history: str = r"D:\melate\Chispazo.csv"
    v249_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py"
    v259_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V259_CALIBRATED_ANTICOLLAPSE.py"
    v260_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V260_ASSEMBLY_RESCUE.py"
    v261_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V261_LEXICOGRAPHIC_REGRET.py"
    v261_config_path: str = r"D:\melate\melate_new\chispazo_v261.toml"
    v261_state_dir: str = r"D:\melate\state_v261"
    v262_state_dir: str = r"D:\melate\state_v262"
    out_dir: str = r"D:\melate\resultados_v262_{target}"
    prospective_registry_dir: str = r"D:\melate\preregistros_v262"

    target: Optional[int] = None
    expected_last: Optional[int] = None
    lines: int = 30
    quiet: bool = False

    # Disjoint exact-rank calibration buckets. Last edge must be 98,280.
    rank_bucket_edges: str = "1,3,5,10,20,30,50,100,200,500,1000,2500,5000,10000,25000,50000,98280"
    evidence_lookback: int = 1200
    same_parity_min_oos: int = 40
    prior_strengths: str = "150,300,600"
    half_lives: str = "90,180,360"
    edge_min_prequential: int = 30
    edge_mature_prequential: int = 120
    edge_alpha: float = 0.10

    # Candidate construction uses the union of the parent head and every
    # calibration scenario head, then grows if the MILP cannot meet caps.
    candidate_pool_rank: int = 500
    candidate_pool_max_rank: int = 5000
    candidate_pool_growth: float = 2.0

    # Structural model-risk caps; relaxed only on a deterministic frontier.
    strict_max_number_exposure: int = 9
    strict_max_pair_exposure: int = 4
    strict_max_triple_exposure: int = 2

    # Secondary structural assembly is allowed to spend at most this fraction of
    # Stage-1 robust exact probability mass in every calibration scenario.
    stage2_probability_regret_budget: float = 0.0025
    second_number_coverage_discount: float = 0.40
    number_coverage_mass: float = 0.28
    pair_coverage_mass: float = 0.42
    triple_coverage_mass: float = 0.30
    stage2_top_pairs: int = 190
    stage2_top_triples: int = 300

    milp_time_limit_seconds: float = 45.0
    milp_mip_rel_gap: float = 0.0
    top_ranking_rows: int = 5000
    prospective_register: bool = True


def _flatten_toml(d: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    def walk(x: Mapping[str, Any]) -> None:
        for k, v in x.items():
            kk = str(k).replace('-', '_')
            if isinstance(v, dict):
                walk(v)
            else:
                out[kk] = v
    walk(d)
    return out


def load_config(path: Optional[Path]) -> V262Config:
    base = asdict(V262Config())
    if path is not None:
        with Path(path).open('rb') as fh:
            vals = _flatten_toml(tomllib.load(fh))
        bad = sorted(set(vals) - set(base))
        if bad:
            raise ValueError(f"Config V262 contiene claves desconocidas: {bad}")
        base.update(vals)
    cfg = V262Config(**base)
    validate_config(cfg)
    return cfg


def _parse_ints(s: str) -> Tuple[int, ...]:
    return tuple(int(x.strip()) for x in str(s).split(',') if x.strip())


def _parse_floats(s: str) -> Tuple[float, ...]:
    return tuple(float(x.strip()) for x in str(s).split(',') if x.strip())


def rank_bucket_edges(cfg: V262Config) -> np.ndarray:
    x = np.asarray(_parse_ints(cfg.rank_bucket_edges), dtype=np.int32)
    if len(x) < 2 or np.any(np.diff(x) <= 0) or int(x[-1]) != UNIVERSE_SIZE or int(x[0]) < 1:
        raise ValueError('rank_bucket_edges invalidos')
    return x


def validate_config(cfg: V262Config) -> None:
    rank_bucket_edges(cfg)
    ps = _parse_floats(cfg.prior_strengths)
    hl = _parse_floats(cfg.half_lives)
    checks = [
        (1 <= cfg.lines <= 200, 'lines invalido'),
        (cfg.evidence_lookback >= 0, 'evidence_lookback invalido'),
        (cfg.same_parity_min_oos >= 0, 'same_parity_min_oos invalido'),
        (bool(ps) and min(ps) > 0, 'prior_strengths invalidos'),
        (bool(hl) and min(hl) > 0, 'half_lives invalidas'),
        (cfg.edge_min_prequential >= 10, 'edge_min_prequential invalido'),
        (cfg.edge_mature_prequential >= cfg.edge_min_prequential, 'edge_mature_prequential invalido'),
        (0 < cfg.edge_alpha < 0.5, 'edge_alpha invalido'),
        (cfg.candidate_pool_rank >= cfg.lines, 'candidate_pool_rank invalido'),
        (cfg.candidate_pool_max_rank >= cfg.candidate_pool_rank and cfg.candidate_pool_max_rank <= UNIVERSE_SIZE, 'candidate_pool_max_rank invalido'),
        (cfg.candidate_pool_growth > 1, 'candidate_pool_growth invalido'),
        (1 <= cfg.strict_max_number_exposure <= cfg.lines, 'strict_max_number_exposure invalido'),
        (1 <= cfg.strict_max_pair_exposure <= cfg.lines, 'strict_max_pair_exposure invalido'),
        (1 <= cfg.strict_max_triple_exposure <= cfg.lines, 'strict_max_triple_exposure invalido'),
        (0 <= cfg.stage2_probability_regret_budget <= 0.05, 'stage2_probability_regret_budget invalido'),
        (0 <= cfg.second_number_coverage_discount <= 1, 'second_number_coverage_discount invalido'),
        (cfg.stage2_top_pairs >= 0 and cfg.stage2_top_pairs <= PAIR_COUNT, 'stage2_top_pairs invalido'),
        (cfg.stage2_top_triples >= 0 and cfg.stage2_top_triples <= TRIPLE_COUNT, 'stage2_top_triples invalido'),
        (cfg.milp_time_limit_seconds > 0, 'milp_time_limit_seconds invalido'),
    ]
    bad = [m for ok, m in checks if not ok]
    if bad:
        raise ValueError('Configuracion V262 invalida: ' + '; '.join(bad))


def _load_module(path: Path, name: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    spec = importlib.util.spec_from_file_location(name, p)
    if spec is None or spec.loader is None:
        raise ImportError(p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def progress(cfg: V262Config, msg: str) -> None:
    if not cfg.quiet:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _array_sha256(a: np.ndarray) -> str:
    x = np.ascontiguousarray(a)
    h = hashlib.sha256()
    h.update(str(x.dtype).encode())
    h.update(str(tuple(x.shape)).encode())
    h.update(x.tobytes())
    return h.hexdigest()


def ordinal_rank_vector(score: np.ndarray) -> np.ndarray:
    """Strict 1..U rank with deterministic combo-index tie-break.

    Exact bucket widths must have the exact number of outcomes implied by their
    boundaries. A tie-worst rank can skip integers and break probability mass
    normalization; ordinal ranks cannot.
    """
    s = np.asarray(score, dtype=np.float64)
    if s.ndim != 1 or len(s) != UNIVERSE_SIZE or not np.all(np.isfinite(s)):
        raise ValueError('score invalido')
    idx = np.arange(len(s), dtype=np.int64)
    order = np.lexsort((idx, -s))
    r = np.empty(len(s), dtype=np.int32)
    r[order] = np.arange(1, len(s) + 1, dtype=np.int32)
    return r


def bucket_ids_from_ranks(ranks: np.ndarray, edges: np.ndarray) -> np.ndarray:
    r = np.asarray(ranks, dtype=np.int32)
    return np.searchsorted(edges, r, side='left').astype(np.int16)


def bucket_geometry(edges: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    lo = np.concatenate(([0], np.asarray(edges[:-1], dtype=np.int64)))
    widths = np.asarray(edges, dtype=np.int64) - lo
    null_mass = widths.astype(float) / float(UNIVERSE_SIZE)
    return widths.astype(np.int32), null_mass


def posterior_bucket_mass(
    winner_ranks: np.ndarray,
    winner_targets: np.ndarray,
    current_target: int,
    edges: np.ndarray,
    prior_strength: float,
    half_life: float,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    widths, null_mass = bucket_geometry(edges)
    wr = np.asarray(winner_ranks, dtype=np.int32)
    wt = np.asarray(winner_targets, dtype=np.int64)
    if len(wr) == 0:
        return null_mass.copy(), {
            'n': 0, 'decayed_weight': 0.0, 'prior_strength': float(prior_strength),
            'half_life': float(half_life), 'posterior_kl_to_uniform': 0.0,
        }
    age = np.maximum(0.0, float(current_target) - wt.astype(float))
    rw = np.exp(-math.log(2.0) * age / float(half_life))
    bi = np.searchsorted(edges, wr, side='left')
    counts = np.bincount(bi, weights=rw, minlength=len(edges)).astype(float)
    alpha = counts + float(prior_strength) * null_mass
    post = alpha / max(1e-15, float(np.sum(alpha)))
    kl = float(np.sum(post * np.log(np.maximum(post, 1e-300) / np.maximum(null_mass, 1e-300))))
    return post, {
        'n': int(len(wr)), 'decayed_weight': float(np.sum(rw)),
        'prior_strength': float(prior_strength), 'half_life': float(half_life),
        'posterior_kl_to_uniform': kl,
    }


def scenario_probability_vector(ranks: np.ndarray, edges: np.ndarray, bucket_mass: np.ndarray) -> np.ndarray:
    widths, _ = bucket_geometry(edges)
    bi = bucket_ids_from_ranks(ranks, edges)
    per_line = np.asarray(bucket_mass, float) / widths.astype(float)
    p = per_line[bi]
    z = float(np.sum(p))
    if not np.isfinite(z) or z <= 0:
        raise RuntimeError('probability scenario invalido')
    p = p / z
    if abs(float(np.sum(p)) - 1.0) > 1e-10:
        raise RuntimeError('probability scenario no normaliza a 1')
    return p


def _combo_index_map(combos: np.ndarray) -> Dict[Tuple[int, ...], int]:
    return {tuple(map(int, c)): int(i) for i, c in enumerate(combos)}


def collect_resolved_v261_evidence(
    cfg: V262Config,
    history: pd.DataFrame,
    combos: np.ndarray,
    v261,
) -> pd.DataFrame:
    actuals = {
        int(r.CONCURSO): tuple(sorted(map(int, (r.R1, r.R2, r.R3, r.R4, r.R5))))
        for r in history.itertuples()
    }
    cmap = _combo_index_map(combos)
    rows = []
    snap_dir = Path(cfg.v261_state_dir) / 'snapshots'
    if not snap_dir.exists():
        return pd.DataFrame(columns=['target', 'winner_rank', 'winner_combo_index', 'snapshot_manifest'])
    files = sorted(snap_dir.glob('target_*.joblib'))
    for p in files:
        try:
            s = joblib.load(p)
            v261.verify_snapshot(s)
            t = int(s['target'])
            if cfg.target is not None and t >= int(cfg.target):
                continue
            if t not in actuals:
                continue
            wi = cmap.get(actuals[t])
            if wi is None:
                continue
            score = np.asarray(s['parent_score'], dtype=np.float64)
            ranks = ordinal_rank_vector(score)
            rows.append({
                'target': t,
                'winner_rank': int(ranks[int(wi)]),
                'winner_combo_index': int(wi),
                'snapshot_manifest': str(s.get('manifest_sha256', '')),
            })
        except Exception:
            # Broken/non-matching historical snapshots must not poison calibration.
            continue
    if not rows:
        return pd.DataFrame(columns=['target', 'winner_rank', 'winner_combo_index', 'snapshot_manifest'])
    df = pd.DataFrame(rows).sort_values('target').drop_duplicates('target', keep='last').reset_index(drop=True)
    if cfg.evidence_lookback > 0:
        df = df.tail(int(cfg.evidence_lookback)).reset_index(drop=True)
    return df




def prequential_edge_gate(cfg: V262Config, evidence: pd.DataFrame, edges: np.ndarray) -> Dict[str, Any]:
    """Causal gate for any departure from the uniform exact-outcome null.

    For each resolved target j after a minimum training prefix, predict its winner
    rank using only earlier targets. The per-target score is the average log
    likelihood ratio across all prior-strength/half-life scenarios. Concentration
    is admitted only when this prequential proper-score edge is significantly >0.
    """
    if evidence.empty or len(evidence) <= cfg.edge_min_prequential:
        return {'state': 'cold_start', 'lambda': 0.0, 'n_predictions': 0, 'mean_log_lift': 0.0, 'p_one_sided': 1.0, 'lower_log_lift': 0.0}
    ps = _parse_floats(cfg.prior_strengths); hl = _parse_floats(cfg.half_lives)
    widths, null_mass = bucket_geometry(edges)
    wr = evidence['winner_rank'].to_numpy(np.int32)
    wt = evidence['target'].to_numpy(np.int64)
    logs = []
    start = int(cfg.edge_min_prequential)
    for j in range(start, len(evidence)):
        event_logs = []
        b = int(np.searchsorted(edges, int(wr[j]), side='left'))
        for prior in ps:
            for half in hl:
                bm, _ = posterior_bucket_mass(wr[:j], wt[:j], int(wt[j]), edges, prior, half)
                lift = float(bm[b] / max(1e-300, null_mass[b]))
                event_logs.append(math.log(max(lift, 1e-300)))
        logs.append(float(np.mean(event_logs)))
    x = np.asarray(logs, float)
    n = len(x)
    if n < 2:
        return {'state': 'cold_start', 'lambda': 0.0, 'n_predictions': int(n), 'mean_log_lift': float(np.mean(x)) if n else 0.0, 'p_one_sided': 1.0, 'lower_log_lift': 0.0}
    mean = float(np.mean(x)); sd = float(np.std(x, ddof=1)); se = sd / math.sqrt(n) if sd > 0 else 0.0
    if se <= 1e-15:
        p = 0.0 if mean > 0 else 1.0
        lower = mean
    else:
        tstat = mean / se
        p = float(student_t.sf(tstat, df=n-1))
        crit = float(student_t.ppf(1.0 - cfg.edge_alpha, df=n-1))
        lower = float(mean - crit * se)
    if mean <= 0 or lower <= 0 or p > cfg.edge_alpha:
        lam = 0.0; state = 'closed'
    else:
        confidence = float(np.clip(lower / max(abs(mean), 1e-12), 0.0, 1.0))
        maturity = float(np.clip(n / float(cfg.edge_mature_prequential), 0.0, 1.0))
        lam = confidence * maturity
        state = 'open'
    return {'state': state, 'lambda': float(lam), 'n_predictions': int(n), 'mean_log_lift': mean, 'p_one_sided': p, 'lower_log_lift': lower}


def build_calibration_scenarios(
    cfg: V262Config,
    current_ranks: np.ndarray,
    evidence: pd.DataFrame,
    current_target: int,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    edges = rank_bucket_edges(cfg)
    ps = _parse_floats(cfg.prior_strengths)
    hl = _parse_floats(cfg.half_lives)
    edge_gate = prequential_edge_gate(cfg, evidence, edges)
    edge_lambda = float(edge_gate['lambda'])
    _, uniform_bucket = bucket_geometry(edges)
    scenarios = []
    meta = []

    if evidence.empty:
        wr = np.array([], dtype=np.int32)
        wt = np.array([], dtype=np.int64)
    else:
        wr = evidence['winner_rank'].to_numpy(np.int32)
        wt = evidence['target'].to_numpy(np.int64)

    def add_scope(scope: str, ranks0: np.ndarray, targets0: np.ndarray) -> None:
        for prior in ps:
            for half in hl:
                bm_raw, d = posterior_bucket_mass(ranks0, targets0, current_target, edges, prior, half)
                bm = (1.0 - edge_lambda) * uniform_bucket + edge_lambda * bm_raw
                bm = bm / max(1e-15, float(np.sum(bm)))
                p = scenario_probability_vector(current_ranks, edges, bm)
                scenarios.append(p)
                meta.append({
                    'scope': scope,
                    'prior_strength': float(prior),
                    'half_life': float(half),
                    'n': int(d['n']),
                    'decayed_weight': float(d['decayed_weight']),
                    'posterior_kl_to_uniform': float(d['posterior_kl_to_uniform']),
                    'bucket_mass': bm.tolist(),
                    'raw_bucket_mass': bm_raw.tolist(),
                })

    add_scope('global', wr, wt)
    if len(evidence) >= int(cfg.same_parity_min_oos):
        m = (wt % 2) == (int(current_target) % 2)
        if int(np.sum(m)) >= int(cfg.same_parity_min_oos):
            add_scope('same_parity', wr[m], wt[m])

    P = np.vstack(scenarios)
    meanp = np.mean(P, axis=0)
    _, null_mass = bucket_geometry(edges)
    # Diagnostic posterior mean over buckets, reconstructed exactly from current
    # rank bucket occupancies.
    mean_bucket = np.mean(np.asarray([m['bucket_mass'] for m in meta], float), axis=0)
    kl = float(np.sum(mean_bucket * np.log(np.maximum(mean_bucket, 1e-300) / np.maximum(null_mass, 1e-300))))
    detail = {
        'edges': edges.tolist(),
        'scenario_count': int(P.shape[0]),
        'evidence_n': int(len(evidence)),
        'scenario_meta': meta,
        'mean_bucket_mass': mean_bucket.tolist(),
        'mean_bucket_kl_to_uniform': kl,
        'mean_probability_sha256': _array_sha256(meanp.astype(np.float64)),
        'edge_gate': edge_gate,
    }
    return P, detail


def exposure_metrics(indices: Sequence[int], combos: np.ndarray, parent_ranks: Optional[np.ndarray] = None) -> Dict[str, Any]:
    idx = np.asarray(indices, dtype=int)
    ne = np.zeros(29, dtype=int)
    pe: Dict[Tuple[int, int], int] = {}
    te: Dict[Tuple[int, int, int], int] = {}
    partners = {n: set() for n in range(1, 29)}
    for i in idx:
        c = tuple(map(int, combos[int(i)]))
        for n in c:
            ne[n] += 1
        for p in itertools.combinations(c, 2):
            pe[p] = pe.get(p, 0) + 1
            partners[p[0]].add(p[1]); partners[p[1]].add(p[0])
        for t in itertools.combinations(c, 3):
            te[t] = te.get(t, 0) + 1
    out: Dict[str, Any] = {
        'lines': int(len(idx)),
        'unique_numbers': int(np.sum(ne[1:] > 0)),
        'min_number_exposure': int(np.min(ne[1:])) if len(idx) else 0,
        'max_number_exposure': int(np.max(ne[1:])) if len(idx) else 0,
        'unique_pairs': int(len(pe)),
        'unique_triples': int(len(te)),
        'max_pair_exposure': int(max(pe.values())) if pe else 0,
        'max_triple_exposure': int(max(te.values())) if te else 0,
        'min_number_distinct_partners': int(min((len(v) for v in partners.values()), default=0)),
    }
    if parent_ranks is not None and len(idx):
        r = np.asarray(parent_ranks, int)[idx]
        out.update({
            'best_parent_rank': int(np.min(r)),
            'median_parent_rank': float(np.median(r)),
            'worst_parent_rank': int(np.max(r)),
        })
    return out


def _incidence(pool_idx: np.ndarray, combos: np.ndarray):
    nums = {n: [] for n in range(1, 29)}
    pairs: Dict[Tuple[int, int], list[int]] = {}
    triples: Dict[Tuple[int, int, int], list[int]] = {}
    for j, i in enumerate(pool_idx):
        c = tuple(map(int, combos[int(i)]))
        for n in c:
            nums[n].append(j)
        for p in itertools.combinations(c, 2):
            pairs.setdefault(p, []).append(j)
        for t in itertools.combinations(c, 3):
            triples.setdefault(t, []).append(j)
    return nums, pairs, triples


def _cap_tiers(cfg: V262Config) -> Tuple[Tuple[int, int, int], ...]:
    a = (cfg.strict_max_number_exposure, cfg.strict_max_pair_exposure, cfg.strict_max_triple_exposure)
    tiers = [
        a,
        (min(cfg.lines, a[0] + 1), a[1], a[2]),
        (min(cfg.lines, a[0] + 2), a[1], a[2]),
        (min(cfg.lines, a[0] + 3), min(cfg.lines, a[1] + 1), min(cfg.lines, a[2] + 1)),
    ]
    out = []
    for x in tiers:
        if x not in out:
            out.append(x)
    return tuple(out)


def _candidate_pool(
    parent_score: np.ndarray,
    scenario_probs: np.ndarray,
    pool_rank: int,
) -> np.ndarray:
    U = len(parent_score)
    idx = np.arange(U, dtype=np.int32)
    chosen: set[int] = set()
    po = np.lexsort((idx, -np.asarray(parent_score, float)))[:pool_rank]
    chosen.update(map(int, po))
    for p in scenario_probs:
        order = np.lexsort((idx, -np.asarray(parent_score, float), -np.asarray(p, float)))[:pool_rank]
        chosen.update(map(int, order))
    arr = np.fromiter(chosen, dtype=np.int32)
    meanp = np.mean(scenario_probs[:, arr], axis=0)
    arr = arr[np.lexsort((arr, -parent_score[arr], -meanp))]
    return arr


def _stage1_constraint(
    pool: np.ndarray,
    combos: np.ndarray,
    scenario_lift: np.ndarray,
    lines: int,
    caps: Tuple[int, int, int],
) -> Tuple[LinearConstraint, int, int]:
    K = len(pool)
    zvar = K
    nvar = K + 1
    nums, pairs, triples = _incidence(pool, combos)
    rows = []; cols = []; vals = []; lb = []; ub = []

    def add(entries: Iterable[Tuple[int, float]], lo: float, hi: float):
        rr = len(lb)
        for c, v in entries:
            rows.append(rr); cols.append(int(c)); vals.append(float(v))
        lb.append(float(lo)); ub.append(float(hi))

    add(((j, 1.0) for j in range(K)), lines, lines)
    maxn, maxp, maxt = caps
    for js in nums.values():
        add(((j, 1.0) for j in js), -np.inf, maxn)
    for js in pairs.values():
        add(((j, 1.0) for j in js), -np.inf, maxp)
    for js in triples.values():
        add(((j, 1.0) for j in js), -np.inf, maxt)
    # z <= scenario mass (scaled as lift-per-line; uniform line lift == 1).
    for s in range(scenario_lift.shape[0]):
        add([(zvar, 1.0)] + [(j, -float(scenario_lift[s, j])) for j in range(K)], -np.inf, 0.0)

    A = coo_matrix((vals, (rows, cols)), shape=(len(lb), nvar)).tocsr()
    return LinearConstraint(A, np.array(lb, float), np.array(ub, float)), nvar, len(lb)


def _posterior_motif_weights(meanp: np.ndarray, combos: np.ndarray, top_pairs: int, top_triples: int):
    nw = np.zeros(29, dtype=float)
    pw: Dict[Tuple[int, int], float] = {}
    tw: Dict[Tuple[int, int, int], float] = {}
    for i, pr in enumerate(np.asarray(meanp, float)):
        if pr <= 0:
            continue
        c = tuple(map(int, combos[int(i)]))
        for n in c:
            nw[n] += pr
        for p in itertools.combinations(c, 2):
            pw[p] = pw.get(p, 0.0) + pr
        for t in itertools.combinations(c, 3):
            tw[t] = tw.get(t, 0.0) + pr
    pitems = sorted(pw.items(), key=lambda kv: (-kv[1], kv[0]))[:int(top_pairs)]
    titems = sorted(tw.items(), key=lambda kv: (-kv[1], kv[0]))[:int(top_triples)]
    return nw, dict(pitems), dict(titems)


def _stage2_constraint_and_objective(
    cfg: V262Config,
    pool: np.ndarray,
    combos: np.ndarray,
    scenario_lift: np.ndarray,
    robust_floor: float,
    caps: Tuple[int, int, int],
    meanp_all: np.ndarray,
) -> Tuple[np.ndarray, LinearConstraint, int]:
    K = len(pool)
    nums, pairs, triples = _incidence(pool, combos)
    nw, pw, tw = _posterior_motif_weights(meanp_all, combos, cfg.stage2_top_pairs, cfg.stage2_top_triples)
    P = list(pw); T = list(tw)
    off = K
    num1 = {n: off + i for i, n in enumerate(range(1, 29))}; off += 28
    num2 = {n: off + i for i, n in enumerate(range(1, 29))}; off += 28
    pairv = {p: off + i for i, p in enumerate(P)}; off += len(P)
    triv = {t: off + i for i, t in enumerate(T)}; off += len(T)
    nvar = off

    rows = []; cols = []; vals = []; lb = []; ub = []
    def add(entries: Iterable[Tuple[int, float]], lo: float, hi: float):
        rr = len(lb)
        for c, v in entries:
            rows.append(rr); cols.append(int(c)); vals.append(float(v))
        lb.append(float(lo)); ub.append(float(hi))

    add(((j, 1.0) for j in range(K)), cfg.lines, cfg.lines)
    maxn, maxp, maxt = caps
    for js in nums.values(): add(((j, 1.0) for j in js), -np.inf, maxn)
    for js in pairs.values(): add(((j, 1.0) for j in js), -np.inf, maxp)
    for js in triples.values(): add(((j, 1.0) for j in js), -np.inf, maxt)
    # Every scenario, not only the posterior mean, must retain the probability floor.
    for s in range(scenario_lift.shape[0]):
        add(((j, float(scenario_lift[s, j])) for j in range(K)), robust_floor, np.inf)

    for n, y in num1.items():
        add([(y, 1.0)] + [(j, -1.0) for j in nums[n]], -np.inf, 0.0)
    for n, y in num2.items():
        add([(y, 2.0)] + [(j, -1.0) for j in nums[n]], -np.inf, 0.0)
    for p, y in pairv.items():
        add([(y, 1.0)] + [(j, -1.0) for j in pairs.get(p, [])], -np.inf, 0.0)
    for t, y in triv.items():
        add([(y, 1.0)] + [(j, -1.0) for j in triples.get(t, [])], -np.inf, 0.0)

    c = np.zeros(nvar, dtype=float)
    # Tiny posterior-mean exact mass tie-break inside the hard robust floor.
    mean_lift = meanp_all[pool] * UNIVERSE_SIZE
    c[:K] = -1e-7 * mean_lift / max(1.0, float(cfg.lines))

    nvals = nw[1:].copy()
    nvals /= max(1e-15, float(np.sum(nvals)))
    for i, n in enumerate(range(1, 29)):
        c[num1[n]] = -cfg.number_coverage_mass * float(nvals[i])
        c[num2[n]] = -cfg.number_coverage_mass * cfg.second_number_coverage_discount * float(nvals[i])
    if P:
        vals0 = np.asarray([pw[p] for p in P], float)
        vals0 /= max(1e-15, float(np.sum(vals0)))
        for p, v in zip(P, vals0):
            c[pairv[p]] = -cfg.pair_coverage_mass * float(v)
    if T:
        vals0 = np.asarray([tw[t] for t in T], float)
        vals0 /= max(1e-15, float(np.sum(vals0)))
        for t, v in zip(T, vals0):
            c[triv[t]] = -cfg.triple_coverage_mass * float(v)

    A = coo_matrix((vals, (rows, cols)), shape=(len(lb), nvar)).tocsr()
    return c, LinearConstraint(A, np.array(lb, float), np.array(ub, float)), len(lb)


def _run_milp(c: np.ndarray, integrality: np.ndarray, bounds: Bounds, constraint: LinearConstraint, cfg: V262Config):
    return milp(
        c=c,
        integrality=integrality,
        bounds=bounds,
        constraints=constraint,
        options={'time_limit': float(cfg.milp_time_limit_seconds), 'mip_rel_gap': float(cfg.milp_mip_rel_gap), 'presolve': True},
    )


def exact_mass_metrics(indices: Sequence[int], scenario_probs: np.ndarray) -> Dict[str, Any]:
    idx = np.asarray(indices, dtype=int)
    masses = np.sum(scenario_probs[:, idx], axis=1)
    base = len(idx) / float(UNIVERSE_SIZE)
    return {
        'uniform_mass': float(base),
        'scenario_min_mass': float(np.min(masses)),
        'scenario_mean_mass': float(np.mean(masses)),
        'scenario_max_mass': float(np.max(masses)),
        'robust_lift_vs_uniform': float(np.min(masses) / max(1e-300, base)),
        'mean_lift_vs_uniform': float(np.mean(masses) / max(1e-300, base)),
        'scenario_masses': masses.tolist(),
    }


def dro_selector(
    parent_score: np.ndarray,
    combos: np.ndarray,
    scenario_probs: np.ndarray,
    cfg: V262Config,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    s = np.asarray(parent_score, float)
    parent_ranks = ordinal_rank_vector(s)
    meanp_all = np.mean(scenario_probs, axis=0)
    pool_rank = int(cfg.candidate_pool_rank)
    attempts = []
    best = None

    while True:
        pool = _candidate_pool(s, scenario_probs, pool_rank)
        scen_lift_pool = scenario_probs[:, pool] * UNIVERSE_SIZE
        K = len(pool)
        for caps in _cap_tiers(cfg):
            con, nvar, nc = _stage1_constraint(pool, combos, scen_lift_pool, cfg.lines, caps)
            c = np.zeros(nvar, dtype=float)
            c[K] = -1.0
            # Posterior mean and parent rank are deterministic tie-breakers only.
            c[:K] = -1e-8 * (meanp_all[pool] * UNIVERSE_SIZE) - 1e-12 / np.maximum(1, parent_ranks[pool])
            integrality = np.zeros(nvar, dtype=np.int8); integrality[:K] = 1
            bounds = Bounds(np.zeros(nvar), np.concatenate([np.ones(K), [np.inf]]))
            try:
                res = _run_milp(c, integrality, bounds, con, cfg)
            except Exception as e:
                attempts.append({'pool_rank': pool_rank, 'pool_size': K, 'caps': caps, 'state': 'exception', 'error': repr(e)})
                continue
            if res.x is None:
                attempts.append({'pool_rank': pool_rank, 'pool_size': K, 'caps': caps, 'state': 'no_solution', 'status': int(res.status)})
                continue
            ix = np.where(np.asarray(res.x[:K]) > 0.5)[0]
            if len(ix) != cfg.lines:
                attempts.append({'pool_rank': pool_rank, 'pool_size': K, 'caps': caps, 'state': 'bad_cardinality', 'chosen': int(len(ix))})
                continue
            idx = pool[ix].astype(np.int32)
            met = exact_mass_metrics(idx, scenario_probs)
            z = float(np.min(np.sum(scen_lift_pool[:, ix], axis=1)))
            attempts.append({'pool_rank': pool_rank, 'pool_size': K, 'caps': caps, 'state': 'ok', 'status': int(res.status), 'robust_scaled_mass': z, 'robust_lift': met['robust_lift_vs_uniform']})
            best = (idx, pool, caps, met, z, int(res.status), nc)
            break
        if best is not None:
            break
        if pool_rank >= cfg.candidate_pool_max_rank:
            break
        pool_rank = min(cfg.candidate_pool_max_rank, max(pool_rank + 1, int(math.ceil(pool_rank * cfg.candidate_pool_growth))))

    if best is None:
        raise RuntimeError('V262 Stage1 no encontro solucion factible')

    idx1, pool, caps, met1, robust_scaled_mass, status1, nc1 = best
    scen_lift_pool = scenario_probs[:, pool] * UNIVERSE_SIZE
    robust_floor = robust_scaled_mass * (1.0 - cfg.stage2_probability_regret_budget)
    c2, con2, nc2 = _stage2_constraint_and_objective(cfg, pool, combos, scen_lift_pool, robust_floor, caps, meanp_all)
    nvar2 = len(c2)
    integrality2 = np.ones(nvar2, dtype=np.int8)
    bounds2 = Bounds(np.zeros(nvar2), np.ones(nvar2))
    res2 = _run_milp(c2, integrality2, bounds2, con2, cfg)
    if res2.x is None:
        idx = idx1
        stage2 = {'state': 'fallback_stage1', 'status': int(res2.status), 'robust_scaled_floor': float(robust_floor)}
    else:
        K = len(pool)
        ix = np.where(np.asarray(res2.x[:K]) > 0.5)[0]
        if len(ix) != cfg.lines:
            raise RuntimeError('V262 Stage2 cardinalidad invalida')
        idx = pool[ix].astype(np.int32)
        met2 = exact_mass_metrics(idx, scenario_probs)
        actual_scaled_min = float(met2['scenario_min_mass'] * UNIVERSE_SIZE)
        if actual_scaled_min + 1e-8 < robust_floor:
            raise RuntimeError('V262 Stage2 violo el probability regret floor')
        stage2 = {
            'state': 'optimal' if int(res2.status) == 0 else 'feasible',
            'status': int(res2.status),
            'objective': float(res2.fun),
            'robust_scaled_floor': float(robust_floor),
            'actual_robust_scaled_mass': actual_scaled_min,
            'stage1_robust_ratio': float(actual_scaled_min / max(1e-15, robust_scaled_mass)),
            'constraints': int(nc2),
            'variables': int(nvar2),
        }

    idx = idx[np.lexsort((idx, -meanp_all[idx], -s[idx]))]
    met_final = exact_mass_metrics(idx, scenario_probs)
    selector = {
        'state': 'exact_mass_dro',
        'candidate_pool_rank': int(pool_rank),
        'candidate_pool_size': int(len(pool)),
        'caps': {'number': int(caps[0]), 'pair': int(caps[1]), 'triple': int(caps[2])},
        'stage1': {
            'status': status1,
            'constraints': int(nc1),
            'robust_scaled_mass': float(robust_scaled_mass),
            'robust_probability_mass': float(met1['scenario_min_mass']),
            'robust_lift_vs_uniform': float(met1['robust_lift_vs_uniform']),
        },
        'stage2': stage2,
        'final_exact_mass': met_final,
        'attempts': attempts,
    }
    return idx, selector


def render_portfolio(core, idx: Sequence[int], parent_score: np.ndarray, parent_ranks: np.ndarray, meanp: np.ndarray, source: str) -> pd.DataFrame:
    rows = []
    for pos, i in enumerate(np.asarray(idx, int), 1):
        rows.append({
            'pos': pos,
            'combo_index': int(i),
            'combo': core.combo_str(tuple(map(int, core.ALL_COMBOS[int(i)]))),
            'parent_rank': int(parent_ranks[int(i)]),
            'parent_score': float(parent_score[int(i)]),
            'posterior_mean_probability': float(meanp[int(i)]),
            'posterior_line_lift_vs_uniform': float(meanp[int(i)] / UNIFORM_LINE_PROB),
            'source': source,
        })
    return pd.DataFrame(rows)


def _snapshot_path(cfg: V262Config, target: int) -> Path:
    return Path(cfg.v262_state_dir) / 'snapshots' / f'target_{int(target)}.joblib'


def _manifest_payload(s: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        'schema': int(s['schema']), 'engine': str(s['engine']), 'target': int(s['target']),
        'history_last': int(s['history_last']), 'history_sha256': str(s['history_sha256']),
        'parent_v261_manifest': str(s.get('parent_v261_manifest', '')),
        'parent_score_sha256': _array_sha256(np.asarray(s['parent_score'])),
        'posterior_mean_sha256': _array_sha256(np.asarray(s['posterior_mean_probability'])),
        'v261_idx': np.asarray(s['v261_idx'], int).tolist(),
        'v262_idx': np.asarray(s['v262_idx'], int).tolist(),
        'calibration': dict(s['calibration_summary']),
        'selector': dict(s['selector']),
    }


def save_snapshot(cfg: V262Config, s: Dict[str, Any]) -> Path:
    p = _snapshot_path(cfg, int(s['target']))
    p.parent.mkdir(parents=True, exist_ok=True)
    x = dict(s)
    x['manifest_sha256'] = hashlib.sha256(json.dumps(_manifest_payload(x), sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    tmp = p.with_suffix('.tmp')
    joblib.dump(x, tmp, compress=1)
    os.replace(tmp, p)
    return p


def verify_snapshot(s: Mapping[str, Any]) -> None:
    if int(s.get('schema', -1)) != V262_SCHEMA:
        raise RuntimeError('V262 snapshot schema invalido')
    got = hashlib.sha256(json.dumps(_manifest_payload(s), sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    if got != str(s.get('manifest_sha256', '')):
        raise RuntimeError('V262 snapshot manifest mismatch')


def preregister(cfg: V262Config, audit, snap: Mapping[str, Any], research: pd.DataFrame, control: pd.DataFrame) -> Path:
    d = Path(str(cfg.prospective_registry_dir).replace('{target}', str(int(audit.target))))
    d.mkdir(parents=True, exist_ok=True)
    p = d / f'target_{int(audit.target)}_V262_preregister.json'
    payload = {
        'engine': V262_ENGINE,
        'target': int(audit.target),
        'history_last': int(audit.max_concurso),
        'history_sha256': str(audit.sha256),
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'snapshot_manifest': str(snap['manifest_sha256']),
        'v262_research': research['combo'].astype(str).tolist(),
        'v261_control': control['combo'].astype(str).tolist(),
        'robust_exact_mass': float(snap['exact_mass_metrics']['scenario_min_mass']),
        'mean_exact_mass': float(snap['exact_mass_metrics']['scenario_mean_mass']),
        'uniform_exact_mass': float(cfg.lines / UNIVERSE_SIZE),
        'calibration_evidence_n': int(snap['calibration_summary']['evidence_n']),
        'statement': 'Frozen before target resolution. V262 optimizes normalized calibrated exact-outcome probability mass under multiple causal calibration scenarios. No 5/5 guarantee.',
    }
    man = dict(payload); man.pop('created_at', None)
    payload['manifest_sha256'] = hashlib.sha256(json.dumps(man, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    if p.exists():
        old = json.loads(p.read_text(encoding='utf-8'))
        if str(old.get('history_sha256')) != str(audit.sha256):
            raise RuntimeError('V262 prereg FROZEN CONFLICT')
        return p
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    os.replace(tmp, p)
    return p


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description='Chispazo V262 Calibrated Exact-Mass Distributionally Robust Optimizer')
    ap.add_argument('--config', default=None)
    ap.add_argument('--history', default=None)
    ap.add_argument('--target', type=int, default=None)
    ap.add_argument('--expected-last', type=int, default=None)
    ap.add_argument('--quiet', action='store_true')
    return ap


def main() -> int:
    args = parser().parse_args()
    cfg = load_config(Path(args.config) if args.config else None)
    d = asdict(cfg)
    if args.history is not None: d['history'] = args.history
    if args.target is not None: d['target'] = args.target
    if args.expected_last is not None: d['expected_last'] = args.expected_last
    if args.quiet: d['quiet'] = True
    cfg = V262Config(**d); validate_config(cfg)

    v261 = _load_module(Path(cfg.v261_engine_path), 'chispazo_v261_parent_v262')
    v259 = _load_module(Path(cfg.v259_engine_path), 'chispazo_v259_parent_v262')
    core = _load_module(Path(cfg.v249_engine_path), 'chispazo_v249_parent_v262')

    hp = Path(cfg.history)
    if not hp.exists():
        print(f'ERROR: no existe {hp}', file=sys.stderr)
        return 2
    hist = core.read_history(hp)
    audit = core.audit_history(hp, hist, cfg.target, cfg.expected_last)
    print('\n=== AUDIT ===')
    print(json.dumps(asdict(audit), indent=2, ensure_ascii=False))
    if audit.status != 'PASS':
        print('ABORTADO por auditoria', file=sys.stderr)
        return 3
    cfg = V262Config(**{**asdict(cfg), 'target': int(audit.target), 'expected_last': int(audit.max_concurso)})

    p261 = Path(cfg.v261_state_dir) / 'snapshots' / f'target_{int(audit.target)}.joblib'
    if not p261.exists():
        raise FileNotFoundError(f'Falta snapshot V261 para target {audit.target}: ejecuta V261 primero: {p261}')
    s261 = joblib.load(p261)
    v261.verify_snapshot(s261)
    if int(s261['target']) != int(audit.target) or str(s261['history_sha256']) != str(audit.sha256):
        raise RuntimeError('Snapshot V261 no coincide con target/historico actual')

    parent_score = np.asarray(s261['parent_score'], dtype=np.float64)
    parent_ranks = ordinal_rank_vector(parent_score)
    v261_idx = np.asarray(s261['v261_idx'], dtype=np.int32)

    evidence = collect_resolved_v261_evidence(cfg, hist, core.ALL_COMBOS, v261)
    scenarios, cal = build_calibration_scenarios(cfg, parent_ranks, evidence, int(audit.target))
    meanp = np.mean(scenarios, axis=0)
    progress(cfg, f"V262 evidence={len(evidence)} resolved V261 targets; scenarios={scenarios.shape[0]}; KL={cal['mean_bucket_kl_to_uniform']:.6g}")

    idx, selector = dro_selector(parent_score, core.ALL_COMBOS, scenarios, cfg)
    exact = exact_mass_metrics(idx, scenarios)
    struct = exposure_metrics(idx, core.ALL_COMBOS, parent_ranks)
    control_exact = exact_mass_metrics(v261_idx, scenarios)
    control_struct = exposure_metrics(v261_idx, core.ALL_COMBOS, parent_ranks)

    research = render_portfolio(core, idx, parent_score, parent_ranks, meanp, 'v262_exact_mass_dro')
    control = render_portfolio(core, v261_idx, parent_score, parent_ranks, meanp, 'v261_control')

    cal_summary = {
        'evidence_n': int(cal['evidence_n']),
        'scenario_count': int(cal['scenario_count']),
        'edges': cal['edges'],
        'mean_bucket_mass': cal['mean_bucket_mass'],
        'mean_bucket_kl_to_uniform': float(cal['mean_bucket_kl_to_uniform']),
        'scenario_meta': cal['scenario_meta'],
        'edge_gate': cal['edge_gate'],
    }
    snap = {
        'schema': V262_SCHEMA,
        'engine': V262_ENGINE,
        'target': int(audit.target),
        'history_last': int(audit.max_concurso),
        'history_sha256': str(audit.sha256),
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'parent_v261_manifest': str(s261.get('manifest_sha256', '')),
        'parent_score': parent_score.astype(np.float32),
        'posterior_mean_probability': meanp.astype(np.float32),
        'v261_idx': v261_idx,
        'v262_idx': idx,
        'calibration_summary': cal_summary,
        'selector': selector,
        'exact_mass_metrics': exact,
        'v261_exact_mass_metrics': control_exact,
        'structure_metrics': struct,
        'v261_structure_metrics': control_struct,
    }
    sp = save_snapshot(cfg, snap)
    verify_snapshot(joblib.load(sp))

    out = Path(str(cfg.out_dir).replace('{target}', str(int(audit.target))))
    out.mkdir(parents=True, exist_ok=True)
    research.to_csv(out / f'v262_EXACT_MASS_DRO_{cfg.lines}_target_{audit.target}.csv', index=False)
    control.to_csv(out / f'v262_CONTROL_V261_{cfg.lines}_target_{audit.target}.csv', index=False)
    evidence.to_csv(out / 'v262_calibration_evidence.csv', index=False)

    order = np.lexsort((np.arange(UNIVERSE_SIZE), -parent_score, -meanp))
    topn = min(UNIVERSE_SIZE, max(cfg.lines, cfg.top_ranking_rows))
    pd.DataFrame({
        'rank_probability': np.arange(1, topn + 1),
        'combo_index': order[:topn],
        'combo': [core.combo_str(tuple(map(int, core.ALL_COMBOS[int(i)]))) for i in order[:topn]],
        'parent_rank': parent_ranks[order[:topn]],
        'posterior_mean_probability': meanp[order[:topn]],
        'posterior_line_lift_vs_uniform': meanp[order[:topn]] / UNIFORM_LINE_PROB,
        'parent_score': parent_score[order[:topn]],
    }).to_csv(out / f'v262_probability_top{topn}_ranking.csv', index=False)

    runtime = {
        'target': int(audit.target),
        'history_last': int(audit.max_concurso),
        'uniform_line_probability': UNIFORM_LINE_PROB,
        'uniform_30line_exact5_probability': float(cfg.lines / UNIVERSE_SIZE),
        'calibration': cal_summary,
        'selector': selector,
        'v262_exact_mass': exact,
        'v261_control_exact_mass': control_exact,
        'v262_structure': struct,
        'v261_structure': control_struct,
        'statement': 'V262 optimizes worst-case normalized Exact5 probability mass across causal rank-calibration scenarios; assembly is only a probability-regret-bounded secondary objective.',
    }
    (out / 'v262_runtime.json').write_text(json.dumps(runtime, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    preg = preregister(cfg, audit, joblib.load(sp), research, control) if cfg.prospective_register else None

    print('\n=== V262 CALIBRATION ===')
    print(json.dumps({k: v for k, v in cal_summary.items() if k != 'scenario_meta'}, indent=2, ensure_ascii=False))
    print('\n=== V262 SELECTOR ===')
    print(json.dumps(selector, indent=2, ensure_ascii=False, default=str))
    print('\n=== V262 EXACT MASS ===')
    print(json.dumps(exact, indent=2, ensure_ascii=False))
    print('\n=== V262 STRUCTURE ===')
    print(json.dumps(struct, indent=2, ensure_ascii=False))
    print('\n=== V262 TOP30 ===')
    print(research.to_string(index=False))
    print('Snapshot:', sp)
    print('Preregister:', preg)
    print('Outputs:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
