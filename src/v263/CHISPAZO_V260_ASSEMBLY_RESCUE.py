#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
CHISPAZO V260 — EVIDENCE-SHRUNK ASSEMBLY RESCUE
=================================================

V260 extends V259's anti-collapse portfolio control. V259 fixed single-number
concentration, but the 12244 forensic review exposed a second failure mode:
correct numbers can be present across the portfolio yet never be assembled
into useful pairs/triples in the same tickets.

V260 therefore separates:
  1) exact-combination quality, inherited unchanged from the causal parent score;
  2) portfolio risk control, inherited from V259; and
  3) assembly coverage, optimized only while exact Top30 edge is unvalidated.

Assembly evidence is NOT taken from the realized target. It is derived only from
motifs repeatedly represented in the current target's causal elite rank pool.
Pair/triple motif weights are shrunk strongly toward their uniform null and
clipped. A MILP then chooses the defensive part of the 30-line portfolio while:
  * preserving the aggressive DIRECT core,
  * enforcing number exposure lower/upper bounds,
  * bounding pair and triple repetition,
  * rewarding coverage of evidence-admitted elite pairs/triples,
  * restricting all tickets to a high-quality parent-rank pool whenever feasible.

If the prospective parent gate matures, V260 returns DIRECT Top-N exactly. Thus
assembly rescue is a cold-start/model-risk defense, not a claim that diversity
or pair/triple patterns predict a fair lottery.
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

try:
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import coo_matrix
    SCIPY_MILP = True
except Exception:
    SCIPY_MILP = False

V260_SCHEMA = 260
V260_ENGINE = "CHISPAZO_V260_ASSEMBLY_RESCUE"
UNIVERSE_SIZE = 98280
PAIR_COUNT = math.comb(28, 2)
TRIPLE_COUNT = math.comb(28, 3)


@dataclass(frozen=True)
class V260Config:
    history: str = r"D:\melate\Chispazo.csv"
    v249_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py"
    v259_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V259_CALIBRATED_ANTICOLLAPSE.py"
    v259_state_dir: str = r"D:\melate\state_v259"
    v258_state_dir: str = r"D:\melate\state_v258"
    v257_state_dir: str = r"D:\melate\state_v257"
    v260_state_dir: str = r"D:\melate\state_v260"
    out_dir: str = r"D:\melate\resultados_v260_{target}"
    prospective_registry_dir: str = r"D:\melate\preregistros_v260"
    target: Optional[int] = None
    expected_last: Optional[int] = None
    lines: int = 30
    quiet: bool = False

    # Candidate-pool expansion. Never weaken structure before widening quality pool.
    candidate_pool_rank: int = 200
    candidate_pool_max_rank: int = 5000
    candidate_pool_growth: float = 2.5

    # Cold-start structure. 150 number-slots / 28 ~= 5.36, so min=2 is conservative.
    cold_min_number_exposure: int = 2
    cold_max_number_exposure: int = 9
    cold_max_pair_exposure: int = 4
    cold_max_triple_exposure: int = 2

    # Elite motif model. Weights are rank-derived, null-shrunk and clipped.
    assembly_elite_rank: int = 500
    assembly_rank_temperature: float = 120.0
    assembly_prior_strength: float = 160.0
    assembly_min_lift: float = 1.05
    assembly_max_lift: float = 2.50
    assembly_top_pairs: int = 96
    assembly_top_triples: int = 160

    # MILP objective shares. Each block is normalized so these are comparable masses.
    quality_mass: float = 0.62
    pair_assembly_mass: float = 0.22
    triple_assembly_mass: float = 0.16

    # Solver / fallback.
    milp_time_limit_seconds: float = 20.0
    milp_mip_rel_gap: float = 0.0
    fallback_to_v259_greedy: bool = True

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


def load_config(path: Optional[Path]) -> V260Config:
    base = asdict(V260Config())
    if path is not None:
        with Path(path).open('rb') as fh: vals = _flatten_toml(tomllib.load(fh))
        bad = sorted(set(vals) - set(base))
        if bad: raise ValueError(f"Config V260 contiene claves desconocidas: {bad}")
        base.update(vals)
    cfg = V260Config(**base); validate_config(cfg); return cfg


def validate_config(cfg: V260Config) -> None:
    checks = [
        (cfg.lines >= 1, 'lines debe ser >=1'),
        (cfg.candidate_pool_rank >= cfg.lines and cfg.candidate_pool_rank <= UNIVERSE_SIZE, 'candidate_pool_rank invalido'),
        (cfg.candidate_pool_max_rank >= cfg.candidate_pool_rank and cfg.candidate_pool_max_rank <= UNIVERSE_SIZE, 'candidate_pool_max_rank invalido'),
        (cfg.candidate_pool_growth > 1.0, 'candidate_pool_growth debe ser >1'),
        (0 <= cfg.cold_min_number_exposure <= cfg.cold_max_number_exposure, 'number exposure bounds invalidos'),
        (cfg.cold_max_number_exposure <= cfg.lines, 'cold_max_number_exposure > lines'),
        (cfg.cold_max_pair_exposure >= 1, 'cold_max_pair_exposure invalido'),
        (cfg.cold_max_triple_exposure >= 1, 'cold_max_triple_exposure invalido'),
        (cfg.assembly_elite_rank >= cfg.lines and cfg.assembly_elite_rank <= UNIVERSE_SIZE, 'assembly_elite_rank invalido'),
        (cfg.assembly_rank_temperature > 0, 'assembly_rank_temperature invalido'),
        (cfg.assembly_prior_strength >= 0, 'assembly_prior_strength invalido'),
        (1.0 <= cfg.assembly_min_lift <= cfg.assembly_max_lift, 'assembly lift bounds invalidos'),
        (0 <= cfg.assembly_top_pairs <= PAIR_COUNT, 'assembly_top_pairs invalido'),
        (0 <= cfg.assembly_top_triples <= TRIPLE_COUNT, 'assembly_top_triples invalido'),
        (cfg.quality_mass >= 0 and cfg.pair_assembly_mass >= 0 and cfg.triple_assembly_mass >= 0, 'objective masses invalidas'),
        (cfg.quality_mass + cfg.pair_assembly_mass + cfg.triple_assembly_mass > 0, 'objective mass total debe ser >0'),
        (cfg.milp_time_limit_seconds > 0, 'milp_time_limit_seconds invalido'),
        (cfg.milp_mip_rel_gap >= 0, 'milp_mip_rel_gap invalido'),
        (cfg.top_ranking_rows >= cfg.lines, 'top_ranking_rows debe ser >= lines'),
    ]
    bad = [m for ok, m in checks if not ok]
    if bad: raise ValueError('Configuracion V260 invalida: ' + '; '.join(bad))


def _load_module(path: Path, name: str):
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    spec = importlib.util.spec_from_file_location(name, p)
    if spec is None or spec.loader is None: raise ImportError(p)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


def progress(cfg: V260Config, msg: str) -> None:
    if not cfg.quiet: print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _array_sha256(a: np.ndarray) -> str:
    x = np.ascontiguousarray(a); h = hashlib.sha256(); h.update(str(x.dtype).encode()); h.update(str(tuple(x.shape)).encode()); h.update(x.tobytes()); return h.hexdigest()


def _normalize_positive(d: Mapping[Tuple[int, ...], float]) -> Dict[Tuple[int, ...], float]:
    vals = {k: max(0.0, float(v)) for k, v in d.items() if float(v) > 0}
    z = sum(vals.values())
    if z <= 0: return {}
    return {k: v / z for k, v in vals.items()}


def _rank_weights(n: int, temperature: float) -> np.ndarray:
    r = np.arange(n, dtype=float)
    w = np.exp(-r / float(temperature)); return w / max(1e-15, float(w.sum()))


def assembly_profile(score: np.ndarray, combos: np.ndarray, cfg: V260Config, v259) -> Dict[str, Any]:
    """Build current-target motif evidence from the causal elite ranking only.

    For each motif we compare its rank-weighted elite mass to the uniform motif null,
    then shrink by a pseudo-count prior and clip the lift. Only positive residual
    lift above assembly_min_lift is admitted into the assembly objective.
    """
    s = np.asarray(score, dtype=float)
    order = np.lexsort((np.arange(len(s)), -s))
    elite_n = min(int(cfg.assembly_elite_rank), len(order)); elite = order[:elite_n]
    rw = _rank_weights(elite_n, cfg.assembly_rank_temperature)

    pair_obs: Dict[Tuple[int, int], float] = {}
    triple_obs: Dict[Tuple[int, int, int], float] = {}
    for j, i in enumerate(elite):
        c = tuple(map(int, combos[int(i)])); w = float(rw[j])
        for p in itertools.combinations(c, 2): pair_obs[p] = pair_obs.get(p, 0.0) + w / 10.0
        for t in itertools.combinations(c, 3): triple_obs[t] = triple_obs.get(t, 0.0) + w / 10.0

    # Under the 5/28 uniform null, motif mass across all pairs/triples is uniform.
    prior = float(cfg.assembly_prior_strength)
    n_eff = float(elite_n)
    def residual_lifts(obs: Mapping[Tuple[int, ...], float], count: int) -> Dict[Tuple[int, ...], float]:
        null = 1.0 / float(count)
        out: Dict[Tuple[int, ...], float] = {}
        # obs is a probability mass over motifs; convert to pseudo counts n_eff*obs.
        den = n_eff + prior
        for k, mass in obs.items():
            post = (n_eff * float(mass) + prior * null) / den
            lift = float(np.clip(post / null, 1.0 / cfg.assembly_max_lift, cfg.assembly_max_lift))
            if lift >= float(cfg.assembly_min_lift): out[k] = lift - 1.0
        return out

    pair_sig = residual_lifts(pair_obs, PAIR_COUNT)
    triple_sig = residual_lifts(triple_obs, TRIPLE_COUNT)
    pair_ranked = sorted(pair_sig.items(), key=lambda kv: (-kv[1], kv[0]))[:int(cfg.assembly_top_pairs)]
    triple_ranked = sorted(triple_sig.items(), key=lambda kv: (-kv[1], kv[0]))[:int(cfg.assembly_top_triples)]
    pair_w = _normalize_positive(dict(pair_ranked)); triple_w = _normalize_positive(dict(triple_ranked))
    return {
        'elite_rank': elite_n,
        'pair_weights': pair_w,
        'triple_weights': triple_w,
        'pair_signal_count': len(pair_sig),
        'triple_signal_count': len(triple_sig),
        'admitted_pairs': len(pair_w),
        'admitted_triples': len(triple_w),
        'top_pairs': [{'motif': '-'.join(map(str, k)), 'weight': float(v)} for k, v in list(pair_w.items())[:20]],
        'top_triples': [{'motif': '-'.join(map(str, k)), 'weight': float(v)} for k, v in list(triple_w.items())[:20]],
    }


def assembly_metrics(indices: Sequence[int], combos: np.ndarray, profile: Mapping[str, Any], ranks: Optional[np.ndarray] = None, v259=None) -> Dict[str, Any]:
    idx = np.asarray(indices, dtype=int)
    pe: Dict[Tuple[int,int], int] = {}; te: Dict[Tuple[int,int,int], int] = {}
    num_partners = {n: set() for n in range(1,29)}
    for i in idx:
        c = tuple(map(int, combos[int(i)]))
        for p in itertools.combinations(c, 2):
            pe[p] = pe.get(p, 0) + 1; num_partners[p[0]].add(p[1]); num_partners[p[1]].add(p[0])
        for t in itertools.combinations(c, 3): te[t] = te.get(t, 0) + 1
    pw = profile.get('pair_weights', {}); tw = profile.get('triple_weights', {})
    pair_cov = float(sum(float(w) for k, w in pw.items() if pe.get(tuple(k), 0) > 0))
    triple_cov = float(sum(float(w) for k, w in tw.items() if te.get(tuple(k), 0) > 0))
    m = {
        'unique_pairs': int(len(pe)), 'unique_triples': int(len(te)),
        'max_pair_exposure': int(max(pe.values()) if pe else 0),
        'max_triple_exposure': int(max(te.values()) if te else 0),
        'assembly_pair_weighted_coverage': pair_cov,
        'assembly_triple_weighted_coverage': triple_cov,
        'min_number_distinct_partners': int(min((len(x) for x in num_partners.values()), default=0)),
        'mean_number_distinct_partners': float(np.mean([len(x) for x in num_partners.values()])),
    }
    if v259 is not None:
        m.update(v259.portfolio_metrics(idx, combos, ranks))
    return m


def _motif_incidence(pool_idx: np.ndarray, combos: np.ndarray, motifs: Sequence[Tuple[int,...]]) -> Dict[Tuple[int,...], list[int]]:
    pos = {m: [] for m in motifs}
    motif_set = set(motifs)
    for j, i in enumerate(pool_idx):
        c = tuple(map(int, combos[int(i)])); k = len(next(iter(motifs))) if motifs else 0
        if k:
            for m in itertools.combinations(c, k):
                if m in motif_set: pos[m].append(j)
    return pos



def safe_aggressive_core(score: np.ndarray, combos: np.ndarray, desired: int, cfg: V260Config, v259) -> Tuple[np.ndarray, Dict[str,Any]]:
    """Keep the best DIRECT candidates that do not themselves violate cold structural caps.

    A cold-start aggressive core is not allowed to make the downstream MILP infeasible.
    Once the prospective gate is validated this function is bypassed and DIRECT Top-N is exact.
    """
    order=np.lexsort((np.arange(len(score)),-np.asarray(score,float)))
    selected=[]; num=np.zeros(29,dtype=np.int32); pe={}; te={}; skipped=[]
    scan_limit=min(len(order),max(int(cfg.candidate_pool_rank),int(desired)*20))
    for i in order[:scan_limit]:
        c=tuple(map(int,combos[int(i)]))
        if any(int(num[n])+1 > int(cfg.cold_max_number_exposure) for n in c):
            skipped.append({'combo_index':int(i),'reason':'number_cap'}); continue
        if any(int(pe.get(p,0))+1 > int(cfg.cold_max_pair_exposure) for p in itertools.combinations(c,2)):
            skipped.append({'combo_index':int(i),'reason':'pair_cap'}); continue
        if any(int(te.get(t,0))+1 > int(cfg.cold_max_triple_exposure) for t in itertools.combinations(c,3)):
            skipped.append({'combo_index':int(i),'reason':'triple_cap'}); continue
        selected.append(int(i))
        for n in c:num[n]+=1
        for q in itertools.combinations(c,2):pe[q]=int(pe.get(q,0))+1
        for q in itertools.combinations(c,3):te[q]=int(te.get(q,0))+1
        if len(selected)>=int(desired):break
    if len(selected)<int(desired):
        raise RuntimeError(f'V260 no pudo construir core agresivo estructural {len(selected)}/{desired}')
    return np.asarray(selected,dtype=np.int32),{'desired':int(desired),'selected':int(len(selected)),'skipped':skipped[:50],'scan_limit':int(scan_limit)}

def _solve_milp(score: np.ndarray, combos: np.ndarray, pool_idx: np.ndarray, aggressive_idx: np.ndarray,
                profile: Mapping[str, Any], cfg: V260Config, v259) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
    if not SCIPY_MILP: return None, {'state':'scipy_milp_unavailable'}
    K = len(pool_idx); pool_pos = {int(i): j for j, i in enumerate(pool_idx)}
    forced = [pool_pos[int(i)] for i in aggressive_idx if int(i) in pool_pos]
    pair_w: Dict[Tuple[int,int], float] = {tuple(map(int,k)): float(v) for k,v in profile.get('pair_weights',{}).items()}
    triple_w: Dict[Tuple[int,int,int], float] = {tuple(map(int,k)): float(v) for k,v in profile.get('triple_weights',{}).items()}
    pairs = list(pair_w); triples = list(triple_w)
    P, T = len(pairs), len(triples); nvar = K + P + T

    # Objective normalized by block so masses have interpretable total influence.
    ranks = v259.tie_worst_rank_vector(score)
    denom = max(1e-12, math.log(max(2, int(np.max(ranks[pool_idx])))))
    quality = np.array([max(0.0, 1.0 - math.log(max(1,int(ranks[i]))) / denom) for i in pool_idx], dtype=float)
    c = np.zeros(nvar, dtype=float)
    c[:K] = -float(cfg.quality_mass) * quality / float(cfg.lines)
    if P:
        vals = np.array([pair_w[p] for p in pairs], float); vals /= max(1e-15, vals.sum()); c[K:K+P] = -float(cfg.pair_assembly_mass) * vals
    if T:
        vals = np.array([triple_w[t] for t in triples], float); vals /= max(1e-15, vals.sum()); c[K+P:] = -float(cfg.triple_assembly_mass) * vals

    rows=[]; cols=[]; vals=[]; lb=[]; ub=[]
    def add_row(entries: Iterable[Tuple[int,float]], lo: float, hi: float):
        r=len(lb)
        for col,val in entries: rows.append(r); cols.append(int(col)); vals.append(float(val))
        lb.append(float(lo)); ub.append(float(hi))

    # Exactly lines tickets.
    add_row(((j,1.0) for j in range(K)), cfg.lines, cfg.lines)
    # Force aggressive direct core.
    for j in forced: add_row([(j,1.0)], 1.0, 1.0)

    # Number lower/upper exposures.
    for n in range(1,29):
        js=[j for j,i in enumerate(pool_idx) if n in set(map(int,combos[int(i)]))]
        add_row(((j,1.0) for j in js), cfg.cold_min_number_exposure, cfg.cold_max_number_exposure)

    # Pair repetition caps for all 378 pairs represented in pool.
    for p in itertools.combinations(range(1,29),2):
        js=[j for j,i in enumerate(pool_idx) if p[0] in combos[int(i)] and p[1] in combos[int(i)]]
        if js: add_row(((j,1.0) for j in js), -np.inf, cfg.cold_max_pair_exposure)

    # Triple repetition cap only for represented triples.
    tri_to_js: Dict[Tuple[int,int,int], list[int]] = {}
    for j,i in enumerate(pool_idx):
        for t in itertools.combinations(tuple(map(int,combos[int(i)])),3): tri_to_js.setdefault(t,[]).append(j)
    for t,js in tri_to_js.items(): add_row(((j,1.0) for j in js), -np.inf, cfg.cold_max_triple_exposure)

    # y_m <= sum x_i containing motif, y is automatically pushed to 1 by negative objective.
    pinc = _motif_incidence(pool_idx, combos, pairs)
    for q,p in enumerate(pairs):
        y=K+q; add_row([(y,1.0)] + [(j,-1.0) for j in pinc.get(p,[])], -np.inf, 0.0)
    tinc = _motif_incidence(pool_idx, combos, triples)
    for q,t in enumerate(triples):
        y=K+P+q; add_row([(y,1.0)] + [(j,-1.0) for j in tinc.get(t,[])], -np.inf, 0.0)

    A=coo_matrix((vals,(rows,cols)),shape=(len(lb),nvar)).tocsr()
    bounds=Bounds(np.zeros(nvar),np.ones(nvar)); integrality=np.ones(nvar,dtype=np.int8)
    try:
        res=milp(c=c,integrality=integrality,bounds=bounds,constraints=LinearConstraint(A,np.array(lb),np.array(ub)),
                 options={'time_limit':float(cfg.milp_time_limit_seconds),'mip_rel_gap':float(cfg.milp_mip_rel_gap),'presolve':True})
    except Exception as e:
        return None, {'state':'milp_exception','error':repr(e)}
    if res.x is None:
        return None, {'state':'milp_infeasible_or_no_solution','status':int(res.status),'message':str(res.message)}
    chosen=np.where(np.asarray(res.x[:K]) > .5)[0]
    if len(chosen) != cfg.lines:
        return None, {'state':'milp_bad_cardinality','status':int(res.status),'chosen':int(len(chosen)),'message':str(res.message)}
    idx=pool_idx[chosen].astype(np.int32)
    # Deterministic presentation order by parent score/rank, not solver variable order.
    idx=idx[np.lexsort((idx,-np.asarray(score)[idx]))]
    return idx, {'state':'milp_assembly_rescue','status':int(res.status),'message':str(res.message),'objective':float(res.fun),
                 'pool_size':int(K),'variables':int(nvar),'constraints':int(len(lb)),'forced_core':int(len(forced))}


def assembly_selector(score: np.ndarray, combos: np.ndarray, cfg: V260Config, parent_policy: Mapping[str,Any], profile: Mapping[str,Any], v259) -> Tuple[np.ndarray, Dict[str,Any]]:
    s=np.asarray(score,float); direct=v259.direct_topn(s,cfg.lines)
    if bool(parent_policy.get('validated')) and int(parent_policy.get('aggressive_lines',0)) >= cfg.lines:
        return direct, {'state':'validated_direct_topn','pool_expansions':[]}
    aggressive_n=int(parent_policy.get('aggressive_lines', max(3,round(.2*cfg.lines))))
    aggressive,core_detail=safe_aggressive_core(s,combos,aggressive_n,cfg,v259)
    order=np.lexsort((np.arange(len(s)),-s)); pool_rank=int(cfg.candidate_pool_rank); expansions=[]; attempts=[]
    while True:
        pool_idx=order[:pool_rank].astype(np.int32)
        idx,detail=_solve_milp(s,combos,pool_idx,aggressive,profile,cfg,v259)
        attempts.append({'pool_rank':int(pool_rank),**detail})
        if idx is not None:
            return idx, {'state':'assembly_rescue','pool_expansions':expansions,'final_pool_rank':int(pool_rank),'solver':detail,'attempts':attempts,'aggressive_core':core_detail}
        if pool_rank >= int(cfg.candidate_pool_max_rank): break
        old=pool_rank; pool_rank=min(int(cfg.candidate_pool_max_rank),max(pool_rank+1,int(math.ceil(pool_rank*cfg.candidate_pool_growth))))
        expansions.append({'from':int(old),'to':int(pool_rank)})
    if cfg.fallback_to_v259_greedy:
        # Preserve V259's proven feasibility contract rather than weakening assembly caps silently.
        idx,detail=v259.anti_collapse_selector(s,combos,_v259_cfg_from_v260(cfg,v259),parent_policy)
        return idx, {'state':'fallback_v259_anticollapse','pool_expansions':expansions,'attempts':attempts,'aggressive_core':core_detail,'fallback_detail':detail}
    raise RuntimeError('V260 no encontro portfolio factible y fallback deshabilitado')


def _v259_cfg_from_v260(cfg: V260Config, v259):
    # Conservative bridge used only if the MILP cannot solve. V259 supports full-universe emergency expansion.
    return v259.V259Config(
        history=cfg.history,v249_engine_path=cfg.v249_engine_path,v259_state_dir=cfg.v259_state_dir,
        v258_state_dir=cfg.v258_state_dir,v257_state_dir=cfg.v257_state_dir,lines=cfg.lines,quiet=cfg.quiet,
        coverage_pool_rank=cfg.candidate_pool_rank,coverage_pool_max_rank=cfg.candidate_pool_max_rank,
        coverage_pool_growth=cfg.candidate_pool_growth,cold_max_number_exposure=cfg.cold_max_number_exposure,
        cold_max_pair_exposure=cfg.cold_max_pair_exposure,top_ranking_rows=cfg.top_ranking_rows,prospective_register=False)


def _snapshot_path(cfg: V260Config,target:int)->Path:
    return Path(cfg.v260_state_dir)/'snapshots'/f'target_{int(target)}.joblib'


def _manifest_payload(s:Mapping[str,Any])->Dict[str,Any]:
    return {'schema':int(s['schema']),'engine':str(s['engine']),'target':int(s['target']),'history_last':int(s['history_last']),'history_sha256':str(s['history_sha256']),
            'parent_manifest':str(s.get('parent_manifest','')),'score_sha256':_array_sha256(np.asarray(s['parent_score'])),
            'direct_idx':np.asarray(s['direct_idx'],int).tolist(),'v260_idx':np.asarray(s['v260_idx'],int).tolist(),
            'policy':dict(s['policy']),'profile_sha256':str(s.get('profile_sha256',''))}


def save_snapshot(cfg:V260Config,s:Dict[str,Any])->Path:
    p=_snapshot_path(cfg,int(s['target'])); p.parent.mkdir(parents=True,exist_ok=True)
    x=dict(s); x['manifest_sha256']=hashlib.sha256(json.dumps(_manifest_payload(x),sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    tmp=p.with_suffix('.tmp'); joblib.dump(x,tmp,compress=1); os.replace(tmp,p); return p


def verify_snapshot(s:Mapping[str,Any])->None:
    if int(s.get('schema',-1))!=V260_SCHEMA: raise RuntimeError('V260 snapshot schema invalido')
    got=hashlib.sha256(json.dumps(_manifest_payload(s),sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    if not s.get('manifest_sha256') or got!=str(s['manifest_sha256']): raise RuntimeError('V260 snapshot manifest mismatch')


def _profile_sha(profile:Mapping[str,Any])->str:
    serial={'elite_rank':profile['elite_rank'],'pair_weights':{'-'.join(map(str,k)):v for k,v in profile.get('pair_weights',{}).items()},
            'triple_weights':{'-'.join(map(str,k)):v for k,v in profile.get('triple_weights',{}).items()}}
    return hashlib.sha256(json.dumps(serial,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _load_parent(cfg:V260Config,target:int,audit_sha:str,v259)->Tuple[np.ndarray,np.ndarray,Dict[str,Any],str,str]:
    p=Path(cfg.v259_state_dir)/'snapshots'/f'target_{target}.joblib'
    if p.exists():
        s=joblib.load(p); v259.verify_snapshot(s)
        if int(s.get('target',-1))!=target or str(s.get('history_sha256'))!=audit_sha: raise RuntimeError('V260 parent V259 target/historico mismatch')
        score=np.asarray(s['parent_score'],float); baseline=np.asarray(s['v259_idx'],np.int32); pol=dict(s.get('policy',{})); man=str(s.get('manifest_sha256',''))
        return score,baseline,pol,'v259',man
    # On-the-fly V259 reconstruction from V258/V257, preserving its policy contract.
    cfg259=_v259_cfg_from_v260(cfg,v259)
    parent,label=v259._load_parent(cfg259,target,audit_sha); score,_=v259._parent_score_and_idx(parent); pol=v259.parent_policy(parent,cfg259); pol['parent']=label
    baseline,_=v259.anti_collapse_selector(score,_CORE.ALL_COMBOS,cfg259,pol)
    return score,baseline,pol,'v259_reconstructed_'+label,str(parent.get('manifest_sha256',''))


_CORE=None

def render(core,idx:Sequence[int],score:np.ndarray,ranks:np.ndarray,source:str)->pd.DataFrame:
    rows=[]
    for pos,i in enumerate(np.asarray(idx,int),1):
        rows.append({'pos':pos,'combo_index':int(i),'combo':core.combo_str(tuple(map(int,core.ALL_COMBOS[i]))),'parent_rank':int(ranks[i]),'parent_score':float(score[i]),'source':source})
    return pd.DataFrame(rows)


def preregister(cfg:V260Config,audit,snap:Mapping[str,Any],port:pd.DataFrame,direct:pd.DataFrame)->Path:
    d=Path(str(cfg.prospective_registry_dir).replace('{target}',str(int(audit.target)))); d.mkdir(parents=True,exist_ok=True)
    p=d/f'target_{int(audit.target)}_V260_preregister.json'
    payload={'engine':V260_ENGINE,'target':int(audit.target),'history_last':int(audit.max_concurso),'history_sha256':str(audit.sha256),'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),
             'snapshot_manifest':str(snap['manifest_sha256']),'policy':dict(snap['policy']),'v260_metrics':dict(snap['v260_metrics']),'direct_metrics':dict(snap['direct_metrics']),
             'v260_portfolio':port['combo'].astype(str).tolist(),'direct_control':direct['combo'].astype(str).tolist(),
             'statement':'V260 assembly rescue is prospective model-risk control. Pair/triple motifs come only from the causal elite ranking and do not imply lottery predictability or guarantee 5/5.'}
    man=dict(payload); man.pop('created_at',None); payload['manifest_sha256']=hashlib.sha256(json.dumps(man,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    if p.exists():
        old=json.loads(p.read_text(encoding='utf-8'))
        if str(old.get('history_sha256'))!=str(audit.sha256): raise RuntimeError('V260 prereg FROZEN CONFLICT')
        return p
    tmp=p.with_suffix('.tmp'); tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding='utf-8'); os.replace(tmp,p); return p


def parser()->argparse.ArgumentParser:
    ap=argparse.ArgumentParser(description='Chispazo V260 Evidence-Shrunk Assembly Rescue')
    ap.add_argument('--config',default=None); ap.add_argument('--history',default=None); ap.add_argument('--target',type=int,default=None); ap.add_argument('--expected-last',type=int,default=None); ap.add_argument('--quiet',action='store_true'); return ap


def main()->int:
    global _CORE
    args=parser().parse_args(); cfg=load_config(Path(args.config) if args.config else None); d=asdict(cfg)
    if args.history is not None:d['history']=args.history
    if args.target is not None:d['target']=args.target
    if args.expected_last is not None:d['expected_last']=args.expected_last
    if args.quiet:d['quiet']=True
    cfg=V260Config(**d); validate_config(cfg)
    v259=_load_module(Path(cfg.v259_engine_path),'chispazo_v259_parent_v260')
    core=_load_module(Path(cfg.v249_engine_path),'chispazo_v249_parent_v260'); _CORE=core
    hp=Path(cfg.history)
    if not hp.exists(): print(f'ERROR: no existe {hp}',file=sys.stderr); return 2
    df=core.read_history(hp); audit=core.audit_history(hp,df,cfg.target,cfg.expected_last)
    print('\n=== AUDIT ==='); print(json.dumps(asdict(audit),indent=2,ensure_ascii=False))
    if audit.status!='PASS': print('ABORTADO por auditoria',file=sys.stderr); return 3
    cfg=V260Config(**{**asdict(cfg),'target':int(audit.target),'expected_last':int(audit.max_concurso)})

    score,baseline_idx,pol,parent_label,parent_manifest=_load_parent(cfg,int(audit.target),str(audit.sha256),v259)
    if len(score)!=UNIVERSE_SIZE: raise RuntimeError('V260 parent score no cubre 98,280 combinaciones')
    ranks=v259.tie_worst_rank_vector(score); direct_idx=v259.direct_topn(score,cfg.lines)
    profile=assembly_profile(score,core.ALL_COMBOS,cfg,v259)
    progress(cfg,f"V260 parent={parent_label} validated={pol.get('validated')} aggressive={pol.get('aggressive_lines')}/{cfg.lines} motifs={profile['admitted_pairs']}P/{profile['admitted_triples']}T")
    v260_idx,selector=assembly_selector(score,core.ALL_COMBOS,cfg,pol,profile,v259)

    direct_met=assembly_metrics(direct_idx,core.ALL_COMBOS,profile,ranks,v259)
    base_met=assembly_metrics(baseline_idx,core.ALL_COMBOS,profile,ranks,v259)
    v260_met=assembly_metrics(v260_idx,core.ALL_COMBOS,profile,ranks,v259)
    direct=render(core,direct_idx,score,ranks,'parent_direct_topn_control')
    base=render(core,baseline_idx,score,ranks,'v259_control')
    port=render(core,v260_idx,score,ranks,'v260_assembly_rescue')
    port['is_direct_top30']=port['combo_index'].astype(int).isin(set(map(int,direct_idx))).astype(int)
    port['is_v259_control']=port['combo_index'].astype(int).isin(set(map(int,baseline_idx))).astype(int)

    psha=_profile_sha(profile)
    snap={'schema':V260_SCHEMA,'engine':V260_ENGINE,'target':int(audit.target),'history_last':int(audit.max_concurso),'history_sha256':str(audit.sha256),'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),
          'parent_label':parent_label,'parent_manifest':parent_manifest,'parent_score':score.astype(np.float32),'direct_idx':direct_idx,'v259_idx':baseline_idx,'v260_idx':v260_idx,
          'policy':pol,'selector':selector,'profile_sha256':psha,'direct_metrics':direct_met,'v259_metrics':base_met,'v260_metrics':v260_met}
    sp=save_snapshot(cfg,snap); loaded=joblib.load(sp); verify_snapshot(loaded)
    out=Path(str(cfg.out_dir).replace('{target}',str(int(audit.target)))); out.mkdir(parents=True,exist_ok=True)
    port.to_csv(out/f'v260_ASSEMBLY_RESCUE_{cfg.lines}_target_{audit.target}.csv',index=False)
    base.to_csv(out/f'v260_CONTROL_V259_{cfg.lines}_target_{audit.target}.csv',index=False)
    direct.to_csv(out/f'v260_CONTROL_DIRECT_{cfg.lines}_target_{audit.target}.csv',index=False)
    # Export admitted motifs for auditability.
    pd.DataFrame([{'pair':'-'.join(map(str,k)),'weight':v} for k,v in profile['pair_weights'].items()]).to_csv(out/'v260_admitted_pairs.csv',index=False)
    pd.DataFrame([{'triple':'-'.join(map(str,k)),'weight':v} for k,v in profile['triple_weights'].items()]).to_csv(out/'v260_admitted_triples.csv',index=False)
    order=np.lexsort((np.arange(len(score)),-score)); topn=min(len(order),max(cfg.lines,int(cfg.top_ranking_rows)))
    pd.DataFrame({'rank':np.arange(1,topn+1),'combo_index':order[:topn],'combo':[core.combo_str(tuple(map(int,core.ALL_COMBOS[i]))) for i in order[:topn]],'parent_score':score[order[:topn]]}).to_csv(out/f'v260_parent_top{topn}_ranking.csv',index=False)
    runtime={'target':int(audit.target),'history_last':int(audit.max_concurso),'parent':parent_label,'policy':pol,'assembly_profile':{k:v for k,v in profile.items() if k not in ('pair_weights','triple_weights')},
             'direct_metrics':direct_met,'v259_metrics':base_met,'v260_metrics':v260_met,'selector':selector,
             'statement':'V260 repairs assembly fragmentation only under unvalidated edge. It never uses the realized target and reverts to DIRECT Top-N when the prospective parent gate is mature.'}
    (out/'v260_runtime.json').write_text(json.dumps(runtime,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    preg=preregister(cfg,audit,loaded,port,direct) if cfg.prospective_register else None
    print('\n=== V259 CONTROL METRICS ==='); print(json.dumps(base_met,indent=2,ensure_ascii=False))
    print('\n=== V260 METRICS ==='); print(json.dumps(v260_met,indent=2,ensure_ascii=False))
    print('\n=== V260 SELECTOR ==='); print(json.dumps(selector,indent=2,ensure_ascii=False))
    print('\n=== V260 TOP30 ==='); print(port.to_string(index=False))
    print('Snapshot:',sp); print('Preregister:',preg); print('Outputs:',out)
    return 0

if __name__=='__main__': raise SystemExit(main())
