from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import logsumexp

def audit(scores: str, *, resamples: int = 5000, seed: int = 20261120) -> dict:
    frame = pd.read_csv(scores)
    required = {"CONCURSO", "expert", "log_lift"}
    if required - set(frame.columns): raise ValueError(f"missing columns: {sorted(required-set(frame.columns))}")
    if frame.duplicated(["CONCURSO","expert"]).any(): raise ValueError("duplicate contest/expert rows")
    frame["log_lift"] = pd.to_numeric(frame["log_lift"], errors="raise")
    if not np.isfinite(frame.log_lift.to_numpy(float)).all(): raise ValueError("non-finite scores")
    pivot = frame.pivot(index="CONCURSO", columns="expert", values="log_lift").sort_index()
    if pivot.isna().any().any(): raise ValueError("incomplete expert matrix")
    x = pivot.to_numpy(float); prior = np.ones(x.shape[1])/x.shape[1]
    def mix(window, eta):
        out = np.empty(len(x))
        for t in range(len(x)):
            start = 0 if window is None else max(0,t-window)
            lw = np.log(prior) + eta*x[start:t].sum(axis=0)
            lw -= logsumexp(lw)
            out[t] = logsumexp(lw+x[t])
        return out
    specs=[("static_full_bayes",None,1.0)]+[(f"rolling_w{w}_eta{eta:g}",w,eta) for w in (100,250,500) for eta in (.25,.5,1.0)]
    y=np.column_stack([mix(w,e) for _,w,e in specs]); obs=y.mean(axis=0); se=y.std(axis=0,ddof=1)/np.sqrt(len(y))
    n=len(y); block=30; rng=np.random.default_rng(seed); centered=y-y.mean(axis=0); nblocks=int(np.ceil(n/block))
    max_t=np.empty(resamples); max_abs=np.empty(resamples)
    for b in range(resamples):
        starts=rng.integers(0,n,size=nblocks); idx=(starts[:,None]+np.arange(block)[None,:])%n
        sample=centered[idx.reshape(-1)[:n]]; t=sample.mean(axis=0)/se
        max_t[b]=t.max(); max_abs[b]=np.abs(t).max()
    p_adj=np.array([(1+np.sum(max_t>=v))/(resamples+1) for v in obs/se]); q=float(np.quantile(max_abs,.95))
    rows=[]
    for i,(name,_,_) in enumerate(specs):
        rows.append({"candidate":name,"mean_log_lift":float(obs[i]),"se_descriptive":float(se[i]),"maxT_one_sided_p_adjusted":float(p_adj[i]),"simultaneous_95_ci_low":float(obs[i]-q*se[i]),"simultaneous_95_ci_high":float(obs[i]+q*se[i])})
    return {"n_targets":n,"contest_min":int(pivot.index.min()),"contest_max":int(pivot.index.max()),"n_experts":int(x.shape[1]),"block_length":block,"bootstrap_resamples":resamples,"seed":seed,"method":"joint circular moving-block bootstrap; centered under null; single-step maxT one-sided FWER adjustment; simultaneous two-sided 95% max-absolute-t interval","maxT_95_abs_critical":q,"results":rows,"limitations":["Canonical sequence includes unresolved official modality assignment; not certified Clásico-only.","Candidate family covers V323 static and rolling expert mixtures only; does not include V294.","Bootstrap inference is dependence-aware diagnostic, not prospective anytime-valid e-process."]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--scores",required=True); ap.add_argument("--out",required=True); ap.add_argument("--resamples",type=int,default=5000); ap.add_argument("--seed",type=int,default=20261120); a=ap.parse_args()
    result=audit(a.scores,resamples=a.resamples,seed=a.seed); Path(a.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8"); print(json.dumps(result,indent=2))
if __name__=="__main__": main()
