import pandas as pd
import pytest
from src.v324.classic_history import build_classic_history

def _history():
    return pd.DataFrame([
      {"CONCURSO":5921,"FECHA":"2017-09-24","R1":1,"R2":2,"R3":3,"R4":4,"R5":5},
      {"CONCURSO":5922,"FECHA":"2017-09-25","R1":1,"R2":2,"R3":3,"R4":4,"R5":5},
      {"CONCURSO":5923,"FECHA":"2017-09-26","R1":1,"R2":2,"R3":3,"R4":4,"R5":5},
      {"CONCURSO":5924,"FECHA":"2017-09-26","R1":2,"R2":3,"R3":4,"R4":5,"R5":6},
      {"CONCURSO":5925,"FECHA":"2017-09-27","R1":1,"R2":2,"R3":3,"R4":4,"R5":5},
    ])

def test_filter_selects_even_ids_and_excludes_legacy_and_final_odd():
    classic,manifest=build_classic_history(_history(),first_pair_contest=5923)
    assert classic.CONCURSO.tolist()==[5924]
    assert manifest["historical_single_draw_era"]["rows_excluded_as_unclassified"]==2
    assert manifest["post_transition"]["final_unpaired_odd_contest_excluded"]==5925
    assert manifest["classification"].startswith("INFERRED_")

def test_rejects_duplicate_ids():
    frame=pd.concat([_history(),_history().iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match="duplicate contest"): build_classic_history(frame,first_pair_contest=5923)

def test_rejects_nonconsecutive_or_wrong_order_pair():
    frame=_history(); frame.loc[frame.CONCURSO==5924,"CONCURSO"]=5926
    with pytest.raises(ValueError): build_classic_history(frame,first_pair_contest=5923)

def test_rejects_nonfinal_unpaired_draw_after_transition():
    frame=_history(); frame.loc[frame.CONCURSO==5924,"FECHA"]="2017-09-28"
    with pytest.raises(ValueError,match="unpaired"): build_classic_history(frame,first_pair_contest=5923)
