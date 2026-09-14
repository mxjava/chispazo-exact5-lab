#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
CHISPAZO V261 — LEXICOGRAPHIC EXACT5 REGRET ASSEMBLY
=====================================================

V261 fixes four weaknesses of V260:
1) Exact5 quality and assembly are no longer mixed in one weighted objective.
2) Pair/triple evidence uses the Kish effective sample size of rank weights.
3) Motif strength is stability-selected across several elite windows and keeps
   its absolute strength; weak residual lift cannot receive a fixed 38% mass.
4) Number coverage is soft and probability-aware instead of forcing every number
   to appear twice regardless of parent ranking quality.

Selection is lexicographic:
  Stage 1: maximize parent-rank exact-quality subject to anti-collapse caps.
  Stage 2: maximize stable number/pair/triple assembly, subject to keeping at
           least (1 - stage2_regret_budget) of Stage-1 exact-quality.

The structural caps themselves are also regret-bounded versus DIRECT Top30.
If a strict cap tier costs too much quality, V261 relaxes it deterministically.
This creates an explicit Pareto frontier instead of an arbitrary fixed blend.
"""

import argparse, hashlib, importlib.util, itertools, json, math, os, sys, time, tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.stats import binom
from scipy.sparse import coo_matrix

V261_SCHEMA = 261
V261_ENGINE = "CHISPAZO_V261_LEXICOGRAPHIC_REGRET"
UNIVERSE_SIZE = math.comb(28, 5)
PAIR_COUNT = math.comb(28, 2)
TRIPLE_COUNT = math.comb(28, 3)

@dataclass(frozen=True)
class V261Config:
    history: str = r"D:\melate\Chispazo.csv"
    v249_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V249_COVERAGE_ANTISAT_EXACT5.py"
    v259_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V259_CALIBRATED_ANTICOLLAPSE.py"
    v260_engine_path: str = r"D:\melate\melate_new\CHISPAZO_V260_ASSEMBLY_RESCUE.py"
    v259_state_dir: str = r"D:\melate\state_v259"
    v258_state_dir: str = r"D:\melate\state_v258"
    v257_state_dir: str = r"D:\melate\state_v257"
    v260_state_dir: str = r"D:\melate\state_v260"
    v261_state_dir: str = r"D:\melate\state_v261"
    out_dir: str = r"D:\melate\resultados_v261_{target}"
    prospective_registry_dir: str = r"D:\melate\preregistros_v261"
    target: Optional[int] = None
    expected_last: Optional[int] = None
    lines: int = 30
    quiet: bool = False

    candidate_pool_rank: int = 200
    candidate_pool_max_rank: int = 5000
    candidate_pool_growth: float = 2.5

    # Stage-1 structure is selected from a deterministic relaxation frontier.
    structural_quality_floor: float = 0.995
    strict_max_number_exposure: int = 9
    strict_max_pair_exposure: int = 4
    strict_max_triple_exposure: int = 2
    min_direct_overlap: int = 6

    # Stage-2 assembly may spend only this fraction of Stage-1 exact-quality.
    stage2_regret_budget: float = 0.0025

    motif_windows: str = "500,1000,2500,5000"
    motif_rank_temperature: float = 900.0
    motif_prior_strength: float = 300.0
    motif_min_lift: float = 1.05
    motif_max_lift: float = 2.50
    motif_min_persistence: float = 0.75
    motif_fwer_alpha: float = 0.05
    motif_top_pairs: int = 96
    motif_top_triples: int = 160

    # Secondary objective block caps; actual block mass is multiplied by measured
    # residual signal strength, so weak motifs automatically shrink toward zero.
    number_coverage_mass: float = 0.30
    pair_coverage_mass_cap: float = 0.42
    triple_coverage_mass_cap: float = 0.28
    second_number_coverage_discount: float = 0.45

    milp_time_limit_seconds: float = 30.0
    milp_mip_rel_gap: float = 0.0
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


def load_config(path: Optional[Path]) -> V261Config:
    base = asdict(V261Config())
    if path is not None:
        with Path(path).open('rb') as fh: vals = _flatten_toml(tomllib.load(fh))
        bad = sorted(set(vals) - set(base))
        if bad: raise ValueError(f"Config V261 contiene claves desconocidas: {bad}")
        base.update(vals)
    cfg = V261Config(**base); validate_config(cfg); return cfg


def motif_windows(cfg: V261Config) -> Tuple[int, ...]:
    xs = tuple(sorted(set(int(x.strip()) for x in str(cfg.motif_windows).split(',') if x.strip())))
    if not xs or min(xs) < cfg.lines or max(xs) > UNIVERSE_SIZE:
        raise ValueError('motif_windows invalidas')
    return xs


def validate_config(cfg: V261Config) -> None:
    checks = [
        (1 <= cfg.lines <= 200, 'lines invalido'),
        (cfg.candidate_pool_rank >= cfg.lines, 'candidate_pool_rank invalido'),
        (cfg.candidate_pool_max_rank >= cfg.candidate_pool_rank and cfg.candidate_pool_max_rank <= UNIVERSE_SIZE, 'candidate_pool_max_rank invalido'),
        (cfg.candidate_pool_growth > 1, 'candidate_pool_growth invalido'),
        (0.90 <= cfg.structural_quality_floor <= 1.0, 'structural_quality_floor invalido'),
        (0 <= cfg.stage2_regret_budget <= 0.05, 'stage2_regret_budget invalido'),
        (1 <= cfg.strict_max_number_exposure <= cfg.lines, 'strict_max_number_exposure invalido'),
        (1 <= cfg.strict_max_pair_exposure <= cfg.lines, 'strict_max_pair_exposure invalido'),
        (1 <= cfg.strict_max_triple_exposure <= cfg.lines, 'strict_max_triple_exposure invalido'),
        (0 <= cfg.min_direct_overlap <= cfg.lines, 'min_direct_overlap invalido'),
        (cfg.motif_rank_temperature > 0, 'motif_rank_temperature invalido'),
        (cfg.motif_prior_strength >= 0, 'motif_prior_strength invalido'),
        (1 <= cfg.motif_min_lift <= cfg.motif_max_lift, 'motif lift invalido'),
        (0 <= cfg.motif_min_persistence <= 1, 'motif_min_persistence invalido'),
        (0 < cfg.motif_fwer_alpha <= 0.5, 'motif_fwer_alpha invalido'),
        (0 <= cfg.motif_top_pairs <= PAIR_COUNT, 'motif_top_pairs invalido'),
        (0 <= cfg.motif_top_triples <= TRIPLE_COUNT, 'motif_top_triples invalido'),
        (cfg.milp_time_limit_seconds > 0, 'milp_time_limit_seconds invalido'),
    ]
    motif_windows(cfg)
    bad = [m for ok, m in checks if not ok]
    if bad: raise ValueError('Configuracion V261 invalida: ' + '; '.join(bad))


def _load_module(path: Path, name: str):
    p = Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    spec = importlib.util.spec_from_file_location(name, p)
    if spec is None or spec.loader is None: raise ImportError(p)
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


def progress(cfg: V261Config, msg: str) -> None:
    if not cfg.quiet: print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _array_sha256(a: np.ndarray) -> str:
    x = np.ascontiguousarray(a); h = hashlib.sha256(); h.update(str(x.dtype).encode()); h.update(str(tuple(x.shape)).encode()); h.update(x.tobytes()); return h.hexdigest()


def _rank_weights(n: int, temperature: float) -> np.ndarray:
    r = np.arange(n, dtype=float)
    w = np.exp(-r / float(temperature)); w /= max(1e-15, float(w.sum()))
    return w


def kish_ess(w: np.ndarray) -> float:
    x = np.asarray(w, float); z = float(np.sum(x*x))
    return float(1.0 / z) if z > 0 else 0.0


def _posterior_residual(obs: Mapping[Tuple[int, ...], float], count: int, ess: float,
                        prior: float, min_lift: float, max_lift: float, fwer_alpha: float) -> Dict[Tuple[int, ...], float]:
    """Residual lift with conservative family-wise admission.

    We convert rank weights to Kish ESS, then test motif incidence against the
    exact uniform 5/28 incidence q0=10/count using an effective Binomial tail.
    This is deliberately conservative for sparse triples; normal z tails are
    materially anti-conservative when expected triple counts are only a few.
    """
    null_mass = 1.0 / float(count)
    q0 = 10.0 / float(count)
    n_eff = max(1, int(math.floor(float(ess))))
    alpha_each = float(fwer_alpha) / float(count)
    den = float(ess + prior)
    out: Dict[Tuple[int, ...], float] = {}
    for k, mass in obs.items():
        qobs = min(1.0, max(0.0, 10.0 * float(mass)))
        k_eff = int(math.ceil(qobs * n_eff - 1e-12))
        p_tail = float(binom.sf(k_eff - 1, n_eff, q0)) if k_eff > 0 else 1.0
        if p_tail > alpha_each:
            continue
        post = (ess * float(mass) + prior * null_mass) / max(1e-15, den)
        lift = float(np.clip(post / null_mass, 1.0/max_lift, max_lift))
        if lift >= min_lift:
            # Preserve absolute evidence: stronger-than-threshold tails receive more weight.
            sig = min(1.0, max(0.0, math.log10(max(alpha_each,1e-300) / max(p_tail,1e-300)) + 1.0))
            out[k] = (lift - 1.0) * sig
    return out


def robust_motif_profile(score: np.ndarray, combos: np.ndarray, cfg: V261Config) -> Dict[str, Any]:
    s = np.asarray(score, float); order = np.lexsort((np.arange(len(s)), -s))
    windows = motif_windows(cfg)
    pair_by_window=[]; triple_by_window=[]; details=[]
    for n0 in windows:
        n=min(n0,len(order)); elite=order[:n]; rw=_rank_weights(n,cfg.motif_rank_temperature); ess=kish_ess(rw)
        po: Dict[Tuple[int,int],float]={}; to: Dict[Tuple[int,int,int],float]={}
        for j,i in enumerate(elite):
            c=tuple(map(int,combos[int(i)])); w=float(rw[j])
            for p in itertools.combinations(c,2): po[p]=po.get(p,0.0)+w/10.0
            for t in itertools.combinations(c,3): to[t]=to.get(t,0.0)+w/10.0
        pr=_posterior_residual(po,PAIR_COUNT,ess,cfg.motif_prior_strength,cfg.motif_min_lift,cfg.motif_max_lift,cfg.motif_fwer_alpha)
        tr=_posterior_residual(to,TRIPLE_COUNT,ess,cfg.motif_prior_strength,cfg.motif_min_lift,cfg.motif_max_lift,cfg.motif_fwer_alpha)
        pair_by_window.append(pr); triple_by_window.append(tr)
        details.append({'window':int(n),'kish_ess':float(ess),'pair_signal_count':len(pr),'triple_signal_count':len(tr)})

    def stable(ds, topk):
        keys=set().union(*(d.keys() for d in ds)); W=max(1,len(ds)); out={}
        for k in keys:
            vals=np.array([float(d.get(k,0.0)) for d in ds],float)
            pers=float(np.mean(vals>0))
            if pers + 1e-12 < cfg.motif_min_persistence: continue
            nz=vals[vals>0]
            residual=float(np.median(nz)) if len(nz) else 0.0
            out[k]=residual*pers
        ranked=sorted(out.items(),key=lambda kv:(-kv[1],kv[0]))[:int(topk)]
        return dict(ranked)

    pw=stable(pair_by_window,cfg.motif_top_pairs); tw=stable(triple_by_window,cfg.motif_top_triples)
    max_res=max(1e-12,cfg.motif_max_lift-1.0)
    pair_strength=float(np.clip(np.mean(list(pw.values())[:20])/max_res if pw else 0.0,0,1))
    triple_strength=float(np.clip(np.mean(list(tw.values())[:20])/max_res if tw else 0.0,0,1))

    # Rank-weighted number marginal for soft first/second coverage rewards.
    n=max(windows); elite=order[:n]; rw=_rank_weights(n,cfg.motif_rank_temperature)
    nm=np.zeros(29,float)
    for j,i in enumerate(elite):
        for x in combos[int(i)]: nm[int(x)]+=float(rw[j])
    nw={i:float(math.sqrt(max(1e-15,nm[i]))) for i in range(1,29)}
    z=sum(nw.values()); nw={k:v/z for k,v in nw.items()}
    return {'windows':windows,'window_detail':details,'pair_weights':pw,'triple_weights':tw,
            'pair_strength':pair_strength,'triple_strength':triple_strength,'number_weights':nw,
            'admitted_pairs':len(pw),'admitted_triples':len(tw)}


def exact_quality_vector(score: np.ndarray, ranks: np.ndarray, denominator_rank: int) -> np.ndarray:
    """Affine-normalized parent score over the candidate head.

    For a fixed portfolio cardinality, maximizing this vector is exactly equivalent
    to maximizing the original parent score because q=a*score+b with a>0 inside
    the candidate head. This preserves V254's Exact5 objective ordering while making
    a dimensionless regret ratio possible.
    """
    s=np.asarray(score,float); r=np.asarray(ranks,int); k=min(max(2,int(denominator_rank)),len(s))
    order=np.lexsort((np.arange(len(s)),-s)); floor=float(s[order[k-1]]); top=float(s[order[0]])
    if not np.isfinite(top-floor) or abs(top-floor)<=1e-15:
        rr=np.maximum(1,r.astype(float)); den=max(math.log(k),1e-12); return np.clip(1.0-np.log(rr)/den,0.0,1.0)
    return np.clip((s-floor)/(top-floor),0.0,1.0)


def exposure_metrics(indices: Sequence[int], combos: np.ndarray, ranks: np.ndarray,
                     profile: Optional[Mapping[str,Any]]=None) -> Dict[str,Any]:
    idx=np.asarray(indices,int); ne=np.zeros(29,int); pe={}; te={}; partners={n:set() for n in range(1,29)}
    for i in idx:
        c=tuple(map(int,combos[int(i)]))
        for n in c: ne[n]+=1
        for p in itertools.combinations(c,2): pe[p]=pe.get(p,0)+1; partners[p[0]].add(p[1]); partners[p[1]].add(p[0])
        for t in itertools.combinations(c,3): te[t]=te.get(t,0)+1
    m={'lines':len(idx),'unique_numbers':int(np.sum(ne[1:]>0)),'min_number_exposure':int(np.min(ne[1:])),'max_number_exposure':int(np.max(ne[1:])),
       'unique_pairs':len(pe),'unique_triples':len(te),'max_pair_exposure':max(pe.values()) if pe else 0,'max_triple_exposure':max(te.values()) if te else 0,
       'min_number_distinct_partners':min((len(v) for v in partners.values()),default=0),'median_parent_rank':float(np.median(ranks[idx])),'worst_parent_rank':int(np.max(ranks[idx]))}
    if profile:
        pden=max(1e-15,float(sum(profile['pair_weights'].values())))
        tden=max(1e-15,float(sum(profile['triple_weights'].values())))
        m['weighted_pair_coverage']=float(sum(v for k,v in profile['pair_weights'].items() if pe.get(k,0)>0)/pden) if profile['pair_weights'] else 0.0
        m['weighted_triple_coverage']=float(sum(v for k,v in profile['triple_weights'].items() if te.get(k,0)>0)/tden) if profile['triple_weights'] else 0.0
    return m


def _incidence(pool_idx: np.ndarray, combos: np.ndarray):
    nums={n:[] for n in range(1,29)}; pairs={}; triples={}
    for j,i in enumerate(pool_idx):
        c=tuple(map(int,combos[int(i)]))
        for n in c: nums[n].append(j)
        for p in itertools.combinations(c,2): pairs.setdefault(p,[]).append(j)
        for t in itertools.combinations(c,3): triples.setdefault(t,[]).append(j)
    return nums,pairs,triples


def _base_constraints(pool_idx: np.ndarray, combos: np.ndarray, lines: int, direct_set: set[int], min_direct_overlap: int,
                      caps: Tuple[int,int,int], nvar: int, quality: Optional[np.ndarray]=None, quality_floor: Optional[float]=None,
                      aux: Optional[Dict[str,Any]]=None):
    rows=[]; cols=[]; vals=[]; lb=[]; ub=[]
    def add(entries: Iterable[Tuple[int,float]], lo: float, hi: float):
        rr=len(lb)
        for c,v in entries: rows.append(rr); cols.append(int(c)); vals.append(float(v))
        lb.append(float(lo)); ub.append(float(hi))
    K=len(pool_idx); nums,pairs,triples=_incidence(pool_idx,combos)
    add(((j,1.0) for j in range(K)),lines,lines)
    direct_js=[j for j,i in enumerate(pool_idx) if int(i) in direct_set]
    if min_direct_overlap>0: add(((j,1.0) for j in direct_js),min_direct_overlap,np.inf)
    maxn,maxp,maxt=caps
    for n,js in nums.items(): add(((j,1.0) for j in js),-np.inf,maxn)
    for p,js in pairs.items(): add(((j,1.0) for j in js),-np.inf,maxp)
    for t,js in triples.items(): add(((j,1.0) for j in js),-np.inf,maxt)
    if quality is not None and quality_floor is not None:
        add(((j,float(quality[j])) for j in range(K)),float(quality_floor),np.inf)
    if aux:
        # First/second number coverage binaries.
        for n,y in aux.get('num1',{}).items(): add([(y,1.0)]+[(j,-1.0) for j in nums[n]],-np.inf,0.0)
        for n,y in aux.get('num2',{}).items(): add([(y,2.0)]+[(j,-1.0) for j in nums[n]],-np.inf,0.0)
        for p,y in aux.get('pair',{}).items(): add([(y,1.0)]+[(j,-1.0) for j in pairs.get(p,[])],-np.inf,0.0)
        for t,y in aux.get('triple',{}).items(): add([(y,1.0)]+[(j,-1.0) for j in triples.get(t,[])],-np.inf,0.0)
    A=coo_matrix((vals,(rows,cols)),shape=(len(lb),nvar)).tocsr()
    return LinearConstraint(A,np.array(lb,float),np.array(ub,float)),len(lb)


def _milp(c: np.ndarray, constraint: LinearConstraint, time_limit: float, gap: float):
    n=len(c); return milp(c=c,integrality=np.ones(n,dtype=np.int8),bounds=Bounds(np.zeros(n),np.ones(n)),constraints=constraint,
                          options={'time_limit':float(time_limit),'mip_rel_gap':float(gap),'presolve':True})


def _cap_tiers(cfg: V261Config) -> Tuple[Tuple[int,int,int],...]:
    a=(cfg.strict_max_number_exposure,cfg.strict_max_pair_exposure,cfg.strict_max_triple_exposure)
    # Never remove anti-collapse entirely. The last tier is a controlled ceiling,
    # not DIRECT-without-guards. If the quality floor is missed, V261 reports it.
    tiers=[a,(min(cfg.lines,a[0]+1),a[1],a[2]),(min(cfg.lines,a[0]+2),a[1],a[2]),
           (min(cfg.lines,a[0]+3),min(cfg.lines,a[1]+1),min(cfg.lines,a[2]+1))]
    out=[]
    for x in tiers:
        if x not in out: out.append(x)
    return tuple(out)


def lexicographic_selector(score: np.ndarray, combos: np.ndarray, cfg: V261Config, v259, profile: Mapping[str,Any]) -> Tuple[np.ndarray,Dict[str,Any]]:
    s=np.asarray(score,float); ranks=v259.tie_worst_rank_vector(s); order=np.lexsort((np.arange(len(s)),-s)); direct=order[:cfg.lines].astype(np.int32)
    direct_set=set(map(int,direct)); q_all=exact_quality_vector(s,ranks,cfg.candidate_pool_max_rank)
    direct_q=float(np.sum(q_all[direct])); pool_rank=cfg.candidate_pool_rank; attempts=[]
    chosen_stage1=None; stage1_info=None; chosen_pool=None; chosen_q=None; chosen_caps=None
    best_fallback=None
    while True:
        pool=order[:pool_rank].astype(np.int32); q=q_all[pool]; K=len(pool)
        for caps in _cap_tiers(cfg):
            con,nc=_base_constraints(pool,combos,cfg.lines,direct_set,cfg.min_direct_overlap,caps,K)
            c=-q.copy()
            # deterministic infinitesimal preference for smaller parent rank/index
            c += 1e-10*np.arange(K,dtype=float)/max(1,K)
            try: res=_milp(c,con,cfg.milp_time_limit_seconds,cfg.milp_mip_rel_gap)
            except Exception as e:
                attempts.append({'pool_rank':pool_rank,'caps':caps,'state':'exception','error':repr(e)}); continue
            if res.x is None:
                attempts.append({'pool_rank':pool_rank,'caps':caps,'state':'no_solution','status':int(res.status)}); continue
            ix=np.where(np.asarray(res.x)>0.5)[0]
            if len(ix)!=cfg.lines:
                attempts.append({'pool_rank':pool_rank,'caps':caps,'state':'bad_cardinality','chosen':len(ix)}); continue
            idx=pool[ix]; qsum=float(np.sum(q[ix])); ratio=qsum/max(1e-15,direct_q)
            attempts.append({'pool_rank':pool_rank,'caps':caps,'state':'ok','quality':qsum,'direct_quality_ratio':ratio,'status':int(res.status)})
            cand=(ratio,idx.astype(np.int32),{'quality':qsum,'direct_quality':direct_q,'direct_quality_ratio':ratio,'status':int(res.status),'constraints':nc,'quality_floor_met':bool(ratio+1e-12>=cfg.structural_quality_floor)},pool,q,caps)
            if best_fallback is None or ratio > best_fallback[0]: best_fallback=cand
            if ratio + 1e-12 >= cfg.structural_quality_floor:
                _,chosen_stage1,stage1_info,chosen_pool,chosen_q,chosen_caps=cand; break
        if chosen_stage1 is not None: break
        if pool_rank>=cfg.candidate_pool_max_rank:
            if chosen_stage1 is None and best_fallback is not None:
                _,chosen_stage1,stage1_info,chosen_pool,chosen_q,chosen_caps=best_fallback
            break
        pool_rank=min(cfg.candidate_pool_max_rank,max(pool_rank+1,int(math.ceil(pool_rank*cfg.candidate_pool_growth))))
    if chosen_stage1 is None: raise RuntimeError('V261 Stage1 no encontro solucion factible')

    pool=chosen_pool; q=chosen_q; K=len(pool); stage1_q=float(stage1_info['quality'])
    pw=dict(profile.get('pair_weights',{})); tw=dict(profile.get('triple_weights',{})); nw=dict(profile.get('number_weights',{}))
    P=list(pw); T=list(tw)
    off=K; num1={n:off+i for i,n in enumerate(range(1,29))}; off+=28
    num2={n:off+i for i,n in enumerate(range(1,29))}; off+=28
    pair_vars={p:off+i for i,p in enumerate(P)}; off+=len(P)
    tri_vars={t:off+i for i,t in enumerate(T)}; off+=len(T); nvar=off
    aux={'num1':num1,'num2':num2,'pair':pair_vars,'triple':tri_vars}
    qfloor=stage1_q*(1.0-cfg.stage2_regret_budget)
    con2,nc2=_base_constraints(pool,combos,cfg.lines,direct_set,cfg.min_direct_overlap,chosen_caps,nvar,quality=q,quality_floor=qfloor,aux=aux)
    c=np.zeros(nvar,float)
    # Exact quality only as tiny tie-break; the hard qfloor carries the guarantee.
    c[:K]=-1e-6*q/max(1.0,float(cfg.lines))
    nvals=np.array([nw.get(n,0.0) for n in range(1,29)],float); nvals/=max(1e-15,nvals.sum())
    for i,n in enumerate(range(1,29)):
        c[num1[n]]=-cfg.number_coverage_mass*nvals[i]
        c[num2[n]]=-cfg.number_coverage_mass*cfg.second_number_coverage_discount*nvals[i]
    if P:
        vals=np.array([pw[p] for p in P],float); vals/=max(1e-15,vals.sum())
        mass=cfg.pair_coverage_mass_cap*float(profile.get('pair_strength',0.0))
        for p,v in zip(P,vals): c[pair_vars[p]]=-mass*float(v)
    if T:
        vals=np.array([tw[t] for t in T],float); vals/=max(1e-15,vals.sum())
        mass=cfg.triple_coverage_mass_cap*float(profile.get('triple_strength',0.0))
        for t,v in zip(T,vals): c[tri_vars[t]]=-mass*float(v)
    res2=_milp(c,con2,cfg.milp_time_limit_seconds,cfg.milp_mip_rel_gap)
    if res2.x is None:
        idx=chosen_stage1
        stage2={'state':'fallback_stage1','status':int(res2.status),'quality_floor':qfloor}
    else:
        ix=np.where(np.asarray(res2.x[:K])>0.5)[0]
        if len(ix)!=cfg.lines: raise RuntimeError('V261 Stage2 cardinalidad invalida')
        idx=pool[ix].astype(np.int32); q2=float(np.sum(q[ix]))
        stage2={'state':'optimal' if int(res2.status)==0 else 'feasible','status':int(res2.status),'objective':float(res2.fun),'quality':q2,
                'stage1_quality_ratio':q2/max(1e-15,stage1_q),'direct_quality_ratio':q2/max(1e-15,direct_q),'quality_floor':qfloor,'constraints':nc2,'variables':nvar}
    idx=idx[np.lexsort((idx,-s[idx]))]
    return idx,{'state':'lexicographic_regret','final_pool_rank':int(pool_rank),'caps':{'number':chosen_caps[0],'pair':chosen_caps[1],'triple':chosen_caps[2]},
                'stage1':stage1_info,'stage2':stage2,'attempts':attempts,'direct_overlap':int(len(set(map(int,idx))&direct_set))}


def _snapshot_path(cfg: V261Config,target:int)->Path:
    return Path(cfg.v261_state_dir)/'snapshots'/f'target_{int(target)}.joblib'


def _manifest_payload(s:Mapping[str,Any])->Dict[str,Any]:
    return {'schema':int(s['schema']),'engine':str(s['engine']),'target':int(s['target']),'history_last':int(s['history_last']),'history_sha256':str(s['history_sha256']),
            'parent_manifest':str(s.get('parent_manifest','')),'score_sha256':_array_sha256(np.asarray(s['parent_score'])),
            'direct_idx':np.asarray(s['direct_idx'],int).tolist(),'v259_idx':np.asarray(s['v259_idx'],int).tolist(),'v261_idx':np.asarray(s['v261_idx'],int).tolist(),
            'selector':dict(s['selector']),'profile_sha256':str(s.get('profile_sha256',''))}


def save_snapshot(cfg:V261Config,s:Dict[str,Any])->Path:
    p=_snapshot_path(cfg,int(s['target'])); p.parent.mkdir(parents=True,exist_ok=True)
    x=dict(s); x['manifest_sha256']=hashlib.sha256(json.dumps(_manifest_payload(x),sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    tmp=p.with_suffix('.tmp'); joblib.dump(x,tmp,compress=1); os.replace(tmp,p); return p


def verify_snapshot(s:Mapping[str,Any])->None:
    if int(s.get('schema',-1))!=V261_SCHEMA: raise RuntimeError('V261 snapshot schema invalido')
    got=hashlib.sha256(json.dumps(_manifest_payload(s),sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    if got!=str(s.get('manifest_sha256','')): raise RuntimeError('V261 snapshot manifest mismatch')


def _profile_sha(profile:Mapping[str,Any])->str:
    serial={'windows':list(profile['windows']),'pair_weights':{'-'.join(map(str,k)):v for k,v in profile['pair_weights'].items()},
            'triple_weights':{'-'.join(map(str,k)):v for k,v in profile['triple_weights'].items()},'pair_strength':profile['pair_strength'],'triple_strength':profile['triple_strength']}
    return hashlib.sha256(json.dumps(serial,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def render(core,idx:Sequence[int],score:np.ndarray,ranks:np.ndarray,source:str)->pd.DataFrame:
    return pd.DataFrame([{'pos':p,'combo_index':int(i),'combo':core.combo_str(tuple(map(int,core.ALL_COMBOS[int(i)]))),
                          'parent_rank':int(ranks[int(i)]),'parent_score':float(score[int(i)]),'source':source}
                         for p,i in enumerate(np.asarray(idx,int),1)])


def preregister(cfg:V261Config,audit,snap:Mapping[str,Any],port:pd.DataFrame,control:pd.DataFrame,direct:pd.DataFrame)->Path:
    d=Path(str(cfg.prospective_registry_dir).replace('{target}',str(int(audit.target)))); d.mkdir(parents=True,exist_ok=True)
    p=d/f'target_{int(audit.target)}_V261_preregister.json'
    payload={'engine':V261_ENGINE,'target':int(audit.target),'history_last':int(audit.max_concurso),'history_sha256':str(audit.sha256),'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),
             'snapshot_manifest':str(snap['manifest_sha256']),'v261_portfolio':port['combo'].astype(str).tolist(),'v259_control':control['combo'].astype(str).tolist(),
             'direct_control':direct['combo'].astype(str).tolist(),'selector':dict(snap['selector']),
             'statement':'Frozen before target resolution. V261 lexicographically protects Exact5 rank-quality before optimizing assembly. No 5/5 guarantee.'}
    man=dict(payload); man.pop('created_at',None); payload['manifest_sha256']=hashlib.sha256(json.dumps(man,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    if p.exists():
        old=json.loads(p.read_text(encoding='utf-8'))
        if str(old.get('history_sha256'))!=str(audit.sha256): raise RuntimeError('V261 prereg FROZEN CONFLICT')
        return p
    tmp=p.with_suffix('.tmp'); tmp.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding='utf-8'); os.replace(tmp,p); return p


def parser()->argparse.ArgumentParser:
    ap=argparse.ArgumentParser(description='Chispazo V261 Lexicographic Exact5 Regret Assembly')
    ap.add_argument('--config',default=None); ap.add_argument('--history',default=None); ap.add_argument('--target',type=int,default=None); ap.add_argument('--expected-last',type=int,default=None); ap.add_argument('--quiet',action='store_true'); return ap


def main()->int:
    args=parser().parse_args(); cfg=load_config(Path(args.config) if args.config else None); d=asdict(cfg)
    if args.history is not None:d['history']=args.history
    if args.target is not None:d['target']=args.target
    if args.expected_last is not None:d['expected_last']=args.expected_last
    if args.quiet:d['quiet']=True
    cfg=V261Config(**d); validate_config(cfg)
    v259=_load_module(Path(cfg.v259_engine_path),'chispazo_v259_parent_v261')
    v260=_load_module(Path(cfg.v260_engine_path),'chispazo_v260_parent_v261')
    core=_load_module(Path(cfg.v249_engine_path),'chispazo_v249_parent_v261'); v260._CORE=core
    hp=Path(cfg.history)
    if not hp.exists(): print(f'ERROR: no existe {hp}',file=sys.stderr); return 2
    df=core.read_history(hp); audit=core.audit_history(hp,df,cfg.target,cfg.expected_last)
    print('\n=== AUDIT ==='); print(json.dumps(asdict(audit),indent=2,ensure_ascii=False))
    if audit.status!='PASS': print('ABORTADO por auditoria',file=sys.stderr); return 3
    cfg=V261Config(**{**asdict(cfg),'target':int(audit.target),'expected_last':int(audit.max_concurso)})

    # Reuse V260's causal parent loader, not its selector/objective.
    cfg260=v260.V260Config(history=cfg.history,v249_engine_path=cfg.v249_engine_path,v259_engine_path=cfg.v259_engine_path,
        v259_state_dir=cfg.v259_state_dir,v258_state_dir=cfg.v258_state_dir,v257_state_dir=cfg.v257_state_dir,v260_state_dir=cfg.v260_state_dir,
        target=int(audit.target),expected_last=int(audit.max_concurso),lines=cfg.lines,quiet=cfg.quiet,prospective_register=False)
    score,baseline_idx,pol,parent_label,parent_manifest=v260._load_parent(cfg260,int(audit.target),str(audit.sha256),v259)
    ranks=v259.tie_worst_rank_vector(score); direct_idx=v259.direct_topn(score,cfg.lines)
    profile=robust_motif_profile(score,core.ALL_COMBOS,cfg)
    progress(cfg,f"V261 parent={parent_label}; motif stability={profile['admitted_pairs']}P/{profile['admitted_triples']}T; strength={profile['pair_strength']:.3f}/{profile['triple_strength']:.3f}")
    idx,selector=lexicographic_selector(score,core.ALL_COMBOS,cfg,v259,profile)

    direct=render(core,direct_idx,score,ranks,'parent_direct_topn_control')
    control=render(core,baseline_idx,score,ranks,'v259_control')
    port=render(core,idx,score,ranks,'v261_lexicographic_regret')
    dmet=exposure_metrics(direct_idx,core.ALL_COMBOS,ranks,profile); cmet=exposure_metrics(baseline_idx,core.ALL_COMBOS,ranks,profile); vmet=exposure_metrics(idx,core.ALL_COMBOS,ranks,profile)
    q=exact_quality_vector(score,ranks,cfg.candidate_pool_max_rank); dq=float(np.sum(q[direct_idx])); vq=float(np.sum(q[idx])); vmet['exact_quality_ratio_vs_direct']=vq/max(1e-15,dq)
    port['is_direct_top30']=port['combo_index'].isin(set(map(int,direct_idx))).astype(int); port['is_v259_control']=port['combo_index'].isin(set(map(int,baseline_idx))).astype(int)
    psha=_profile_sha(profile)
    snap={'schema':V261_SCHEMA,'engine':V261_ENGINE,'target':int(audit.target),'history_last':int(audit.max_concurso),'history_sha256':str(audit.sha256),'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),
          'parent_label':parent_label,'parent_manifest':parent_manifest,'parent_score':np.asarray(score,np.float32),'direct_idx':direct_idx,'v259_idx':baseline_idx,'v261_idx':idx,
          'selector':selector,'profile_sha256':psha,'direct_metrics':dmet,'v259_metrics':cmet,'v261_metrics':vmet}
    sp=save_snapshot(cfg,snap); verify_snapshot(joblib.load(sp))
    out=Path(str(cfg.out_dir).replace('{target}',str(int(audit.target)))); out.mkdir(parents=True,exist_ok=True)
    port.to_csv(out/f'v261_LEXICOGRAPHIC_REGRET_{cfg.lines}_target_{audit.target}.csv',index=False)
    control.to_csv(out/f'v261_CONTROL_V259_{cfg.lines}_target_{audit.target}.csv',index=False)
    direct.to_csv(out/f'v261_CONTROL_DIRECT_{cfg.lines}_target_{audit.target}.csv',index=False)
    pd.DataFrame([{'pair':'-'.join(map(str,k)),'weight':v} for k,v in profile['pair_weights'].items()]).to_csv(out/'v261_stable_pairs.csv',index=False)
    pd.DataFrame([{'triple':'-'.join(map(str,k)),'weight':v} for k,v in profile['triple_weights'].items()]).to_csv(out/'v261_stable_triples.csv',index=False)
    order=np.lexsort((np.arange(len(score)),-np.asarray(score))); topn=min(len(order),max(cfg.lines,cfg.top_ranking_rows))
    pd.DataFrame({'rank':np.arange(1,topn+1),'combo_index':order[:topn],'combo':[core.combo_str(tuple(map(int,core.ALL_COMBOS[i]))) for i in order[:topn]],'parent_score':np.asarray(score)[order[:topn]]}).to_csv(out/f'v261_parent_top{topn}_ranking.csv',index=False)
    runtime={'target':int(audit.target),'history_last':int(audit.max_concurso),'parent':parent_label,'profile':{k:v for k,v in profile.items() if k not in ('pair_weights','triple_weights','number_weights')},
             'selector':selector,'direct_metrics':dmet,'v259_metrics':cmet,'v261_metrics':vmet,
             'statement':'V261 uses lexicographic MILP: exact-quality first, assembly second under an explicit regret budget.'}
    (out/'v261_runtime.json').write_text(json.dumps(runtime,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
    preg=preregister(cfg,audit,joblib.load(sp),port,control,direct) if cfg.prospective_register else None
    print('\n=== V261 SELECTOR ==='); print(json.dumps(selector,indent=2,ensure_ascii=False,default=str))
    print('\n=== V261 METRICS ==='); print(json.dumps(vmet,indent=2,ensure_ascii=False,default=str))
    print('\n=== V261 TOP30 ==='); print(port.to_string(index=False))
    print('Snapshot:',sp); print('Preregister:',preg); print('Outputs:',out)
    return 0

if __name__=='__main__': raise SystemExit(main())
