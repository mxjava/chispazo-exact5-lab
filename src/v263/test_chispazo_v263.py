import importlib.util, itertools, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v263',HERE/'CHISPAZO_V263_INTEGRITY_ISLAND_DRO.py')
v=importlib.util.module_from_spec(spec); sys.modules['v263']=v; spec.loader.exec_module(v)

def synthetic_df(live=True):
    cs=list(itertools.combinations(range(1,29),5))
    n=len(cs); x=np.arange(n,dtype=float)
    d={'rank':np.arange(1,n+1),'combo':[v.combo_text(c) for c in cs],'score':np.sin(x/97.0)}
    for k,c in enumerate(v.EXACT5_COLUMNS):
        d[c]=np.cos(x/(31.0+k*7)) if live else np.zeros(n)
    for k,c in enumerate(v.SUPPORT_COLUMNS): d[c]=np.sin(x/(43.0+k*11))
    return pd.DataFrame(d)

def test_dead_exact5_hard_fails():
    h=v.parent_health_audit(synthetic_df(False),v.V263Config())
    assert h['state']=='HARD_FAIL_EXACT5' and h['live_exact5_count']==0

def test_live_exact5_passes():
    h=v.parent_health_audit(synthetic_df(True),v.V263Config())
    assert h['state']=='PASS' and h['live_exact5_count']==5

def test_islands_reach_beyond_parent_head():
    d=synthetic_df(True); h=v.parent_health_audit(d,v.V263Config())
    pool,m=v.candidate_islands(d,h,v.V263Config(parent_head_rank=30,exact5_island_rank=100,support_island_rank=50))
    assert len(pool)>=100 and m['outside_parent_head']>0

def test_null_hedge_balance_and_pair_cap():
    d=synthetic_df(False); h=v.parent_health_audit(d,v.V263Config())
    cfg=v.V263Config(hedge_iterations=50000,hedge_restarts=4)
    p,m,_=v.null_hedge(d,h,12250,cfg)
    assert len(p)==30 and p.combo.nunique()==30
    assert m['min_number_exposure']==5 and m['max_number_exposure']==6
    assert m['max_pair_repeat']<=2
    assert m['unique_pairs']>=285

def test_null_hedge_deterministic():
    d=synthetic_df(False); h=v.parent_health_audit(d,v.V263Config())
    cfg=v.V263Config(hedge_iterations=20000,hedge_restarts=2)
    a,_,_=v.null_hedge(d,h,999,cfg); b,_,_=v.null_hedge(d,h,999,cfg)
    assert a.combo.tolist()==b.combo.tolist()

if __name__=='__main__':
    tests=[x for k,x in sorted(globals().items()) if k.startswith('test_')]
    for t in tests:
        t(); print('PASS',t.__name__)
    print(f'{len(tests)}/{len(tests)} PASS')
