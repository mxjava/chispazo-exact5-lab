#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, hashlib, importlib.util, itertools, json, math, os, sys, time, tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple
import joblib, numpy as np, pandas as pd

V261E_SCHEMA=2611
V261E_ENGINE='CHISPAZO_V261_PROSPECTIVE_EVIDENCE_LOOP'

@dataclass(frozen=True)
class EvidenceConfig:
    history: str=r'D:\melate\Chispazo.csv'
    v261_engine_path: str=r'D:\melate\melate_new\CHISPAZO_V261_LEXICOGRAPHIC_REGRET.py'
    v261_config_path: str=r'D:\melate\melate_new\chispazo_v261.toml'
    registry_dir: str=r'D:\melate\preregistros_v261e'
    evidence_dir: str=r'D:\melate\state_v261e'
    lines: int=30
    gate_min_oos: int=30
    gate_mature_oos: int=120
    gate_alpha: float=0.10
    require_exact5_noninferior: bool=True
    require_ge4_noninferior: bool=True
    require_ge3_noninferior: bool=True

def _flatten(d:Mapping[str,Any])->Dict[str,Any]:
    out={}
    def walk(x):
        for k,v in x.items():
            kk=str(k).replace('-','_')
            if isinstance(v,dict): walk(v)
            else: out[kk]=v
    walk(d); return out

def load_config(path:Optional[Path])->EvidenceConfig:
    base=asdict(EvidenceConfig())
    if path is not None:
        with Path(path).open('rb') as f: vals=_flatten(tomllib.load(f))
        bad=sorted(set(vals)-set(base))
        if bad: raise ValueError(f'Claves V261E desconocidas: {bad}')
        base.update(vals)
    cfg=EvidenceConfig(**base); validate_config(cfg); return cfg

def validate_config(cfg):
    if cfg.lines<1: raise ValueError('lines invalido')
    if cfg.gate_min_oos<1 or cfg.gate_mature_oos<cfg.gate_min_oos: raise ValueError('gate OOS invalido')
    if not (0<cfg.gate_alpha<=.5): raise ValueError('gate_alpha invalido')

def _load_module(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,Path(path)); mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod

def _json_hash(payload:Mapping[str,Any],drop=('manifest_sha256',))->str:
    d=dict(payload)
    for k in drop:d.pop(k,None)
    return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def verify_preregister(p:Mapping[str,Any])->None:
    if int(p.get('schema',-1))!=V261E_SCHEMA or str(p.get('engine',''))!=V261E_ENGINE: raise RuntimeError('V261E prereg schema/engine invalido')
    if _json_hash(p)!=str(p.get('manifest_sha256','')): raise RuntimeError('V261E prereg manifest mismatch')
    t=int(p['target'])
    if int(p.get('history_last',-9))!=t-1: raise RuntimeError('V261E target-1 causal lock invalido')

def read_history(path:Path)->pd.DataFrame:
    df=pd.read_csv(path); req=['CONCURSO','R1','R2','R3','R4','R5']; miss=[c for c in req if c not in df.columns]
    if miss: raise ValueError(f'Historico sin {miss}')
    x=df[req].copy()
    for c in req:x[c]=pd.to_numeric(x[c],errors='raise').astype(int)
    return x.drop_duplicates('CONCURSO',keep='first').sort_values('CONCURSO').reset_index(drop=True)

def parse_combo(s:Any)->Tuple[int,...]:
    import re
    x=tuple(sorted(int(z) for z in re.findall(r'\d+',str(s))))
    if len(x)!=5 or len(set(x))!=5 or min(x)<1 or max(x)>28: raise ValueError(f'combo invalida {s}')
    return x

def combo_str(x:Sequence[int])->str:return '-'.join(f'{int(z):02d}' for z in sorted(map(int,x)))

def score_portfolio(lines:Sequence[Any],actual:Sequence[int])->Dict[str,Any]:
    a=tuple(sorted(map(int,actual))); aset=set(a); hits=[]; cp=set(); ct=set(); best=[]
    for x in lines:
        c=parse_combo(x); h=len(aset&set(c)); hits.append(h)
        for p in itertools.combinations(a,2):
            if set(p).issubset(c): cp.add(p)
        for t in itertools.combinations(a,3):
            if set(t).issubset(c): ct.add(t)
    if not hits:return {'lines':0,'best_hit':0,'exact5':0,'ge4':0,'ge3':0,'pair_cov':0,'triple_cov':0,'utility':0.0}
    b=max(hits)
    # best_hit dominates; pair/triple only break ties structurally.
    u=float(b)+0.20*(len(cp)/10.0)+0.10*(len(ct)/10.0)
    return {'lines':len(hits),'best_hit':int(b),'exact5':int(any(h==5 for h in hits)),'ge4':int(any(h>=4 for h in hits)),'ge3':int(any(h>=3 for h in hits)),
            'count5':int(sum(h==5 for h in hits)),'count4':int(sum(h==4 for h in hits)),'count3':int(sum(h==3 for h in hits)),
            'pair_cov':int(len(cp)),'triple_cov':int(len(ct)),'utility':u}

def one_sided_sign_p(wins:int,losses:int)->float:
    n=wins+losses
    if n<=0:return 1.0
    return float(sum(math.comb(n,k) for k in range(wins,n+1))/(2.0**n))

def gate_from_ledger(df:pd.DataFrame,cfg:EvidenceConfig)->Dict[str,Any]:
    if df.empty:return {'state':'cold_start','n':0,'lambda':0.0,'wins':0,'losses':0,'ties':0,'p_sign':1.0,'reason':'no prospective resolved targets'}
    g=df[df['prospective_eligible'].astype(int)==1].copy(); n=len(g)
    if not n:return {'state':'cold_start','n':0,'lambda':0.0,'wins':0,'losses':0,'ties':0,'p_sign':1.0,'reason':'no eligible targets'}
    du=g['v261_utility'].astype(float)-g['v259_utility'].astype(float)
    wins=int((du>1e-12).sum()); losses=int((du<-1e-12).sum()); ties=n-wins-losses; p=one_sided_sign_p(wins,losses)
    ex261=int(g.v261_exact5.sum()); ex259=int(g.v259_exact5.sum()); g4a=int(g.v261_ge4.sum()); g4b=int(g.v259_ge4.sum()); g3a=int(g.v261_ge3.sum()); g3b=int(g.v259_ge3.sum())
    d={'state':'cold_start','n':n,'lambda':0.0,'wins':wins,'losses':losses,'ties':ties,'p_sign':p,'v261_exact5':ex261,'v259_exact5':ex259,'v261_ge4':g4a,'v259_ge4':g4b,'v261_ge3':g3a,'v259_ge3':g3b,'mean_utility_delta':float(du.mean())}
    if n<cfg.gate_min_oos:d['reason']=f'n<{cfg.gate_min_oos}'; return d
    cond=[]
    if cfg.require_exact5_noninferior:cond.append(ex261>=ex259)
    if cfg.require_ge4_noninferior:cond.append(g4a>=g4b)
    if cfg.require_ge3_noninferior:cond.append(g3a>=g3b)
    cond.extend([wins>losses,p<=cfg.gate_alpha,float(du.mean())>0])
    if all(cond):
        lam=1.0 if cfg.gate_mature_oos==cfg.gate_min_oos else min(1.0,max(0.0,(n-cfg.gate_min_oos+1)/(cfg.gate_mature_oos-cfg.gate_min_oos+1)))
        d.update({'state':'open','lambda':float(lam),'reason':'all prospective gates pass; lambda is used for gradual production replacement'})
    else:d.update({'state':'closed','lambda':0.0,'reason':'prospective gate conditions not met'})
    return d

def _winner_parent_rank(score:np.ndarray,actual:Sequence[int],core)->int:
    mp={tuple(map(int,c)):i for i,c in enumerate(core.ALL_COMBOS)}; i=mp[tuple(sorted(map(int,actual)))]; s=np.asarray(score,float); return int(np.sum(s>=s[i]))

def rebuild_ledger(cfg:EvidenceConfig):
    hist=read_history(Path(cfg.history)); actuals={int(r.CONCURSO):(r.R1,r.R2,r.R3,r.R4,r.R5) for r in hist.itertuples()}
    v261=_load_module(Path(cfg.v261_engine_path),'v261e_engine'); cfg261=v261.load_config(Path(cfg.v261_config_path)); core=_load_module(Path(cfg261.v249_engine_path),'v261e_core')
    reg=Path(cfg.registry_dir); reg.mkdir(parents=True,exist_ok=True); rows=[]; prev=''; preregs=[]
    for pth in reg.glob('target_*_V261E_preregister.json'):
        try:q=json.loads(pth.read_text(encoding='utf-8')); preregs.append((int(q.get('target',-1)),pth,q))
        except Exception:preregs.append((-1,pth,None))
    for _,pth,p0 in sorted(preregs,key=lambda z:(z[0],z[1].name)):
        try:
            p=p0 if p0 is not None else json.loads(pth.read_text(encoding='utf-8')); verify_preregister(p); t=int(p['target'])
            if str(p.get('previous_manifest_sha256',''))!=prev: raise RuntimeError('V261E prereg chain mismatch')
            prev=str(p['manifest_sha256'])
            if t not in actuals:continue
            actual=actuals[t]; a=score_portfolio(p['v261_research'],actual); b=score_portfolio(p['v259_control'],actual); prod=score_portfolio(p['production_portfolio'],actual)
            sp=Path(cfg261.v261_state_dir)/'snapshots'/f'target_{t}.joblib'
            if not sp.exists():raise RuntimeError('V261 snapshot missing')
            snap=joblib.load(sp); v261.verify_snapshot(snap)
            if str(snap.get('manifest_sha256',''))!=str(p.get('v261_snapshot_manifest','')):raise RuntimeError('snapshot/prereg mismatch')
            rows.append({'target':t,'actual':combo_str(actual),'prospective_eligible':1,'parent_exact_rank':_winner_parent_rank(np.asarray(snap['parent_score']),actual,core),
                         'v261_best_hit':a['best_hit'],'v261_exact5':a['exact5'],'v261_ge4':a['ge4'],'v261_ge3':a['ge3'],'v261_pair_cov':a['pair_cov'],'v261_triple_cov':a['triple_cov'],'v261_utility':a['utility'],
                         'v259_best_hit':b['best_hit'],'v259_exact5':b['exact5'],'v259_ge4':b['ge4'],'v259_ge3':b['ge3'],'v259_pair_cov':b['pair_cov'],'v259_triple_cov':b['triple_cov'],'v259_utility':b['utility'],
                         'production_best_hit':prod['best_hit'],'production_exact5':prod['exact5'],'production_ge4':prod['ge4'],'production_ge3':prod['ge3'],'production_utility':prod['utility'],
                         'production_lambda':float(p.get('production_lambda',0.0)),'preregister_manifest':p['manifest_sha256']})
        except Exception as e: rows.append({'target':-1,'actual':'','prospective_eligible':0,'error':f'{pth.name}: {type(e).__name__}: {e}'})
    df=pd.DataFrame(rows)
    if not df.empty:df=df.sort_values(['prospective_eligible','target'],ascending=[False,True]).reset_index(drop=True)
    return df,gate_from_ledger(df,cfg)

def write_evidence(cfg,df,gate):
    d=Path(cfg.evidence_dir);d.mkdir(parents=True,exist_ok=True);lp=d/'v261e_prospective_ledger.csv';gp=d/'v261e_gate.json';df.to_csv(lp,index=False)
    q={'schema':V261E_SCHEMA,'engine':V261E_ENGINE,'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),'gate':dict(gate),'ledger_rows':len(df)};q['manifest_sha256']=_json_hash(q)
    tmp=gp.with_suffix('.tmp');tmp.write_text(json.dumps(q,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(tmp,gp);return lp,gp

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--config',default=None);a=ap.parse_args();cfg=load_config(Path(a.config) if a.config else None);df,g=rebuild_ledger(cfg);lp,gp=write_evidence(cfg,df,g);print(json.dumps(g,indent=2,ensure_ascii=False));print('Ledger:',lp);print('Gate:',gp);return 0
if __name__=='__main__':raise SystemExit(main())
