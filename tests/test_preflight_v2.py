from pathlib import Path
import json
import pandas as pd
from src.validation.preflight_v2 import validate_history, validate_ranking, EXACT5_UNIVERSE


def test_history_requires_target_minus_one(tmp_path: Path):
    p=tmp_path/'h.csv'
    pd.DataFrame({'CONCURSO':[102,101,100],'R1':[1,2,3],'R2':[4,5,6],'R3':[7,8,9],'R4':[10,11,12],'R5':[13,14,15],'FECHA':['2026-01-03','2026-01-02','2026-01-01']}).to_csv(p,index=False)
    checks,_=validate_history(p,103)
    m={c.name:c.status for c in checks}
    assert m['history_ends_at_target_minus_1']=='PASS'
    checks,_=validate_history(p,104)
    m={c.name:c.status for c in checks}
    assert m['history_ends_at_target_minus_1']=='FAIL'


def test_ranking_rejects_partial_universe(tmp_path: Path):
    p=tmp_path/'r.csv'
    pd.DataFrame({'combo':['01-02-03-04-05','01-02-03-04-06'],'score_ltr_ndcg_exact5':[0.1,0.2],'score_ltr_exact5_balanced':[0.2,0.3]}).to_csv(p,index=False)
    checks,_=validate_ranking(p)
    m={c.name:c.status for c in checks}
    assert m['ranking_full_universe']=='FAIL'
    assert EXACT5_UNIVERSE==98280
