import pandas as pd, numpy as np, math, json
from pathlib import Path
from itertools import combinations

U=98280
LOGU=math.log(U)
ALPHA=1.0
BETAS=(0.15,0.30,0.60)
WINDOWS=(50,200,800)
EWM_HL=(16,32,64)

def z(v):
    v=np.asarray(v,float); s=v.std()
    return (v-v.mean())/(s if s>1e-12 else 1.0)

def e5(weights):
    e=np.zeros(6,float); e[0]=1.0
    for w in weights:
        for k in range(5,0,-1): e[k]+=w*e[k-1]
    return e[5]

def p_set(signal,beta,actual):
    w=np.exp(beta*z(signal))
    Z=e5(w)
    idx=np.asarray(actual,dtype=int)-1
    return float(np.prod(w[idx])/Z)

def signals(draws, t):
    # all t past draws, each 0-based numbers
    out={}
    for W in WINDOWS:
        sub=draws[max(0,t-W):t]
        cnt=np.bincount(sub.ravel(), minlength=28)
        out[f'freq{W}']=cnt/max(1,len(sub))
    # exponentially weighted inclusion
    for hl in EWM_HL:
        start=max(0,t-6*hl)
        sub=draws[start:t]
        ages=np.arange(len(sub)-1,-1,-1)
        ww=0.5**(ages/hl)
        v=np.zeros(28,float)
        for row,wt in zip(sub,ww): v[row]+=wt
        out[f'ewma{hl}']=v/max(ww.sum(),1e-12)
    # gaps: high score = recently seen / due
    last=np.full(28, t+1, float)
    # scan max 500 backwards
    for age,row in enumerate(draws[max(0,t-500):t][::-1],start=1):
        for n in row:
            if last[n]>t: last[n]=age
    last[last>t]=501
    out['hotgap']=-last
    out['duegap']=np.minimum(last,100)
    # transition conditional to any member of previous draw, rolling 800 transitions
    if t>=2:
        prev=set(draws[t-1])
        start=max(1,t-800)
        num=np.zeros(28,float); den=0
        for j in range(start,t):
            if prev.intersection(draws[j-1]):
                num[draws[j]]+=1; den+=1
        out['transition']=num/max(1,den)
    else: out['transition']=np.zeros(28)
    return out

def main(hist_path,outdir,warmup=800):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    df=pd.read_csv(hist_path).sort_values('CONCURSO').reset_index(drop=True)
    draws=np.sort(df[['R1','R2','R3','R4','R5']].to_numpy(int),axis=1)-1
    names=['uniform']
    for base in [f'freq{w}' for w in WINDOWS]+[f'ewma{h}' for h in EWM_HL]+['hotgap','duegap','transition']:
        for b in BETAS: names.append(f'{base}_b{b:.2f}')
    logpost=np.full(len(names), -math.log(len(names)),float)
    rows=[]
    cum_mix=0.0; cum_best_fixed=None
    expert_cum=np.zeros(len(names),float)
    for t in range(max(warmup,2),len(df)):
        actual=draws[t]+1
        sig=signals(draws,t)
        ps=np.empty(len(names),float); ps[0]=1/U
        k=1
        for base in [f'freq{w}' for w in WINDOWS]+[f'ewma{h}' for h in EWM_HL]+['hotgap','duegap','transition']:
            for b in BETAS:
                ps[k]=p_set(sig[base],b,actual); k+=1
        m=np.max(logpost); post=np.exp(logpost-m); post/=post.sum()
        pmix=float(np.dot(post,ps))
        llr=math.log(pmix)+LOGU
        cum_mix+=llr
        expert_llr=np.log(ps)+LOGU
        expert_cum+=expert_llr
        topidx=np.argsort(post)[-5:][::-1]
        rows.append({'CONCURSO':int(df.loc[t,'CONCURSO']),'mix_p':pmix,'log_lift':llr,'cum_log_e':cum_mix,'e_value_cap':float(math.exp(min(50,cum_mix))), 'top_expert':names[topidx[0]],'top_weight':float(post[topidx[0]]),'best_expert_so_far':names[int(np.argmax(expert_cum))],'best_expert_cum_loge':float(expert_cum.max())})
        # Bayesian posterior update: fixed expert mixture, all based only on past before next target
        logpost += np.log(np.maximum(ps,1e-300))
        mm=np.max(logpost); logpost-=mm+math.log(np.exp(logpost-mm).sum())
    rd=pd.DataFrame(rows); rd.to_csv(outdir/'v264_prequential.csv',index=False)
    # final prospective PMF for next target
    t=len(df); sig=signals(draws,t)
    m=np.max(logpost); post=np.exp(logpost-m); post/=post.sum()
    combos=np.array(list(combinations(range(1,29),5)),dtype=np.int16)
    pmf=np.zeros(len(combos),float)
    pmf += post[0]*(1/U)
    k=1
    expert_meta=[]
    for base in [f'freq{w}' for w in WINDOWS]+[f'ewma{h}' for h in EWM_HL]+['hotgap','duegap','transition']:
        zz=z(sig[base])
        for b in BETAS:
            w=np.exp(b*zz); Z=e5(w)
            lp=np.log(w)[combos-1].sum(axis=1)-math.log(Z)
            pp=np.exp(lp)
            pmf += post[k]*pp
            expert_meta.append((names[k],float(post[k])))
            k+=1
    order=np.argsort(-pmf)
    top=order[:30]
    out=pd.DataFrame({'rank':np.arange(1,31),'combo':['-'.join(f'{x:02d}' for x in combos[i]) for i in top],'p_exact5':pmf[top],'lift_vs_uniform':pmf[top]*U})
    out.to_csv(outdir/f'v264_top30_target_{int(df.CONCURSO.max())+1}.csv',index=False)
    summary={'history_min':int(df.CONCURSO.min()),'history_max':int(df.CONCURSO.max()),'target':int(df.CONCURSO.max())+1,'warmup':warmup,'evaluated':len(rd),'cumulative_log_e':float(cum_mix),'e_value':float(math.exp(min(700,cum_mix))) if cum_mix<700 else float('inf'),'mean_log_lift':float(rd.log_lift.mean()),'positive_log_lift_rate':float((rd.log_lift>0).mean()),'posterior_uniform':float(post[0]),'top_posterior_experts':sorted([(names[i],float(post[i])) for i in range(len(names))],key=lambda x:-x[1])[:10],'top30_total_mass':float(pmf[top].sum()),'uniform_top30_mass':30/U,'top30_mass_lift':float(pmf[top].sum()/(30/U))}
    (outdir/'v264_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main('/mnt/data/model_inputs/Chispazo_12249.csv','/mnt/data/v264_anytime',800)
