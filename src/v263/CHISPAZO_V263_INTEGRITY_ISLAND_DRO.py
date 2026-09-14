#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
CHISPAZO V263 — INTEGRITY + ISLAND RESCUE + NULL-HEDGE
=======================================================

V263 fixes the production failure exposed by target 12250:
  * a parent ranking may be produced even when every Exact5 LTR specialist is dead
    (constant/all-zero output), silently degrading the whole stack;
  * head-only candidate pools cannot rescue a valid alternative that lives on a
    specialist island outside the fused head;
  * when no validated Exact5 edge exists, forcing a concentrated portfolio is
    unjustified and creates avoidable joint-coverage holes.

Production contract
-------------------
1. Audit the full 98,280-line parent ranking before V261/V262 is allowed to run.
2. HARD FAIL if fewer than `min_live_exact5` expected Exact5 specialists are live.
   A dead model is not the same thing as a weak model.
3. When healthy, build a candidate-island manifest: parent head + every live
   Exact5 specialist head + supporting specialist heads + disagreement frontier.
   V262/DRO remains the probability objective; islands only expand eligibility.
4. Optional degraded mode (`--allow-degraded-hedge`) is explicitly NOT a model
   prediction. It emits a deterministic null hedge with 30 distinct lines,
   5-6 appearances per number, and pair repetition minimized by local search.
   Under a uniform Exact5 null every 30-line set has the same 30/98,280 Exact5
   mass; this hedge only improves structural/joint coverage, not the true Exact5
   probability.

No current/future winning result is read or used by this engine.
"""

import argparse
import hashlib
import itertools
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

UNIVERSE_SIZE = math.comb(28, 5)
UNIFORM_LINE_PROB = 1.0 / UNIVERSE_SIZE
V263_SCHEMA = 263
V263_ENGINE = "CHISPAZO_V263_INTEGRITY_ISLAND_DRO"

EXACT5_COLUMNS = (
    'score_ltr_ndcg_exact5',
    'score_ltr_adv_exact5',
    'score_ltr_exact5_balanced',
    'score_ltr_exact5_hard',
    'score_ltr_exact5_ultra',
)
SUPPORT_COLUMNS = (
    'score_markov_exact5_residual',
    'score_number_markov',
    'score_number_knn',
    'score_number_transition',
    'score_heuristic',
)


@dataclass(frozen=True)
class V263Config:
    lines: int = 30
    min_live_exact5: int = 2
    min_unique_values: int = 32
    min_nonzero_fraction: float = 0.01
    min_std: float = 1e-8
    parent_head_rank: int = 500
    exact5_island_rank: int = 2500
    support_island_rank: int = 1250
    disagreement_quantile: float = 0.02
    disagreement_max: int = 5000
    island_pool_cap: int = 20000
    hedge_min_exposure: int = 5
    hedge_max_exposure: int = 6
    hedge_iterations: int = 80000
    hedge_restarts: int = 6
    hedge_max_pair_repeat: int = 2
    seed: int = 777


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_combo(s: str) -> Tuple[int, ...]:
    vals = tuple(sorted(int(x) for x in str(s).replace(',', '-').split('-') if str(x).strip()))
    if len(vals) != 5 or len(set(vals)) != 5 or min(vals) < 1 or max(vals) > 28:
        raise ValueError(f'combo invalida: {s!r}')
    return vals


def combo_text(c: Sequence[int]) -> str:
    return '-'.join(f'{int(x):02d}' for x in sorted(c))


def audit_universe(df: pd.DataFrame) -> Dict[str, object]:
    errors: List[str] = []
    if 'combo' not in df.columns:
        errors.append('Falta columna combo')
        return {'status': 'FAIL', 'errors': errors}
    if len(df) != UNIVERSE_SIZE:
        errors.append(f'Universo incompleto: {len(df)} filas; esperado {UNIVERSE_SIZE}')
    dup = int(df['combo'].duplicated().sum())
    if dup:
        errors.append(f'Combos duplicadas: {dup}')
    bad = 0
    for x in df['combo']:
        try:
            parse_combo(x)
        except Exception:
            bad += 1
    if bad:
        errors.append(f'Combos invalidas: {bad}')
    return {'status': 'PASS' if not errors else 'FAIL', 'rows': int(len(df)), 'duplicate_combos': dup, 'invalid_combos': bad, 'errors': errors}


def signal_health(values: pd.Series, cfg: V263Config) -> Dict[str, object]:
    x = pd.to_numeric(values, errors='coerce').to_numpy(float)
    finite = np.isfinite(x)
    xf = x[finite]
    if len(xf) == 0:
        return {'live': False, 'reason': 'no_finite_values', 'finite_fraction': 0.0, 'unique': 0, 'std': 0.0, 'nonzero_fraction': 0.0}
    unique = int(len(np.unique(xf)))
    std = float(np.std(xf))
    nonzero = float(np.mean(np.abs(xf) > 1e-15))
    live = bool(finite.mean() == 1.0 and unique >= cfg.min_unique_values and std > cfg.min_std and nonzero >= cfg.min_nonzero_fraction)
    reasons = []
    if finite.mean() < 1.0: reasons.append('nonfinite')
    if unique < cfg.min_unique_values: reasons.append('low_unique')
    if std <= cfg.min_std: reasons.append('near_constant')
    if nonzero < cfg.min_nonzero_fraction: reasons.append('mostly_zero')
    return {
        'live': live,
        'reason': 'ok' if live else '+'.join(reasons),
        'finite_fraction': float(finite.mean()),
        'unique': unique,
        'std': std,
        'nonzero_fraction': nonzero,
        'min': float(np.min(xf)),
        'max': float(np.max(xf)),
    }


def parent_health_audit(df: pd.DataFrame, cfg: V263Config) -> Dict[str, object]:
    universe = audit_universe(df)
    exact: Dict[str, object] = {}
    support: Dict[str, object] = {}
    for c in EXACT5_COLUMNS:
        exact[c] = {'live': False, 'reason': 'missing'} if c not in df.columns else signal_health(df[c], cfg)
    for c in SUPPORT_COLUMNS:
        support[c] = {'live': False, 'reason': 'missing'} if c not in df.columns else signal_health(df[c], cfg)
    live_exact = [c for c, v in exact.items() if bool(v['live'])]
    live_support = [c for c, v in support.items() if bool(v['live'])]
    if universe['status'] != 'PASS':
        state = 'HARD_FAIL_UNIVERSE'
    elif len(live_exact) < int(cfg.min_live_exact5):
        state = 'HARD_FAIL_EXACT5'
    else:
        state = 'PASS'
    return {
        'schema': V263_SCHEMA,
        'engine': V263_ENGINE,
        'state': state,
        'production_allowed': state == 'PASS',
        'universe': universe,
        'live_exact5_count': len(live_exact),
        'required_live_exact5': int(cfg.min_live_exact5),
        'live_exact5': live_exact,
        'live_support': live_support,
        'exact5': exact,
        'support': support,
    }


def _ordinal_rank_desc(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    idx = np.arange(len(x), dtype=np.int32)
    order = np.lexsort((idx, -x))
    ranks = np.empty(len(x), dtype=np.int32)
    ranks[order] = np.arange(1, len(x) + 1, dtype=np.int32)
    return ranks


def candidate_islands(df: pd.DataFrame, health: Mapping[str, object], cfg: V263Config) -> Tuple[pd.DataFrame, Dict[str, object]]:
    if health.get('state') != 'PASS':
        raise RuntimeError('candidate_islands requiere parent health PASS')
    N = len(df)
    idx = np.arange(N, dtype=np.int32)
    sources: Dict[int, set] = defaultdict(set)
    component_ranks: Dict[str, np.ndarray] = {}

    parent_col = 'score' if 'score' in df.columns else 'anti_saturation_score'
    if parent_col not in df.columns:
        raise ValueError('Ranking sin score/anti_saturation_score')
    parent_rank = _ordinal_rank_desc(pd.to_numeric(df[parent_col], errors='coerce').fillna(-np.inf).to_numpy(float))
    for j in np.where(parent_rank <= cfg.parent_head_rank)[0]: sources[int(j)].add('parent_head')

    for c in health['live_exact5']:
        r = _ordinal_rank_desc(df[c].to_numpy(float)); component_ranks[c] = r
        for j in np.where(r <= cfg.exact5_island_rank)[0]: sources[int(j)].add(c)
    for c in health['live_support']:
        r = _ordinal_rank_desc(df[c].to_numpy(float)); component_ranks[c] = r
        for j in np.where(r <= cfg.support_island_rank)[0]: sources[int(j)].add(c)

    # Disagreement frontier: strong in at least one live specialist while the
    # fused parent does not already rank it in the same percentile.
    live_cols = list(component_ranks)
    if live_cols:
        mat = np.vstack([component_ranks[c] / float(N) for c in live_cols])
        best_pct = np.min(mat, axis=0)
        spread = np.std(mat, axis=0)
        parent_pct = parent_rank / float(N)
        mask = (best_pct <= cfg.disagreement_quantile) & (parent_pct > cfg.disagreement_quantile)
        cand = np.where(mask)[0]
        if len(cand):
            o = cand[np.lexsort((cand, best_pct[cand], -spread[cand]))][:cfg.disagreement_max]
            for j in o: sources[int(j)].add('disagreement_frontier')
    else:
        best_pct = np.ones(N)
        spread = np.zeros(N)

    selected = np.array(sorted(sources), dtype=np.int32)
    if len(selected) > cfg.island_pool_cap:
        # Deterministic cap: keep strongest best-specialist percentile, then parent rank.
        strength = best_pct[selected] if live_cols else parent_rank[selected] / float(N)
        order = np.lexsort((selected, parent_rank[selected], strength))[:cfg.island_pool_cap]
        selected = selected[order]

    rows = []
    for j in selected:
        rows.append({
            'combo_index': int(j),
            'combo': str(df.iloc[j]['combo']),
            'parent_rank': int(parent_rank[j]),
            'island_sources': '|'.join(sorted(sources[int(j)])),
            'island_source_count': int(len(sources[int(j)])),
            'best_component_percentile': float(best_pct[j]) if live_cols else float(parent_rank[j] / N),
            'component_rank_spread': float(spread[j]) if live_cols else 0.0,
        })
    out = pd.DataFrame(rows).sort_values(['best_component_percentile', 'parent_rank', 'combo_index']).reset_index(drop=True)
    meta = {
        'pool_size': int(len(out)),
        'parent_head_rank': int(cfg.parent_head_rank),
        'exact5_island_rank': int(cfg.exact5_island_rank),
        'support_island_rank': int(cfg.support_island_rank),
        'disagreement_quantile': float(cfg.disagreement_quantile),
        'outside_parent_head': int(np.sum(out['parent_rank'].to_numpy(int) > cfg.parent_head_rank)) if len(out) else 0,
        'max_parent_rank_in_pool': int(out['parent_rank'].max()) if len(out) else 0,
    }
    return out, meta


def _number_priority(df: pd.DataFrame, health: Mapping[str, object]) -> pd.DataFrame:
    combos = np.asarray([parse_combo(x) for x in df['combo']], dtype=np.int16)
    cols = list(health.get('live_support', []))
    if not cols:
        return pd.DataFrame({'number': np.arange(1, 29), 'consensus': np.full(28, .5), 'disagreement': np.zeros(28), 'priority': np.full(28, .5)})
    rank_rows = []
    for c in cols:
        vals = []
        arr = df[c].to_numpy(float)
        for n in range(1, 29):
            vals.append(float(np.mean(arr[np.any(combos == n, axis=1)])))
        vals = np.asarray(vals)
        order = np.lexsort((np.arange(28), -vals))
        r = np.empty(28, int); r[order] = np.arange(1, 29)
        rank_rows.append(r)
    R = np.asarray(rank_rows, float)
    scaled = 1.0 - (R - 1.0) / 27.0
    consensus = np.mean(scaled, axis=0)
    disagreement = np.std(scaled, axis=0)
    # Fixed before outcome: exploit consensus, but reserve weight for model disagreement.
    priority = 0.70 * consensus + 0.30 * disagreement
    return pd.DataFrame({'number': np.arange(1, 29), 'consensus': consensus, 'disagreement': disagreement, 'priority': priority}).sort_values(['priority', 'number'], ascending=[False, True]).reset_index(drop=True)


def _pair_counter(blocks: Sequence[Sequence[int]]) -> Counter:
    c = Counter()
    for b in blocks:
        c.update(itertools.combinations(sorted(map(int, b)), 2))
    return c


def _pair_penalty(pc: Counter) -> int:
    return int(sum((v - 1) ** 2 for v in pc.values() if v > 1))


def _initial_blocks(target_exp: Mapping[int, int], seed: int) -> List[List[int]]:
    """Construct an exact degree sequence without repeated numbers inside a block.

    Greedy Havel-Hakimi style: at every block choose the five largest remaining
    degrees, using a seeded tie break. With V263's 5/6 degree sequence this is
    deterministic and always feasible.
    """
    rng = random.Random(seed)
    rem = {int(n): int(e) for n, e in target_exp.items()}
    total = sum(rem.values())
    if total % 5:
        raise ValueError('target exposure sum must be divisible by 5')
    blocks: List[List[int]] = []
    for step in range(total // 5):
        remaining_blocks = total // 5 - step
        # Feasibility invariant: no number may need more appearances than blocks left.
        if any(e > remaining_blocks for e in rem.values()):
            raise RuntimeError('Degree sequence became infeasible')
        jitter = {n: rng.random() for n in rem}
        avail = [n for n, e in rem.items() if e > 0]
        avail.sort(key=lambda n: (-rem[n], jitter[n], n))
        if len(avail) < 5:
            raise RuntimeError('Insufficient distinct numbers for next block')
        block = avail[:5]
        for n in block:
            rem[n] -= 1
        blocks.append(sorted(block))
    if any(rem.values()):
        raise RuntimeError('Nonzero residual degree after initial construction')
    return blocks


def _optimize_pair_repeats(blocks: List[List[int]], seed: int, iterations: int) -> Tuple[List[List[int]], int]:
    rng = random.Random(seed)
    blocks = [list(b) for b in blocks]
    pc = _pair_counter(blocks)
    cur = _pair_penalty(pc)
    best = cur; best_blocks = [sorted(b) for b in blocks]

    def contrib(v: int) -> int:
        return (v - 1) ** 2 if v > 1 else 0

    for it in range(int(iterations)):
        a, b = rng.sample(range(len(blocks)), 2)
        ia = rng.randrange(5); ib = rng.randrange(5)
        x, y = blocks[a][ia], blocks[b][ib]
        if x == y or y in blocks[a] or x in blocks[b]:
            continue
        na = blocks[a][:]; nb = blocks[b][:]
        na[ia] = y; nb[ib] = x
        old = Counter(itertools.combinations(sorted(blocks[a]), 2)); old.update(itertools.combinations(sorted(blocks[b]), 2))
        new = Counter(itertools.combinations(sorted(na), 2)); new.update(itertools.combinations(sorted(nb), 2))
        affected = set(old) | set(new)
        before = sum(contrib(pc[p]) for p in affected)
        delta = Counter(new)
        delta.subtract(old)
        after = sum(contrib(pc[p] + delta[p]) for p in affected)
        d = after - before
        # Small annealing window early, greedier later.
        T = max(0.02, 1.50 * (1.0 - it / max(1, iterations)))
        if d <= 0 or rng.random() < math.exp(-float(d) / T):
            for p, dv in delta.items():
                pc[p] += dv
                if pc[p] == 0:
                    del pc[p]
            blocks[a], blocks[b] = na, nb
            cur += d
            if cur < best:
                best = cur; best_blocks = [sorted(z) for z in blocks]
                if best == 0:
                    break
    return best_blocks, int(best)


def null_hedge(df: pd.DataFrame, health: Mapping[str, object], target: int, cfg: V263Config) -> Tuple[pd.DataFrame, Dict[str, object], pd.DataFrame]:
    if cfg.lines != 30:
        raise ValueError('Null hedge V263 actualmente preregistrado para 30 lineas')
    if 28 * cfg.hedge_min_exposure > cfg.lines * 5 or 28 * cfg.hedge_max_exposure < cfg.lines * 5:
        raise ValueError('Exposure bounds incompatibles con 30x5 slots')
    pri = _number_priority(df, health)
    extras = cfg.lines * 5 - 28 * cfg.hedge_min_exposure
    extra_numbers = set(map(int, pri.head(extras)['number']))
    target_exp = {n: cfg.hedge_min_exposure + (1 if n in extra_numbers else 0) for n in range(1, 29)}

    best_blocks = None; best_pen = 10**9
    for r in range(cfg.hedge_restarts):
        seed = int(cfg.seed + int(target) * 1009 + r * 7919)
        init = _initial_blocks(target_exp, seed)
        blocks, pen = _optimize_pair_repeats(init, seed + 17, cfg.hedge_iterations)
        if pen < best_pen:
            best_pen = pen; best_blocks = blocks
        if pen == 0:
            break
    if best_blocks is None:
        raise RuntimeError('No se pudo construir null hedge')

    blocks = sorted([tuple(sorted(b)) for b in best_blocks])
    exp = Counter(n for b in blocks for n in b)
    pc = _pair_counter(blocks)
    tc = Counter(t for b in blocks for t in itertools.combinations(b, 3))
    partners = {n: set() for n in range(1, 29)}
    for b in blocks:
        for a, z in itertools.combinations(b, 2):
            partners[a].add(z); partners[z].add(a)
    records = []
    rank_map = {str(c): i + 1 for i, c in enumerate(df.sort_values('rank' if 'rank' in df.columns else 'score')['combo'].astype(str))} if 'rank' in df.columns else {}
    for k, b in enumerate(blocks, 1):
        txt = combo_text(b)
        records.append({'portfolio_rank': k, 'combo': txt, 'mode': 'DEGRADED_NULL_HEDGE', 'parent_rank': int(rank_map.get(txt, 0))})
    metrics = {
        'mode': 'DEGRADED_NULL_HEDGE',
        'is_model_prediction': False,
        'uniform_exact5_mass': float(cfg.lines / UNIVERSE_SIZE),
        'uniform_exact5_probability_pct': float(100.0 * cfg.lines / UNIVERSE_SIZE),
        'min_number_exposure': int(min(exp.values())),
        'max_number_exposure': int(max(exp.values())),
        'number_exposures': {str(n): int(exp[n]) for n in range(1, 29)},
        'unique_pairs': int(len(pc)),
        'max_pair_repeat': int(max(pc.values())),
        'repeated_pair_penalty': int(_pair_penalty(pc)),
        'unique_triples': int(len(tc)),
        'max_triple_repeat': int(max(tc.values())),
        'min_distinct_partners': int(min(len(partners[n]) for n in partners)),
        'median_distinct_partners': float(np.median([len(partners[n]) for n in partners])),
        'max_distinct_partners': int(max(len(partners[n]) for n in partners)),
        'extra_exposure_numbers': sorted(extra_numbers),
        'statement': 'Structural hedge only. Under the uniform Exact5 null it has the same 30/98,280 exact probability mass as any other 30 distinct lines.',
    }
    return pd.DataFrame(records), metrics, pri


def run(ranking_path: Path, target: int, out_dir: Path, cfg: V263Config, allow_degraded_hedge: bool) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(ranking_path)
    health = parent_health_audit(df, cfg)
    health['ranking_path'] = str(ranking_path)
    health['ranking_sha256'] = sha256_file(ranking_path)
    health['target'] = int(target)
    (out_dir / f'v263_parent_health_target_{target}.json').write_text(json.dumps(health, indent=2, ensure_ascii=False), encoding='utf-8')

    if health['state'] == 'PASS':
        islands, meta = candidate_islands(df, health, cfg)
        islands.to_csv(out_dir / f'v263_candidate_islands_target_{target}.csv', index=False)
        manifest = {
            'schema': V263_SCHEMA, 'engine': V263_ENGINE, 'target': int(target),
            'state': 'HEALTHY_PARENT_ISLAND_RESCUE_READY', 'health': health,
            'island_meta': meta,
            'statement': 'Feed this expanded eligibility pool to V262/DRO. Islands do not change calibrated probabilities; they prevent head-only truncation from excluding specialist-supported alternatives.',
        }
        (out_dir / f'v263_manifest_target_{target}.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'state': manifest['state'], 'target': target, 'live_exact5': health['live_exact5'], 'island_meta': meta}, indent=2, ensure_ascii=False))
        return 0

    if not allow_degraded_hedge:
        manifest = {
            'schema': V263_SCHEMA, 'engine': V263_ENGINE, 'target': int(target),
            'state': 'ABORTED_PARENT_INTEGRITY', 'health': health,
            'statement': 'No production prediction emitted. Repair/retrain Exact5 parent before V261/V262.',
        }
        (out_dir / f'v263_manifest_target_{target}.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'state': manifest['state'], 'target': target, 'live_exact5_count': health['live_exact5_count']}, indent=2, ensure_ascii=False))
        return 4

    hedge, metrics, priority = null_hedge(df, health, target, cfg)
    hedge.to_csv(out_dir / f'v263_DEGRADED_NULL_HEDGE_{cfg.lines}_target_{target}.csv', index=False)
    priority.to_csv(out_dir / f'v263_number_priority_target_{target}.csv', index=False)
    manifest = {
        'schema': V263_SCHEMA, 'engine': V263_ENGINE, 'target': int(target),
        'state': 'DEGRADED_NULL_HEDGE', 'health': health, 'hedge_metrics': metrics,
        'statement': 'Parent Exact5 failed integrity. This output is a structural hedge, not a predictive portfolio and must not be reported as model edge.',
    }
    (out_dir / f'v263_manifest_target_{target}.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'state': manifest['state'], 'target': target, 'health_state': health['state'], 'hedge_metrics': metrics}, indent=2, ensure_ascii=False))
    print(hedge.to_string(index=False))
    return 0


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description='Chispazo V263 parent-integrity gate + island rescue/null hedge')
    ap.add_argument('--ranking', required=True, help='Full 98,280-row V249 parent ranking CSV')
    ap.add_argument('--target', required=True, type=int)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--allow-degraded-hedge', action='store_true')
    ap.add_argument('--seed', type=int, default=777)
    ap.add_argument('--hedge-iterations', type=int, default=80000)
    ap.add_argument('--hedge-restarts', type=int, default=6)
    return ap


def main() -> int:
    a = parser().parse_args()
    cfg = V263Config(seed=a.seed, hedge_iterations=a.hedge_iterations, hedge_restarts=a.hedge_restarts)
    return run(Path(a.ranking), int(a.target), Path(a.out_dir), cfg, bool(a.allow_degraded_hedge))


if __name__ == '__main__':
    raise SystemExit(main())
