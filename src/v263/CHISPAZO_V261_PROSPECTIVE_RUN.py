#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, subprocess, sys, time
from pathlib import Path
from typing import Any,Mapping
import pandas as pd, joblib
HERE=Path(__file__).resolve().parent

def loadmod(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def jhash(p:Mapping[str,Any])->str:
    q=dict(p);q.pop('manifest_sha256',None);return hashlib.sha256(json.dumps(q,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def blend(control:pd.DataFrame,research:pd.DataFrame,lam:float,lines:int):
    cr={str(r.combo):int(r.parent_rank) for r in control.itertuples()}; rr={str(r.combo):int(r.parent_rank) for r in research.itertuples()}; C=set(cr);R=set(rr); common=C&R; co=sorted(C-R,key=lambda x:(-cr[x],x)); ro=sorted(R-C,key=lambda x:(rr[x],x))
    budget=min(len(co),len(ro),max(0,int(round(float(lam)*min(len(co),len(ro)))))); chosen=set(C)
    for x,y in zip(co[:budget],ro[:budget]):chosen.remove(x);chosen.add(y)
    rank={**cr,**rr}; out=sorted(chosen,key=lambda x:(rank.get(x,10**9),x))
    if len(out)!=lines:raise RuntimeError(f'blend cardinalidad {len(out)}/{lines}')
    return out,budget

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--evidence-config',default=str(HERE/'chispazo_v261e.toml'));ap.add_argument('--v261-config',default=str(HERE/'chispazo_v261.toml'));a=ap.parse_args()
    ev=loadmod(HERE/'CHISPAZO_V261_PROSPECTIVE_LOOP.py','v261e_run');cfg=ev.load_config(Path(a.evidence_config));ledger,gate=ev.rebuild_ledger(cfg);ev.write_evidence(cfg,ledger,gate)
    cp=subprocess.run([sys.executable,str(HERE/'CHISPAZO_V261_LEXICOGRAPHIC_REGRET.py'),'--config',str(Path(a.v261_config))],check=False)
    if cp.returncode:return int(cp.returncode)
    h=pd.read_csv(cfg.history);target=int(pd.to_numeric(h.CONCURSO).max())+1
    v=loadmod(HERE/'CHISPAZO_V261_LEXICOGRAPHIC_REGRET.py','v261_freeze');c=v.load_config(Path(a.v261_config));out=Path(str(c.out_dir).replace('{target}',str(target)))
    research_df=pd.read_csv(out/f'v261_LEXICOGRAPHIC_REGRET_{c.lines}_target_{target}.csv');control_df=pd.read_csv(out/f'v261_CONTROL_V259_{c.lines}_target_{target}.csv');direct_df=pd.read_csv(out/f'v261_CONTROL_DIRECT_{c.lines}_target_{target}.csv')
    lam=float(gate.get('lambda',0.0)) if gate.get('state')=='open' else 0.0; production,replacements=blend(control_df,research_df,lam,c.lines)
    snap=joblib.load(Path(c.v261_state_dir)/'snapshots'/f'target_{target}.joblib');v.verify_snapshot(snap)
    reg=Path(cfg.registry_dir);reg.mkdir(parents=True,exist_ok=True);prior=[]
    for pth in reg.glob('target_*_V261E_preregister.json'):
        try:q=json.loads(pth.read_text(encoding='utf-8'));qt=int(q.get('target',-1));
        except Exception:continue
        if qt<target:prior.append((qt,str(q.get('manifest_sha256',''))))
    prev=max(prior,key=lambda z:z[0])[1] if prior else ''
    p={'schema':ev.V261E_SCHEMA,'engine':ev.V261E_ENGINE,'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),'previous_manifest_sha256':prev,'target':target,'history_last':target-1,'history_sha256':str(snap['history_sha256']),
       'v261_snapshot_manifest':str(snap['manifest_sha256']),'evidence_gate_at_freeze':dict(gate),'production_lambda':lam,'production_replacements':replacements,
       'v261_research':research_df.combo.astype(str).tolist(),'v259_control':control_df.combo.astype(str).tolist(),'direct_control':direct_df.combo.astype(str).tolist(),'production_portfolio':production,
       'statement':'Frozen before resolution. Production moves gradually from V259 toward V261 using the prospective gate lambda; no binary full switch.'}
    p['manifest_sha256']=jhash(p);pth=reg/f'target_{target}_V261E_preregister.json'
    if pth.exists():
        old=json.loads(pth.read_text(encoding='utf-8'))
        if old.get('manifest_sha256')!=p['manifest_sha256']:raise RuntimeError('V261E FROZEN CONFLICT')
    else:
        tmp=pth.with_suffix('.tmp');tmp.write_text(json.dumps(p,indent=2,ensure_ascii=False),encoding='utf-8');os.replace(tmp,pth)
    print(json.dumps({'target':target,'gate':gate,'lambda_used':lam,'replacements':replacements,'preregister':str(pth)},indent=2,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
