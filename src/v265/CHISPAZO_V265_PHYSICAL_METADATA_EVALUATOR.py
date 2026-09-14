from __future__ import annotations
import argparse, json, math
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.stats import ttest_1samp

N=28; K=5; BASE=K/N

def logprob_conditional5(p, chosen):
    p=np.clip(np.asarray(p,float),1e-9,1-1e-9)
    w=p/(1-p)
    e=np.zeros(K+1,float); e[0]=1.0
    for x in w:
        for j in range(K,0,-1): e[j]+=x*e[j-1]
    return sum(math.log(w[n-1]) for n in chosen)-math.log(e[K])

def shrunk_prob(counts, trials, prior):
    return (counts + prior*BASE)/(trials+prior)

def main():
    ap=argparse.ArgumentParser(description='V265 evaluator: physical metadata, chronological prequential only')
    ap.add_argument('--history',required=True)
    ap.add_argument('--metadata',required=True)
    ap.add_argument('--out-dir',default='v265_physical_eval')
    ap.add_argument('--burn',type=int,default=100)
    ap.add_argument('--prior-set',type=float,default=300.0)
    ap.add_argument('--prior-machine',type=float,default=600.0)
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    h=pd.read_csv(args.history)
    m=pd.read_csv(args.metadata)
    req_h=['CONCURSO','R1','R2','R3','R4','R5']
    req_m=['CONCURSO','sphere_set_id','machine_id','available_before_close']
    for c in req_h:
        if c not in h: raise ValueError(f'history missing {c}')
    for c in req_m:
        if c not in m: raise ValueError(f'metadata missing {c}')
    x=h.merge(m,on='CONCURSO',how='inner').sort_values('CONCURSO').reset_index(drop=True)
    if len(x)<args.burn+30: raise ValueError('Insufficient joined metadata for prequential evaluation')
    global_c=np.zeros(N,int); global_t=0
    set_c=defaultdict(lambda:np.zeros(N,int)); set_t=defaultdict(int)
    mach_c=defaultdict(lambda:np.zeros(N,int)); mach_t=defaultdict(int)
    rows=[]
    for i,r in x.iterrows():
        y=tuple(sorted(int(r[f'R{j}']) for j in range(1,6)))
        sid=str(r['sphere_set_id']); mid=str(r['machine_id'])
        if i>=args.burn:
            pg=shrunk_prob(global_c,global_t,1000.0)
            ps=shrunk_prob(set_c[sid],set_t[sid],args.prior_set)
            pm=shrunk_prob(mach_c[mid],mach_t[mid],args.prior_machine)
            # Equal-weight log-odds ensemble; no target outcome enters these probabilities.
            def lg(p): return np.log(np.clip(p,1e-9,1-1e-9)/(1-np.clip(p,1e-9,1-1e-9)))
            z=(lg(pg)+lg(ps)+lg(pm))/3.0
            p=1/(1+np.exp(-z))
            lp=logprob_conditional5(p,y)
            logu=-math.log(math.comb(N,K))
            rows.append({'CONCURSO':int(r.CONCURSO),'log_lift':lp-logu,
                         'sphere_set_id':sid,'machine_id':mid,
                         'available_before_close':str(r['available_before_close']).strip().lower() in ('1','true','yes','si','sí')})
        global_t+=1; set_t[sid]+=1; mach_t[mid]+=1
        for n in y:
            global_c[n-1]+=1; set_c[sid][n-1]+=1; mach_c[mid][n-1]+=1
    d=pd.DataFrame(rows); d.to_csv(out/'v265_physical_prequential.csv',index=False)
    mean=float(d.log_lift.mean()); t,p2=ttest_1samp(d.log_lift,0.0,nan_policy='omit')
    p1=float(p2/2 if t>0 else 1-p2/2)
    all_preclose=bool(d.available_before_close.all())
    # Research edge and wagering-actionable edge are deliberately separate.
    research_edge=bool(mean>0 and p1<0.01)
    actionable=bool(research_edge and all_preclose)
    rep={'n':len(d),'mean_log_lift':mean,'one_sided_p':p1,
         'research_edge':research_edge,'all_metadata_available_before_close':all_preclose,
         'actionable_for_betting':actionable,
         'decision': 'PROMOTE_PHYSICAL_RESEARCH' if research_edge else 'NO_PHYSICAL_EDGE',
         'production_rule':'Never use post-close/current-draw metadata to claim an actionable pre-bet edge.'}
    (out/'v265_physical_eval_report.json').write_text(json.dumps(rep,indent=2),encoding='utf-8')
    print(json.dumps(rep,indent=2))

if __name__=='__main__': main()
