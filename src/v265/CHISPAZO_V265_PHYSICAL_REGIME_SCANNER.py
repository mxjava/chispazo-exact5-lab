from __future__ import annotations
import argparse, json, math, itertools, hashlib
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, norm, pearsonr, spearmanr
from scipy.special import logsumexp
from scipy import sparse

N_NUMBERS=28
K=5
ALL_COMBOS=list(itertools.combinations(range(1,N_NUMBERS+1),K))
COMBO_INDEX={c:i for i,c in enumerate(ALL_COMBOS)}
U=1.0/len(ALL_COMBOS)
LOGU=math.log(U)
PAIR_LIST=list(itertools.combinations(range(1,N_NUMBERS+1),2))
TRIPLE_LIST=list(itertools.combinations(range(1,N_NUMBERS+1),3))
PAIR_INDEX={p:i for i,p in enumerate(PAIR_LIST)}
TRIPLE_INDEX={t:i for i,t in enumerate(TRIPLE_LIST)}
PAIR_P=math.comb(26,3)/math.comb(28,5)
TRIPLE_P=math.comb(25,2)/math.comb(28,5)


def holm_adjust(pvals):
    p=np.asarray(pvals,float); m=len(p); order=np.argsort(p); out=np.empty(m,float); run=0.0
    for r,idx in enumerate(order):
        a=min(1.0,(m-r)*p[idx]); run=max(run,a); out[idx]=run
    return out


def logprob_conditional5(p, S):
    p=np.clip(np.asarray(p,float),1e-12,1-1e-12)
    w=p/(1-p)
    e=np.zeros(6,float); e[0]=1.0
    for x in w:
        for j in range(5,0,-1): e[j]+=x*e[j-1]
    return sum(math.log(w[n-1]) for n in S)-math.log(e[5])


def load_history(path):
    df=pd.read_csv(path)
    req=['CONCURSO','R1','R2','R3','R4','R5','FECHA']
    miss=[c for c in req if c not in df.columns]
    if miss: raise ValueError(f'Missing columns: {miss}')
    for c in ['CONCURSO','R1','R2','R3','R4','R5']:
        df[c]=pd.to_numeric(df[c],errors='raise').astype(int)
    df['FECHA']=pd.to_datetime(df['FECHA'])
    df=df.sort_values('CONCURSO').drop_duplicates('CONCURSO',keep='last').reset_index(drop=True)
    nums=df[['R1','R2','R3','R4','R5']].to_numpy()
    if ((nums<1)|(nums>28)).any(): raise ValueError('Numbers outside 1..28')
    if any(len(set(map(int,r)))!=5 for r in nums): raise ValueError('Repeated number inside draw')
    return df


def sets_from(df):
    return [set(map(int,r)) for r in df[['R1','R2','R3','R4','R5']].to_numpy()]


def same_day_pairs(df):
    x=df.copy(); x['slot']=x.groupby('FECHA').cumcount()+1
    rows=[]
    for date,g in x.groupby('FECHA'):
        if len(g)!=2: continue
        g=g.sort_values('CONCURSO')
        a=set(map(int,g.iloc[0][['R1','R2','R3','R4','R5']]))
        b=set(map(int,g.iloc[1][['R1','R2','R3','R4','R5']]))
        rows.append((date,int(g.iloc[0].CONCURSO),int(g.iloc[1].CONCURSO),a,b))
    return rows


def same_day_prequential(pairs, prior=112, burn=100):
    N=0; base=5/28
    late_counts=np.zeros(28,int)
    exp_status=np.zeros((28,2),int); suc_status=np.zeros((28,2),int)
    exp_wd=np.zeros((7,28),int); suc_wd=np.zeros((7,28),int)
    ge=np.zeros(2,int); gs=np.zeros(2,int)
    out=[]
    for date,c1,c2,early,late in pairs:
        wd=pd.Timestamp(date).weekday()
        if N>=burn:
            ps=(late_counts+prior*base)/(N+prior)
            q=np.array([(gs[s]+prior*base)/(ge[s]+prior) for s in (0,1)])
            pg=np.array([q[1 if n+1 in early else 0] for n in range(28)])
            pn=np.empty(28); pw=np.empty(28)
            for n in range(28):
                s=1 if n+1 in early else 0
                pn[n]=(suc_status[n,s]+prior*ps[n])/(exp_status[n,s]+prior)
                pw[n]=(suc_wd[wd,n]+prior*ps[n])/(exp_wd[wd,n]+prior)
            def lg(x):
                x=np.clip(x,1e-12,1-1e-12); return np.log(x/(1-x))
            blend=1/(1+np.exp(-(0.5*lg(pn)+0.5*lg(pw))))
            models={'slot_freq':ps,'global_repeat':pg,'num_repeat':pn,'weekday':pw,'blend':blend}
            rec={'contest':c2,'date':str(pd.Timestamp(date).date())}
            for name,pv in models.items(): rec[name]=logprob_conditional5(pv,late)-LOGU
            out.append(rec)
        for n in range(1,29):
            e=int(n in early); l=int(n in late)
            late_counts[n-1]+=l
            exp_status[n-1,e]+=1; suc_status[n-1,e]+=l
            exp_wd[wd,n-1]+=1; suc_wd[wd,n-1]+=l
            ge[e]+=1; gs[e]+=l
        N+=1
    return pd.DataFrame(out)


def counts_pairs(draws):
    c=Counter()
    for s in draws:
        for p in itertools.combinations(sorted(s),2): c[p]+=1
    return np.array([c[p] for p in PAIR_LIST])

def counts_triples(draws):
    c=Counter()
    for s in draws:
        for t in itertools.combinations(sorted(s),3): c[t]+=1
    return np.array([c[t] for t in TRIPLE_LIST])


def persistence(draws):
    N=len(draws); h=N//2; n2=N-h
    pc=counts_pairs(draws); pc1=counts_pairs(draws[:h]); pc2=counts_pairs(draws[h:])
    tp=counts_triples(draws); tp1=counts_triples(draws[:h]); tp2=counts_triples(draws[h:])
    def z(c,n,p): return (c-n*p)/math.sqrt(n*p*(1-p))
    zp=z(pc,N,PAIR_P); z1=z(pc1,h,PAIR_P); z2=z(pc2,n2,PAIR_P)
    zt=z(tp,N,TRIPLE_P); t1=z(tp1,h,TRIPLE_P); t2=z(tp2,n2,TRIPLE_P)
    pp=2*norm.sf(np.abs(zp)); pt=2*norm.sf(np.abs(zt))
    pair_adj=holm_adjust(pp); trip_adj=holm_adjust(pt)
    pi=int(np.argmin(pp)); ti=int(np.argmin(pt))
    return {
        'n':N,
        'pairs_holm_sig':int((pair_adj<0.05).sum()),
        'triples_holm_sig':int((trip_adj<0.05).sum()),
        'pair_half_pearson':float(pearsonr(z1,z2).statistic),
        'pair_half_spearman':float(spearmanr(z1,z2).statistic),
        'triple_half_pearson':float(pearsonr(t1,t2).statistic),
        'triple_half_spearman':float(spearmanr(t1,t2).statistic),
        'most_extreme_pair':{'pair':'-'.join(map(str,PAIR_LIST[pi])),'z':float(zp[pi]),'p_raw':float(pp[pi]),'p_holm':float(pair_adj[pi])},
        'most_extreme_triple':{'triple':'-'.join(map(str,TRIPLE_LIST[ti])),'z':float(zt[ti]),'p_raw':float(pt[ti]),'p_holm':float(trip_adj[ti])},
    }


def periodic_prequential(df, mods=(2,3,4,5,6,7,8,10,12,14,20), priors=(112,448), burn=200):
    sets=sets_from(df); contests=df.CONCURSO.to_numpy(int); base=5/28; rows=[]
    for mod in mods:
        for prior in priors:
            cnt=np.zeros((mod,28),int); nobs=np.zeros(mod,int); ll=[]
            for i,(c,S) in enumerate(zip(contests,sets)):
                g=c%mod
                if i>=burn and nobs[g]>=5:
                    p=(cnt[g]+prior*base)/(nobs[g]+prior)
                    ll.append(logprob_conditional5(p,S)-LOGU)
                for n in S: cnt[g,n-1]+=1
                nobs[g]+=1
            a=np.asarray(ll,float)
            rows.append({'mod':mod,'prior':prior,'n':len(a),'mean_loglift':float(a.mean()),'last1000_mean_loglift':float(a[-min(1000,len(a)):].mean())})
    return pd.DataFrame(rows)


def build_incidence():
    rows=np.repeat(np.arange(len(ALL_COMBOS)),10)
    pcols=[]; tcols=[]
    for c in ALL_COMBOS:
        pcols.extend(PAIR_INDEX[p] for p in itertools.combinations(c,2))
        tcols.extend(TRIPLE_INDEX[t] for t in itertools.combinations(c,3))
    P=sparse.csr_matrix((np.ones(len(pcols),dtype=np.float32),(rows,np.asarray(pcols))),shape=(len(ALL_COMBOS),len(PAIR_LIST)))
    T=sparse.csr_matrix((np.ones(len(tcols),dtype=np.float32),(rows,np.asarray(tcols))),shape=(len(ALL_COMBOS),len(TRIPLE_LIST)))
    return P,T


def motif_prequential_post2022(df, priors=(3000,), alphas=(0.1,0.25), block=20, burn=300):
    draws=sets_from(df); obs=np.array([COMBO_INDEX[tuple(sorted(s))] for s in draws],int)
    P,T=build_incidence()
    drawP=[[PAIR_INDEX[p] for p in itertools.combinations(sorted(s),2)] for s in draws]
    drawT=[[TRIPLE_INDEX[t] for t in itertools.combinations(sorted(s),3)] for s in draws]
    rows=[]
    for label,M,didx,p0 in [('pair',P,drawP,PAIR_P),('triple',T,drawT,TRIPLE_P)]:
        for prior in priors:
            counts=np.zeros(M.shape[1],int); n=0; series={a:[] for a in alphas}
            for start in range(0,len(draws),block):
                end=min(len(draws),start+block)
                if n>=burn:
                    q=(counts+prior*p0)/(n+prior)
                    w=np.log(np.clip(q,1e-12,None)/p0)
                    raw=np.asarray(M.dot(w)).ravel(); ob=raw[obs[start:end]]
                    for a in alphas:
                        lm=logsumexp(a*raw)-math.log(len(raw))
                        series[a].extend((a*ob-lm).tolist())
                for i in range(start,end): np.add.at(counts,didx[i],1)
                n+=end-start
            for a,v in series.items():
                v=np.asarray(v,float); cut=len(v)//2
                rows.append({'motif':label,'prior':prior,'alpha':a,'n':len(v),'discovery_mean_loglift':float(v[:cut].mean()),'validation_mean_loglift':float(v[cut:].mean()),'all_mean_loglift':float(v.mean())})
    return pd.DataFrame(rows)


def metadata_template(path):
    cols=['CONCURSO','FECHA','SLOT','machine_id','machine_model','sphere_set_id','sphere_color','min_weight_g','max_weight_g','weight_range_g','rfid_verified','incident','source_url','source_sha256']
    pd.DataFrame(columns=cols).to_csv(path,index=False)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--history',required=True)
    ap.add_argument('--out-dir',default='v265_outputs')
    ap.add_argument('--machine-cutover',default='2022-03-10')
    args=ap.parse_args()
    out=Path(args.out_dir); out.mkdir(parents=True,exist_ok=True)
    df=load_history(args.history); draws=sets_from(df)
    pairs=same_day_pairs(df)
    sd=same_day_prequential(pairs,prior=112,burn=100); sd.to_csv(out/'v265_same_day_prequential.csv',index=False)
    sd_summary={c:float(sd[c].mean()) for c in ['slot_freq','global_repeat','num_repeat','weekday','blend']}
    all_persist=persistence(draws)
    cut=pd.Timestamp(args.machine_cutover); post=df[df.FECHA>=cut].reset_index(drop=True); postdraws=sets_from(post)
    post_persist=persistence(postdraws)
    periodic=periodic_prequential(post); periodic.to_csv(out/'v265_post2022_periodic_proxy.csv',index=False)
    motif=motif_prequential_post2022(post); motif.to_csv(out/'v265_post2022_motif_prequential.csv',index=False)
    # individual same-day carryover tests
    car=[]
    for n in range(1,29):
        a=b=c=d=0
        for _,_,_,early,late in pairs:
            e=n in early; l=n in late
            if e and l: a+=1
            elif e: b+=1
            elif l: c+=1
            else: d+=1
        odds,p=fisher_exact([[a,b],[c,d]])
        car.append({'number':n,'both':a,'early_only':b,'late_only':c,'neither':d,'odds_ratio':odds,'p_raw':p,'p_late_given_early':a/(a+b),'p_late_given_not':c/(c+d)})
    car=pd.DataFrame(car); car['p_holm']=holm_adjust(car.p_raw.values); car.to_csv(out/'v265_same_day_number_carryover.csv',index=False)
    metadata_template(out/'v265_physical_metadata_template.csv')
    best_periodic=periodic.sort_values('last1000_mean_loglift',ascending=False).iloc[0].to_dict()
    best_motif=motif.sort_values('validation_mean_loglift',ascending=False).iloc[0].to_dict()
    state='RESEARCH_ONLY_METADATA_REQUIRED'
    report={
      'version':'V265_PHYSICAL_REGIME_SCANNER',
      'history':{'rows':len(df),'min_concurso':int(df.CONCURSO.min()),'max_concurso':int(df.CONCURSO.max()),'dual_day_pairs':len(pairs)},
      'machine_cutover':str(cut.date()),'post_cutover_rows':len(post),
      'same_day_mean_loglift':sd_summary,
      'same_day_any_positive_mean':bool(any(v>0 for v in sd_summary.values())),
      'same_day_min_holm':float(car.p_holm.min()),
      'all_history_persistence':all_persist,
      'post2022_persistence':post_persist,
      'best_periodic_proxy':best_periodic,
      'best_motif_validation':best_motif,
      'decision':state,
      'production_rule':'Do not promote result-only physical proxies. Require actual machine_id/sphere_set_id metadata and OOS exact-set log-lift > 0 with multiplicity control.',
    }
    (out/'v265_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    lines=['# V265 Physical-Regime Evidence Scanner','',f"History: {report['history']}",f"Machine-era cutover: {report['machine_cutover']} ({len(post)} draws)",'','## Same-day Clásico conditioning']
    lines += [f"- {k}: mean exact-set log-lift {v:.9f}" for k,v in sd_summary.items()]
    lines += ['',f"Minimum Holm-adjusted carryover p-value: {report['same_day_min_holm']:.6g}",'','## Pair/triple persistence',f"All history: {all_persist}",f"Post-2022: {post_persist}",'',f"Best periodic proxy: {best_periodic}",f"Best motif validation: {best_motif}",'',f"DECISION: {state}",'','Next required data: actual machine/ball-set identity, sphere weights/RFID verification and incidents per draw.']
    (out/'V265_REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
