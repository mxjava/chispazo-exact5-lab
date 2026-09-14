import importlib.util, pandas as pd, numpy as np, math, json
spec=importlib.util.spec_from_file_location('v','/mnt/data/v264_exactset_anytime.py'); v=importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
df=pd.read_csv('/mnt/data/model_inputs/Chispazo_12249.csv').sort_values('CONCURSO').reset_index(drop=True)
draws=np.sort(df[['R1','R2','R3','R4','R5']].to_numpy(int),axis=1)-1
names=['uniform']
for base in [f'freq{w}' for w in v.WINDOWS]+[f'ewma{h}' for h in v.EWM_HL]+['hotgap','duegap','transition']:
 for b in v.BETAS:names.append(f'{base}_b{b:.2f}')
horizons=[100,250,500,1000,2000]
states={h:{'lp':np.full(len(names),-math.log(len(names))), 'cum':0.0,'pos':0,'n':0} for h in horizons}
start=len(df)-max(horizons)
for t in range(start,len(df)):
 actual=draws[t]+1; sig=v.signals(draws,t)
 ps=np.empty(len(names)); ps[0]=1/v.U; k=1
 for base in [f'freq{w}' for w in v.WINDOWS]+[f'ewma{hh}' for hh in v.EWM_HL]+['hotgap','duegap','transition']:
  for b in v.BETAS: ps[k]=v.p_set(sig[base],b,actual); k+=1
 for h,s in states.items():
  if t < len(df)-h: continue
  lp=s['lp']; m=lp.max(); post=np.exp(lp-m);post/=post.sum();pm=float(post@ps);ll=math.log(pm)+v.LOGU
  s['cum']+=ll;s['pos']+=(ll>0);s['n']+=1
  lp += np.log(np.maximum(ps,1e-300)); mm=lp.max();lp-=mm+math.log(np.exp(lp-mm).sum())
out={}
for h,s in states.items():
 lp=s['lp'];m=lp.max();post=np.exp(lp-m);post/=post.sum()
 out[h]={'cum_log_e':s['cum'],'e_value':math.exp(min(700,s['cum'])),'mean_log_lift':s['cum']/s['n'],'positive_rate':s['pos']/s['n'],'posterior_uniform':float(post[0]),'top':sorted([(names[i],float(post[i])) for i in range(len(names))],key=lambda x:-x[1])[:5]}
print(json.dumps(out,indent=2));open('/mnt/data/v264_recent_windows.json','w').write(json.dumps(out,indent=2))
