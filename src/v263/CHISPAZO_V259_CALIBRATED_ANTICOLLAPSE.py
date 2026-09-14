#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
CHISPAZO V259 — CALIBRATED ANTI-COLLAPSE PORTFOLIO
===================================================

V259 fixes a failure mode exposed by the 12248 lab run: a DIRECT Top-N selector
was allowed to concentrate the 30-line portfolio even though the parent ranking
had no validated prospective Top30 edge. The result was model-risk collapse:
many tickets reused the same numbers while several numbers disappeared entirely.

V259 separates two decisions:
  A) ranking: inherited unchanged from V258 (or V257 fallback), and
  B) portfolio construction: how much concentration is justified by evidence.

Policy
------
* If the parent prospective gate is NOT open, only a small evidence-dependent
  fraction of lines are frozen DIRECT Top-N. Remaining lines are selected from a
  high-quality rank pool with deterministic anti-collapse constraints.
* Cold-start portfolio constraints include full 1..28 number coverage, bounded
  single-number exposure, bounded pair exposure, and overlap penalties.
* As real prospective evidence opens/matures the gate, constraints relax and the
  portfolio moves continuously toward DIRECT Top-N.
* No future result is used. This is portfolio-risk control, not a claim that
  diversity predicts the lottery.

For a fair 5/28 draw every exact combination still has base probability
1/C(28,5) = 1/98,280. V259 prevents unvalidated model concentration from making
coverage unnecessarily brittle; it does not guarantee 5/5.
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
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd

V259_SCHEMA = 259
V259_ENGINE = "CHISPAZO_V259_CALIBRATED_ANTICOLLAPSE"
UNIVERSE_SIZE = 98280


@dataclass(frozen=True)
class V259Config:
    history: str = r"D:\melate\Chispazo.csv"
    v249_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py"
    v258_state_dir: str = r"D:\melate\state_v258"
    v257_state_dir: str = r"D:\melate\state_v257"
    v259_state_dir: str = r"D:\melate\state_v259"
    out_dir: str = r"D:\melate\resultados_v259_{target}"
    prospective_registry_dir: str = r"D:\melate\preregistros_v259"
    target: Optional[int] = None
    expected_last: Optional[int] = None
    lines: int = 30
    quiet: bool = False

    # Evidence -> concentration policy.
    validated_min_oos: int = 30
    parent_gate_lambda_reference: float = 0.65
    cold_aggressive_fraction: float = 0.20
    shadow_mass_aggressive_gain: float = 0.50
    min_aggressive_lines: int = 3

    # Defensive candidate pool and hard caps when edge is not prospectively proven.
    coverage_pool_rank: int = 200
    coverage_pool_max_rank: int = 5000
    coverage_pool_growth: float = 2.5
    cold_require_all_numbers: bool = True
    cold_max_number_exposure: int = 9
    cold_max_pair_exposure: int = 4

    # Greedy marginal objective within the quality pool.
    quality_weight: float = 0.44
    missing_number_weight: float = 0.24
    rare_number_weight: float = 0.14
    unseen_pair_weight: float = 0.10
    overlap_penalty_weight: float = 0.08

    # Structural diagnostics / guardrails.
    collapse_missing_numbers_limit: int = 2
    collapse_max_number_exposure_limit: int = 12
    collapse_effective_numbers_floor: float = 16.0

    top_ranking_rows: int = 5000
    prospective_register: bool = True


def _flatten_toml(d: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    def walk(x: Mapping[str, Any]) -> None:
        for k, v in x.items():
            kk = str(k).replace('-', '_')
            if isinstance(v, dict): walk(v)
            else: out[kk] = v
    walk(d); return out


def load_config(path: Optional[Path]) -> V259Config:
    base = asdict(V259Config())
    if path is not None:
        with Path(path).open('rb') as fh: vals = _flatten_toml(tomllib.load(fh))
        bad = sorted(set(vals) - set(base))
        if bad: raise ValueError(f"Config V259 contiene claves desconocidas: {bad}")
        base.update(vals)
    cfg = V259Config(**base); validate_config(cfg); return cfg


def validate_config(cfg: V259Config) -> None:
    wsum = cfg.quality_weight + cfg.missing_number_weight + cfg.rare_number_weight + cfg.unseen_pair_weight + cfg.overlap_penalty_weight
    checks = [
        (cfg.lines >= 1, 'lines debe ser >=1'),
        (cfg.validated_min_oos >= 10, 'validated_min_oos debe ser >=10'),
        (0 < cfg.parent_gate_lambda_reference <= 1, 'parent_gate_lambda_reference invalido'),
        (0 <= cfg.cold_aggressive_fraction <= 1, 'cold_aggressive_fraction invalido'),
        (0 <= cfg.shadow_mass_aggressive_gain <= 1, 'shadow_mass_aggressive_gain invalido'),
        (0 <= cfg.min_aggressive_lines <= cfg.lines, 'min_aggressive_lines invalido'),
        (cfg.coverage_pool_rank >= cfg.lines and cfg.coverage_pool_rank <= UNIVERSE_SIZE, 'coverage_pool_rank invalido'),
        (cfg.coverage_pool_max_rank >= cfg.coverage_pool_rank and cfg.coverage_pool_max_rank <= UNIVERSE_SIZE, 'coverage_pool_max_rank invalido'),
        (cfg.coverage_pool_growth > 1.0, 'coverage_pool_growth debe ser >1'),
        (cfg.cold_max_number_exposure >= 1, 'cold_max_number_exposure invalido'),
        (cfg.cold_max_pair_exposure >= 1, 'cold_max_pair_exposure invalido'),
        (wsum > 0, 'pesos de selector invalidos'),
        (cfg.top_ranking_rows >= cfg.lines, 'top_ranking_rows debe ser >= lines'),
    ]
    bad = [m for ok, m in checks if not ok]
    if bad: raise ValueError('Configuracion V259 invalida: ' + '; '.join(bad))


def _load_module(path: Path, name: str):
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    spec = importlib.util.spec_from_file_location(name, p)
    if spec is None or spec.loader is None: raise ImportError(p)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


def progress(cfg: V259Config, msg: str) -> None:
    if not cfg.quiet: print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _array_sha256(a: np.ndarray) -> str:
    x = np.ascontiguousarray(a); h = hashlib.sha256(); h.update(str(x.dtype).encode()); h.update(str(tuple(x.shape)).encode()); h.update(x.tobytes()); return h.hexdigest()


def tie_worst_rank_vector(score: np.ndarray) -> np.ndarray:
    s = np.asarray(score, dtype=np.float64)
    if s.ndim != 1 or len(s) != UNIVERSE_SIZE or not np.all(np.isfinite(s)): raise ValueError('score invalido')
    order = np.argsort(-s, kind='stable'); ranks = np.empty(len(s), dtype=np.int32); i = 0
    while i < len(s):
        j = i + 1; v = s[order[i]]
        while j < len(s) and s[order[j]] == v: j += 1
        ranks[order[i:j]] = j; i = j
    return ranks


def direct_topn(score: np.ndarray, n: int) -> np.ndarray:
    s = np.asarray(score, dtype=np.float64); idx = np.arange(len(s), dtype=np.int64)
    return np.lexsort((idx, -s))[:int(n)].astype(np.int32)


def number_exposure(indices: Sequence[int], combos: np.ndarray) -> np.ndarray:
    out = np.zeros(29, dtype=np.int32)
    for i in np.asarray(indices, dtype=int):
        for x in combos[int(i)]: out[int(x)] += 1
    return out


def pair_exposure(indices: Sequence[int], combos: np.ndarray) -> Dict[Tuple[int, int], int]:
    out: Dict[Tuple[int, int], int] = {}
    for i in np.asarray(indices, dtype=int):
        c = tuple(map(int, combos[int(i)]))
        for p in itertools.combinations(c, 2): out[p] = out.get(p, 0) + 1
    return out


def portfolio_metrics(indices: Sequence[int], combos: np.ndarray, ranks: Optional[np.ndarray] = None) -> Dict[str, Any]:
    idx = np.asarray(indices, dtype=int); ne = number_exposure(idx, combos); pe = pair_exposure(idx, combos)
    used = ne[1:] > 0; slots = max(1, 5 * len(idx)); shares = ne[1:].astype(float) / float(slots)
    hhi = float(np.sum(shares * shares)); effective = float(1.0 / hhi) if hhi > 0 else 0.0
    pair_vals = list(pe.values()) or [0]
    result: Dict[str, Any] = {
        'lines': int(len(idx)), 'unique_numbers': int(np.sum(used)), 'missing_numbers': [int(x) for x in np.where(~used)[0] + 1],
        'max_number_exposure': int(np.max(ne[1:])) if len(idx) else 0,
        'min_used_number_exposure': int(np.min(ne[1:][used])) if np.any(used) else 0,
        'number_hhi': hhi, 'effective_numbers': effective,
        'unique_pairs': int(len(pe)), 'max_pair_exposure': int(max(pair_vals)),
    }
    if ranks is not None and len(idx):
        r = np.asarray(ranks, dtype=float)[idx]
        result.update({'best_parent_rank': int(np.min(r)), 'median_parent_rank': float(np.median(r)), 'worst_parent_rank': int(np.max(r)), 'mean_log_parent_rank': float(np.mean(np.log(r)))})
    return result


def collapse_detected(metrics: Mapping[str, Any], cfg: V259Config) -> bool:
    return bool(
        len(metrics.get('missing_numbers', [])) > int(cfg.collapse_missing_numbers_limit) or
        int(metrics.get('max_number_exposure', 0)) > int(cfg.collapse_max_number_exposure_limit) or
        float(metrics.get('effective_numbers', 0.0)) < float(cfg.collapse_effective_numbers_floor)
    )


def parent_policy(parent: Mapping[str, Any], cfg: V259Config) -> Dict[str, Any]:
    gate = dict(parent.get('gate', {})) if isinstance(parent.get('gate', {}), Mapping) else {}
    gate_state = str(gate.get('state', 'unknown')); gate_n = int(gate.get('n', 0) or 0); lam = float(gate.get('lambda', 0.0) or 0.0)
    research_mass = float(parent.get('research_mass', 0.0) or 0.0)
    validated = bool(gate_state == 'open' and gate_n >= int(cfg.validated_min_oos) and lam > 0)
    if validated:
        strength = float(np.clip(lam / float(cfg.parent_gate_lambda_reference), 0.0, 1.0))
        frac = float(cfg.cold_aggressive_fraction + (1.0 - cfg.cold_aggressive_fraction) * strength)
    else:
        strength = 0.0
        frac = float(np.clip(cfg.cold_aggressive_fraction + cfg.shadow_mass_aggressive_gain * research_mass, 0.0, 1.0))
    aggressive = int(np.clip(round(cfg.lines * frac), cfg.min_aggressive_lines, cfg.lines))
    # Hard caps relax continuously only after prospective validation.
    max_num = int(round(cfg.cold_max_number_exposure + strength * (cfg.lines - cfg.cold_max_number_exposure)))
    max_pair = int(round(cfg.cold_max_pair_exposure + strength * (cfg.lines - cfg.cold_max_pair_exposure)))
    require_all = bool(cfg.cold_require_all_numbers and not (validated and strength >= 0.85))
    return {'validated': validated, 'gate_state': gate_state, 'gate_n': gate_n, 'gate_lambda': lam, 'validated_strength': strength,
            'research_mass': research_mass, 'aggressive_fraction': frac, 'aggressive_lines': aggressive,
            'max_number_exposure': max_num, 'max_pair_exposure': max_pair, 'require_all_numbers': require_all}


def _rank_utility(rank: int, pool_rank: int) -> float:
    r = max(1, int(rank)); p = max(2, int(pool_rank))
    return float(np.clip(1.0 - math.log(float(r)) / math.log(float(p)), 0.0, 1.0))


def _candidate_gain(combo: Sequence[int], rank: int, selected_combos: Sequence[set[int]], num_exp: np.ndarray,
                    pair_exp: Mapping[Tuple[int, int], int], pool_rank: int, cfg: V259Config) -> float:
    c = tuple(map(int, combo)); cs = set(c)
    missing = sum(1 for n in c if num_exp[n] == 0) / 5.0
    rare = sum(1.0 / (1.0 + float(num_exp[n])) for n in c) / 5.0
    pairs = list(itertools.combinations(c, 2)); unseen = sum(1 for p in pairs if int(pair_exp.get(p, 0)) == 0) / 10.0
    overlap = (max((len(cs & s) for s in selected_combos), default=0) / 5.0)
    quality = _rank_utility(rank, pool_rank)
    return float(cfg.quality_weight * quality + cfg.missing_number_weight * missing + cfg.rare_number_weight * rare + cfg.unseen_pair_weight * unseen - cfg.overlap_penalty_weight * overlap)


def _hard_ok(combo: Sequence[int], num_exp: np.ndarray, pair_exp: Mapping[Tuple[int, int], int], max_num: int, max_pair: int) -> bool:
    c = tuple(map(int, combo))
    if any(int(num_exp[n]) + 1 > int(max_num) for n in c): return False
    if any(int(pair_exp.get(p, 0)) + 1 > int(max_pair) for p in itertools.combinations(c, 2)): return False
    return True


def anti_collapse_selector(score: np.ndarray, combos: np.ndarray, cfg: V259Config, policy: Mapping[str, Any]) -> Tuple[np.ndarray, Dict[str, Any]]:
    s = np.asarray(score, dtype=np.float64); ranks = tie_worst_rank_vector(s); order = np.lexsort((np.arange(len(s)), -s))
    direct = order[:cfg.lines].astype(np.int32)
    if bool(policy.get('validated')) and int(policy.get('aggressive_lines', 0)) >= cfg.lines:
        return direct, {'state': 'validated_direct_topn', 'relaxations': [], 'direct_seed_lines': cfg.lines}

    aggressive = int(policy['aggressive_lines']); selected = [int(x) for x in order[:aggressive]]; chosen = set(selected)
    num_exp = number_exposure(selected, combos); pexp = pair_exposure(selected, combos); selected_sets = [set(map(int, combos[i])) for i in selected]
    current_pool_rank = int(cfg.coverage_pool_rank)
    pool = [int(x) for x in order[:current_pool_rank] if int(x) not in chosen]
    relaxations = []
    expansions = []

    while len(selected) < cfg.lines:
        remaining_after = cfg.lines - (len(selected) + 1)
        missing_before = int(np.sum(num_exp[1:] == 0))
        best_i = None; best_gain = -1e99
        max_num = int(policy['max_number_exposure']); max_pair = int(policy['max_pair_exposure'])
        for i in pool:
            if i in chosen: continue
            c = tuple(map(int, combos[i]))
            if not _hard_ok(c, num_exp, pexp, max_num, max_pair): continue
            if bool(policy['require_all_numbers']):
                missing_after = missing_before - sum(1 for n in c if num_exp[n] == 0)
                if missing_after > remaining_after * 5: continue
            g = _candidate_gain(c, int(ranks[i]), selected_sets, num_exp, pexp, int(cfg.coverage_pool_rank), cfg)
            if g > best_gain + 1e-15 or (abs(g - best_gain) <= 1e-15 and (best_i is None or int(ranks[i]) < int(ranks[best_i]) or (int(ranks[i]) == int(ranks[best_i]) and i < best_i))):
                best_gain = g; best_i = i
        if best_i is None:
            # Prefer widening the quality pool before weakening anti-collapse caps.
            if current_pool_rank < int(cfg.coverage_pool_max_rank):
                old_pool = current_pool_rank
                current_pool_rank = min(int(cfg.coverage_pool_max_rank), max(current_pool_rank + 1, int(math.ceil(current_pool_rank * float(cfg.coverage_pool_growth)))))
                pool = [int(x) for x in order[:current_pool_rank] if int(x) not in chosen]
                expansions.append({'at_line': len(selected) + 1, 'from': old_pool, 'to': current_pool_rank})
                continue
            # If full number coverage is a hard cold-start contract, search the full universe
            # before weakening exposure caps. This emergency path is explicitly recorded.
            if bool(policy.get('require_all_numbers')) and current_pool_rank < UNIVERSE_SIZE:
                old_pool = current_pool_rank; current_pool_rank = UNIVERSE_SIZE
                pool = [int(x) for x in order if int(x) not in chosen]
                expansions.append({'at_line': len(selected) + 1, 'from': old_pool, 'to': current_pool_rank, 'emergency_full_universe': True})
                continue
            # Only after the configured/full pool is exhausted, relax caps one unit.
            policy = dict(policy); policy['max_pair_exposure'] = int(policy['max_pair_exposure']) + 1; policy['max_number_exposure'] = int(policy['max_number_exposure']) + 1
            relaxations.append({'at_line': len(selected) + 1, 'max_number_exposure': int(policy['max_number_exposure']), 'max_pair_exposure': int(policy['max_pair_exposure'])})
            if len(relaxations) > 10: raise RuntimeError('V259 selector no encontro portfolio factible')
            continue
        selected.append(int(best_i)); chosen.add(int(best_i)); c = tuple(map(int, combos[best_i])); selected_sets.append(set(c))
        for n in c: num_exp[n] += 1
        for p in itertools.combinations(c, 2): pexp[p] = int(pexp.get(p, 0)) + 1

    idx = np.asarray(selected, dtype=np.int32)
    # Structural postconditions are part of the algorithm contract in unvalidated mode.
    met = portfolio_metrics(idx, combos, ranks)
    if bool(policy.get('require_all_numbers')) and met['missing_numbers']:
        raise RuntimeError(f"V259 fallo cobertura completa: {met['missing_numbers']}")
    return idx, {'state': 'anti_collapse_hybrid', 'pool_expansions': expansions, 'final_pool_rank': current_pool_rank, 'relaxations': relaxations, 'direct_seed_lines': aggressive, 'final_caps': {'number': int(policy['max_number_exposure']), 'pair': int(policy['max_pair_exposure'])}}


def _snapshot_path(cfg: V259Config, target: int) -> Path:
    return Path(cfg.v259_state_dir) / 'snapshots' / f'target_{int(target)}.joblib'


def _manifest_payload(s: Mapping[str, Any]) -> Dict[str, Any]:
    return {'schema': int(s['schema']), 'engine': str(s['engine']), 'target': int(s['target']), 'history_last': int(s['history_last']), 'history_sha256': str(s['history_sha256']),
            'parent_manifest': str(s.get('parent_manifest', '')), 'score_sha256': _array_sha256(np.asarray(s['parent_score'])),
            'direct_idx': np.asarray(s['direct_idx'], int).tolist(), 'v259_idx': np.asarray(s['v259_idx'], int).tolist(), 'policy': dict(s['policy'])}


def save_snapshot(cfg: V259Config, s: Dict[str, Any]) -> Path:
    p = _snapshot_path(cfg, int(s['target'])); p.parent.mkdir(parents=True, exist_ok=True)
    x = dict(s); x['manifest_sha256'] = hashlib.sha256(json.dumps(_manifest_payload(x), sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    tmp = p.with_suffix('.tmp'); joblib.dump(x, tmp, compress=1); os.replace(tmp, p); return p


def verify_snapshot(s: Mapping[str, Any]) -> None:
    if int(s.get('schema', -1)) != V259_SCHEMA: raise RuntimeError('V259 snapshot schema invalido')
    got = hashlib.sha256(json.dumps(_manifest_payload(s), sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    if not s.get('manifest_sha256') or got != str(s['manifest_sha256']): raise RuntimeError('V259 snapshot manifest mismatch')


def _load_parent(cfg: V259Config, target: int, audit_sha: str) -> Tuple[Dict[str, Any], str]:
    p258 = Path(cfg.v258_state_dir) / 'snapshots' / f'target_{target}.joblib'
    p257 = Path(cfg.v257_state_dir) / 'snapshots' / f'target_{target}.joblib'
    if p258.exists(): p, label = p258, 'v258'
    elif p257.exists(): p, label = p257, 'v257_fallback'
    else: raise FileNotFoundError(f'Falta parent V258/V257 target={target}')
    s = joblib.load(p)
    if int(s.get('target', -1)) != int(target) or str(s.get('history_sha256')) != str(audit_sha): raise RuntimeError('V259 parent no coincide con target/historico')
    return s, label


def _parent_score_and_idx(parent: Mapping[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    score = np.asarray(parent['research_score'], dtype=np.float64)
    idx = np.asarray(parent.get('research_idx', direct_topn(score, 30)), dtype=np.int32)
    return score, idx


def render(core, idx: Sequence[int], score: np.ndarray, ranks: np.ndarray, source: str) -> pd.DataFrame:
    rows = []
    for pos, i in enumerate(np.asarray(idx, int), 1):
        rows.append({'pos': pos, 'combo_index': int(i), 'combo': core.combo_str(tuple(map(int, core.ALL_COMBOS[i]))), 'parent_rank': int(ranks[i]), 'parent_score': float(score[i]), 'source': source})
    return pd.DataFrame(rows)


def preregister(cfg: V259Config, audit, snap: Mapping[str, Any], port: pd.DataFrame, direct: pd.DataFrame) -> Path:
    d = Path(str(cfg.prospective_registry_dir).replace('{target}', str(int(audit.target)))); d.mkdir(parents=True, exist_ok=True)
    p = d / f'target_{int(audit.target)}_V259_preregister.json'
    payload = {'engine': V259_ENGINE, 'target': int(audit.target), 'history_last': int(audit.max_concurso), 'history_sha256': str(audit.sha256), 'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
               'snapshot_manifest': str(snap['manifest_sha256']), 'policy': dict(snap['policy']), 'portfolio_metrics': dict(snap['portfolio_metrics']), 'direct_metrics': dict(snap['direct_metrics']),
               'v259_portfolio': port['combo'].astype(str).tolist(), 'direct_control': direct['combo'].astype(str).tolist(),
               'statement': 'V259 changes portfolio risk control when predictive edge is unvalidated; it does not claim diversity predicts the draw or guarantee 5/5.'}
    man = dict(payload); man.pop('created_at', None); payload['manifest_sha256'] = hashlib.sha256(json.dumps(man, sort_keys=True, separators=(',', ':'), default=str).encode()).hexdigest()
    if p.exists():
        old = json.loads(p.read_text(encoding='utf-8'))
        if str(old.get('history_sha256')) != str(audit.sha256): raise RuntimeError('V259 prereg FROZEN CONFLICT')
        return p
    tmp = p.with_suffix('.tmp'); tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding='utf-8'); os.replace(tmp, p); return p


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description='Chispazo V259 Calibrated Anti-Collapse Portfolio')
    ap.add_argument('--config', default=None); ap.add_argument('--history', default=None); ap.add_argument('--target', type=int, default=None); ap.add_argument('--expected-last', type=int, default=None); ap.add_argument('--quiet', action='store_true'); return ap


def main() -> int:
    args = parser().parse_args(); cfg = load_config(Path(args.config) if args.config else None); d = asdict(cfg)
    if args.history is not None: d['history'] = args.history
    if args.target is not None: d['target'] = args.target
    if args.expected_last is not None: d['expected_last'] = args.expected_last
    if args.quiet: d['quiet'] = True
    cfg = V259Config(**d); validate_config(cfg)
    core = _load_module(Path(cfg.v249_engine_path), 'chispazo_v249_parent_v259')
    hp = Path(cfg.history)
    if not hp.exists(): print(f'ERROR: no existe {hp}', file=sys.stderr); return 2
    df = core.read_history(hp); audit = core.audit_history(hp, df, cfg.target, cfg.expected_last)
    print('\n=== AUDIT ==='); print(json.dumps(asdict(audit), indent=2, ensure_ascii=False))
    if audit.status != 'PASS': print('ABORTADO por auditoria', file=sys.stderr); return 3
    cfg = V259Config(**{**asdict(cfg), 'target': int(audit.target), 'expected_last': int(audit.max_concurso)})

    parent, parent_label = _load_parent(cfg, int(audit.target), str(audit.sha256)); score, parent_idx = _parent_score_and_idx(parent)
    if len(score) != UNIVERSE_SIZE: raise RuntimeError('V259 parent score no cubre 98,280 combinaciones')
    ranks = tie_worst_rank_vector(score); direct_idx = direct_topn(score, cfg.lines); direct_met = portfolio_metrics(direct_idx, core.ALL_COMBOS, ranks)
    pol = parent_policy(parent, cfg); pol['parent'] = parent_label; pol['parent_direct_collapsed'] = collapse_detected(direct_met, cfg)

    progress(cfg, f"V259 parent={parent_label} validated={pol['validated']} aggressive={pol['aggressive_lines']}/{cfg.lines}")
    v259_idx, selector = anti_collapse_selector(score, core.ALL_COMBOS, cfg, pol); v259_met = portfolio_metrics(v259_idx, core.ALL_COMBOS, ranks)
    pol['selector_state'] = selector['state']; pol['selector_relaxations'] = selector['relaxations']

    direct_port = render(core, direct_idx, score, ranks, 'parent_direct_topn_control')
    v259_port = render(core, v259_idx, score, ranks, 'v259_calibrated_anticollapse')
    direct_set = set(map(int, direct_idx)); v259_port['is_direct_top30'] = v259_port['combo_index'].astype(int).isin(direct_set).astype(int)

    snap = {'schema': V259_SCHEMA, 'engine': V259_ENGINE, 'target': int(audit.target), 'history_last': int(audit.max_concurso), 'history_sha256': str(audit.sha256),
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'parent_label': parent_label, 'parent_manifest': str(parent.get('manifest_sha256', '')),
            'parent_score': score.astype(np.float32), 'direct_idx': direct_idx, 'v259_idx': v259_idx, 'policy': pol, 'direct_metrics': direct_met, 'portfolio_metrics': v259_met}
    sp = save_snapshot(cfg, snap); loaded = joblib.load(sp); verify_snapshot(loaded)

    out = Path(str(cfg.out_dir).replace('{target}', str(int(audit.target)))); out.mkdir(parents=True, exist_ok=True)
    v259_port.to_csv(out / f'v259_ANTICOLLAPSE_{cfg.lines}_target_{audit.target}.csv', index=False)
    direct_port.to_csv(out / f'v259_CONTROL_DIRECT_{cfg.lines}_target_{audit.target}.csv', index=False)
    order = np.lexsort((np.arange(len(score)), -score)); topn = min(len(order), max(cfg.lines, int(cfg.top_ranking_rows)))
    pd.DataFrame({'rank': np.arange(1, topn+1), 'combo_index': order[:topn], 'combo': [core.combo_str(tuple(map(int, core.ALL_COMBOS[i]))) for i in order[:topn]], 'parent_score': score[order[:topn]]}).to_csv(out / f'v259_parent_top{topn}_ranking.csv', index=False)
    runtime = {'target': int(audit.target), 'history_last': int(audit.max_concurso), 'parent': parent_label, 'policy': pol, 'direct_metrics': direct_met, 'v259_metrics': v259_met,
               'selector': selector, 'statement': 'When predictive edge is unvalidated, V259 limits portfolio concentration while keeping every selected line inside the parent high-quality rank pool.'}
    (out / 'v259_runtime.json').write_text(json.dumps(runtime, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    preg = preregister(cfg, audit, loaded, v259_port, direct_port) if cfg.prospective_register else None

    print('\n=== DIRECT CONTROL METRICS ==='); print(json.dumps(direct_met, indent=2, ensure_ascii=False))
    print('\n=== V259 POLICY ==='); print(json.dumps(pol, indent=2, ensure_ascii=False))
    print('\n=== V259 PORTFOLIO METRICS ==='); print(json.dumps(v259_met, indent=2, ensure_ascii=False))
    print('\n=== V259 TOP30 ==='); print(v259_port.to_string(index=False))
    print('Snapshot:', sp); print('Preregister:', preg); print('Outputs:', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
