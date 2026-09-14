#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import binomtest

U=98280
DEPTHS=(30,100,500,2500,5000,10000)
EXACT5_COLS=('score_ltr_ndcg_exact5','score_ltr_adv_exact5','score_ltr_exact5_balanced','score_ltr_exact5_hard','score_ltr_exact5_ultra')

def holm(rows, key='p_raw'):
    m=len(rows); order=sorted(range(m), key=lambda i: rows[i][key]); prev=0.0
    for rank,i in enumerate(order):
        adj=min(1.0,(m-rank)*rows[i][key]); adj=max(prev,adj); rows[i]['p_holm']=adj; prev=adj
    return rows

def health(ranking):
    d=pd.read_csv(ranking); out={}; live=[]
    for c in EXACT5_COLS:
        if c not in d:
            out[c]={'live':False,'reason':'missing'};continue
        x=pd.to_numeric(d[c],errors='coerce').to_numpy(float); fin=np.isfinite(x)
        u=len(np.unique(x[fin])) if fin.any() else 0; sd=float(np.nanstd(x)); nz=float(np.mean(np.abs(x[fin])>1e-12)) if fin.any() else 0
        ok=bool(fin.all() and u>=32 and sd>1e-8 and nz>=.01)
        out[c]={'live':ok,'unique':u,'std':sd,'nonzero_fraction':nz,'reason':'ok' if ok else 'dead_or_constant'}
        if ok: live.append(c)
    return d,out,live

def evidence(meta):
    d=pd.read_csv(meta); tests=[]; summaries=[]
    for st,g in d.groupby('strategy'):
        r=g.exact_rank.to_numpy(int); n=len(r)
        sm={'strategy':st,'n':n,'mean_rank':float(r.mean()),'median_rank':float(np.median(r))}
        for dep in DEPTHS:
            k=int(np.sum(r<=dep)); p0=dep/U
            pv=float(binomtest(k,n,p0,alternative='greater').pvalue)
            tests.append({'strategy':st,'depth':dep,'n':n,'hits':k,'rate':k/n,'null_rate':p0,'lift':(k/n)/p0 if k else 0.0,'p_raw':pv})
            sm[f'top{dep}']=k/n
        summaries.append(sm)
    holm(tests)
    approved=[x for x in tests if x['n']>=100 and x['p_holm']<.05 and x['lift']>1]
    return summaries,tests,approved

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ranking',required=True);ap.add_argument('--meta');ap.add_argument('--exactset-summary');ap.add_argument('--out-dir',required=True);a=ap.parse_args()
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    d,h,live=health(a.ranking)
    summaries=tests=approved=[]
    if a.meta and Path(a.meta).exists(): summaries,tests,approved=evidence(a.meta)
    exactset=None
    if a.exactset_summary and Path(a.exactset_summary).exists(): exactset=json.loads(Path(a.exactset_summary).read_text())
    parent_ok=len(live)>=2
    oos_ok=bool(approved)
    exactset_ok=bool(exactset and exactset.get('cumulative_log_e',-999)>=math.log(20))
    state='PROMOTE_EXACT5' if parent_ok and oos_ok and exactset_ok else ('RESEARCH_ONLY_NO_EDGE' if parent_ok else 'HARD_FAIL_PARENT')
    report={'engine':'V264_EVIDENCE_FIREWALL','state':state,'parent_live_exact5':live,'parent_health':h,'oos_approved_tests':approved,'exactset_anytime':exactset,'policy':{'requires_live_exact5':2,'requires_oos_holm_p_lt':.05,'requires_oos_n':100,'requires_anytime_evalue':20.0,'production_concentration_allowed':state=='PROMOTE_EXACT5'}}
    (out/'v264_firewall_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    pd.DataFrame(summaries).to_csv(out/'v264_oos_strategy_summary.csv',index=False)
    pd.DataFrame(tests).to_csv(out/'v264_oos_depth_tests.csv',index=False)
    print(json.dumps(report,indent=2))
    return 0 if state!='HARD_FAIL_PARENT' else 4
if __name__=='__main__': raise SystemExit(main())
