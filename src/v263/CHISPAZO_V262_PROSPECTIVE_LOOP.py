#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""Prospective evidence ledger for V262.

The primary forecast metric is the proper log score assigned to the realized
exact combination, expressed as log(P_v262(actual)/(1/98,280)). Portfolio
Exact5/4+/3+ is tracked separately against the frozen V261 control.
"""

import argparse
import importlib.util
import itertools
import json
import math
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping, Optional

import joblib
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

UNIVERSE_SIZE = math.comb(28, 5)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


@dataclass(frozen=True)
class EvidenceConfig:
    history: str = r"D:\melate\Chispazo.csv"
    v249_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py"
    v262_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V262_EXACT_MASS_DRO.py"
    v262_state_dir: str = r"D:\melate\state_v262"
    evidence_dir: str = r"D:\melate\evidencia_v262"
    gate_min_oos: int = 30
    gate_mature_oos: int = 120
    gate_alpha: float = 0.10
    require_ge4_noninferior: bool = True
    require_ge3_noninferior: bool = True


def combo_hits(lines, actual):
    a = set(map(int, actual)); hs = []
    for c in lines:
        hs.append(len(a & set(map(int, c))))
    b = max(hs) if hs else 0
    return {
        'best_hit': int(b),
        'exact5': int(any(x == 5 for x in hs)),
        'ge4': int(any(x >= 4 for x in hs)),
        'ge3': int(any(x >= 3 for x in hs)),
    }


def one_sided_t_p(x: np.ndarray) -> float:
    x = np.asarray(x, float)
    if len(x) < 2:
        return 1.0
    sd = float(np.std(x, ddof=1))
    if sd <= 1e-15:
        return 0.0 if float(np.mean(x)) > 0 else 1.0
    tstat = float(np.mean(x) / (sd / math.sqrt(len(x))))
    return float(student_t.sf(tstat, df=len(x)-1))


def gate_from_ledger(df: pd.DataFrame, cfg: EvidenceConfig) -> dict[str, Any]:
    if df.empty:
        return {'state': 'cold_start', 'n': 0, 'lambda': 0.0, 'reason': 'no resolved V262 snapshots'}
    g = df[df['eligible'].astype(int) == 1].copy()
    n = len(g)
    if n == 0:
        return {'state': 'cold_start', 'n': 0, 'lambda': 0.0, 'reason': 'no eligible rows'}
    ll = g['log_lift_vs_uniform'].to_numpy(float)
    p = one_sided_t_p(ll)
    mean_ll = float(np.mean(ll))
    exa = int(g['v262_exact5'].sum()); exb = int(g['v261_exact5'].sum())
    g4a = int(g['v262_ge4'].sum()); g4b = int(g['v261_ge4'].sum())
    g3a = int(g['v262_ge3'].sum()); g3b = int(g['v261_ge3'].sum())
    d = {
        'state': 'closed', 'n': int(n), 'lambda': 0.0,
        'mean_log_lift_vs_uniform': mean_ll,
        'geometric_probability_lift': float(math.exp(np.clip(mean_ll, -50, 50))),
        'p_one_sided_logscore': p,
        'v262_exact5': exa, 'v261_exact5': exb,
        'v262_ge4': g4a, 'v261_ge4': g4b,
        'v262_ge3': g3a, 'v261_ge3': g3b,
    }
    if n < cfg.gate_min_oos:
        d['state'] = 'cold_start'; d['reason'] = f'n<{cfg.gate_min_oos}'; return d
    cond = [mean_ll > 0.0, p <= cfg.gate_alpha, exa >= exb]
    if cfg.require_ge4_noninferior: cond.append(g4a >= g4b)
    if cfg.require_ge3_noninferior: cond.append(g3a >= g3b)
    if all(cond):
        lam = min(1.0, max(0.0, (n - cfg.gate_min_oos + 1) / max(1, cfg.gate_mature_oos - cfg.gate_min_oos + 1)))
        d.update({'state': 'open', 'lambda': float(lam), 'reason': 'proper-log-score edge and portfolio noninferiority pass prospectively'})
    else:
        d['reason'] = 'prospective probability/portfolio gate conditions not met'
    return d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', default=EvidenceConfig.history)
    ap.add_argument('--v249-engine-path', default=EvidenceConfig.v249_engine_path)
    ap.add_argument('--v262-engine-path', default=EvidenceConfig.v262_engine_path)
    ap.add_argument('--v262-state-dir', default=EvidenceConfig.v262_state_dir)
    ap.add_argument('--evidence-dir', default=EvidenceConfig.evidence_dir)
    a = ap.parse_args()
    cfg = EvidenceConfig(history=a.history, v249_engine_path=a.v249_engine_path, v262_engine_path=a.v262_engine_path, v262_state_dir=a.v262_state_dir, evidence_dir=a.evidence_dir)

    core = _load_module(Path(cfg.v249_engine_path), 'v262e_core')
    v262 = _load_module(Path(cfg.v262_engine_path), 'v262e_engine')
    hist = core.read_history(Path(cfg.history))
    actuals = {int(r.CONCURSO): tuple(sorted(map(int, (r.R1, r.R2, r.R3, r.R4, r.R5)))) for r in hist.itertuples()}
    cmap = {tuple(map(int, c)): int(i) for i, c in enumerate(core.ALL_COMBOS)}
    rows = []
    for p in sorted((Path(cfg.v262_state_dir) / 'snapshots').glob('target_*.joblib')):
        try:
            s = joblib.load(p); v262.verify_snapshot(s)
            t = int(s['target'])
            if t not in actuals: continue
            actual = actuals[t]; wi = cmap[actual]
            prob = float(np.asarray(s['posterior_mean_probability'], float)[wi])
            log_lift = float(math.log(max(prob, 1e-300) * UNIVERSE_SIZE))
            v262_lines = [core.ALL_COMBOS[int(i)] for i in np.asarray(s['v262_idx'], int)]
            v261_lines = [core.ALL_COMBOS[int(i)] for i in np.asarray(s['v261_idx'], int)]
            a262 = combo_hits(v262_lines, actual); a261 = combo_hits(v261_lines, actual)
            rows.append({
                'target': t, 'eligible': 1, 'actual': core.combo_str(actual),
                'actual_probability': prob, 'log_lift_vs_uniform': log_lift,
                'probability_lift_vs_uniform': float(prob * UNIVERSE_SIZE),
                'v262_best_hit': a262['best_hit'], 'v262_exact5': a262['exact5'], 'v262_ge4': a262['ge4'], 'v262_ge3': a262['ge3'],
                'v261_best_hit': a261['best_hit'], 'v261_exact5': a261['exact5'], 'v261_ge4': a261['ge4'], 'v261_ge3': a261['ge3'],
                'snapshot_manifest': str(s.get('manifest_sha256', '')),
            })
        except Exception as e:
            rows.append({'target': -1, 'eligible': 0, 'error': f'{p.name}: {type(e).__name__}: {e}'})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(['eligible', 'target'], ascending=[False, True]).reset_index(drop=True)
    gate = gate_from_ledger(df, cfg)
    out = Path(cfg.evidence_dir); out.mkdir(parents=True, exist_ok=True)
    lp = out / 'v262_prospective_ledger.csv'; gp = out / 'v262_probability_gate.json'
    df.to_csv(lp, index=False)
    gp.write_text(json.dumps({'created_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'gate': gate}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(gate, indent=2, ensure_ascii=False))
    print('Ledger:', lp); print('Gate:', gp)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
