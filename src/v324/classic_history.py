"""Build a conservative Chispazo Clásico-only history view from the canonical event ledger.

The canonical CSV does not carry a product/modality column. This module therefore
uses a documented inferred numbering rule only after the historical transition
to two consecutive daily draws; it never labels the earlier single-draw era.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

REQUIRED = {"CONCURSO", "FECHA", "R1", "R2", "R3", "R4", "R5"}
OFFICIAL_SOURCES = [
 "https://www.loterianacional.gob.mx/Chispazo/Chispazo",
 "https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-10-25.pdf",
 "https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-03.pdf",
 "https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-08.pdf",
 "https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-10.pdf",
 "https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-15.pdf",
]
OFFICIAL_ANCHORS = [
 {"contest":12333,"modality":"Chispazo de las Tres"},{"contest":12334,"modality":"Chispazo Clásico"},
 {"contest":12351,"modality":"Chispazo de las Tres"},{"contest":12352,"modality":"Chispazo Clásico"},
 {"contest":12361,"modality":"Chispazo de las Tres"},{"contest":12362,"modality":"Chispazo Clásico"},
 {"contest":12365,"modality":"Chispazo de las Tres"},{"contest":12366,"modality":"Chispazo Clásico"},
 {"contest":12375,"modality":"Chispazo de las Tres"},{"contest":12376,"modality":"Chispazo Clásico"},
]

def build_classic_history(history: pd.DataFrame, *, first_pair_contest: int = 5923):
    missing = REQUIRED - set(history.columns)
    if missing: raise ValueError(f"history missing columns: {sorted(missing)}")
    frame=history.copy()
    frame["CONCURSO"]=pd.to_numeric(frame["CONCURSO"],errors="raise")
    if (frame["CONCURSO"]%1!=0).any(): raise ValueError("contest IDs must be integers")
    frame["CONCURSO"]=frame["CONCURSO"].astype("int64")
    frame["FECHA"]=pd.to_datetime(frame["FECHA"],errors="raise").dt.strftime("%Y-%m-%d")
    if frame["CONCURSO"].duplicated().any(): raise ValueError("duplicate contest IDs")
    frame=frame.sort_values("CONCURSO").reset_index(drop=True)
    ids=frame["CONCURSO"].to_numpy()
    if len(ids)==0 or not (ids == range(int(ids[0]),int(ids[-1])+1)).all():
        raise ValueError("contest IDs must form one contiguous sequence")
    if first_pair_contest not in set(ids) or first_pair_contest%2!=1:
        raise ValueError("first paired contest must exist and be odd")
    pre=frame[frame["CONCURSO"]<first_pair_contest]
    if pre["FECHA"].duplicated().any(): raise ValueError("pre-transition single-draw era has duplicate dates")
    paired=frame[frame["CONCURSO"]>=first_pair_contest]
    date_groups=list(paired.groupby("FECHA",sort=True))
    if not date_groups: raise ValueError("no post-transition draws")
    for i,(date,group) in enumerate(date_groups):
        group_ids=group["CONCURSO"].sort_values().tolist()
        if len(group_ids)==1:
            final=(i==len(date_groups)-1 and group_ids[0]==int(ids[-1]) and group_ids[0]%2==1)
            if not final: raise ValueError(f"unpaired non-final contest on {date}: {group_ids}")
        elif len(group_ids)==2:
            if group_ids[0]%2!=1 or group_ids[1]!=group_ids[0]+1:
                raise ValueError(f"daily pair does not follow odd/even order on {date}: {group_ids}")
        else: raise ValueError(f"expected one or two contests on {date}, got {group_ids}")
    first_day=paired[paired["CONCURSO"]<=first_pair_contest+1]
    if first_day["CONCURSO"].tolist()!=[first_pair_contest,first_pair_contest+1] or first_day["FECHA"].nunique()!=1:
        raise ValueError("first paired day does not contain the expected consecutive contests")
    classic=paired[(paired["CONCURSO"]%2)==0].copy().reset_index(drop=True)
    if classic.empty or (classic["CONCURSO"]%2!=0).any(): raise ValueError("classic filter produced invalid contest IDs")
    manifest={
      "schema":"V324_CLASSIC_MODALITY_FILTER_V1",
      "classification":"INFERRED_FROM_DAILY_PAIR_ORDER_NOT_ROW_LEVEL_OFFICIAL_TAG",
      "first_paired_contest":int(first_pair_contest),
      "first_paired_date":str(first_day["FECHA"].iloc[0]),
      "rule":"From the first two-draw-per-date sequence onward, odd contest IDs are Chispazo de las Tres and even IDs are Chispazo Clásico; inferred from consecutive contest ordering and official schedule/result anchors.",
      "historical_single_draw_era":{"min_contest":int(pre["CONCURSO"].min()) if len(pre) else None,"max_contest":int(pre["CONCURSO"].max()) if len(pre) else None,"rows_excluded_as_unclassified":int(len(pre))},
      "post_transition":{"min_contest":int(paired["CONCURSO"].min()),"max_contest":int(paired["CONCURSO"].max()),"rows":int(len(paired)),"date_groups":int(len(date_groups)),"classic_rows_selected":int(len(classic)),"classic_min_contest":int(classic["CONCURSO"].min()),"classic_max_contest":int(classic["CONCURSO"].max()),"final_unpaired_odd_contest_excluded":int(ids[-1]) if ids[-1]%2 else None},
      "official_numbering_anchors":OFFICIAL_ANCHORS,"official_sources":OFFICIAL_SOURCES,
      "limitations":["The canonical history CSV has no official modality column or per-row source tag.","The parity mapping is an inference from the uninterrupted paired sequence plus official schedule/result examples; it is not an individually source-verified classification of every historical row.","Rows before the first paired date are excluded rather than assigned a modality.","This filter supports a research-only sensitivity analysis and cannot authorize betting or model promotion."]
    }
    return classic,manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",required=True); p.add_argument("--out-history",required=True); p.add_argument("--manifest",required=True)
    p.add_argument("--first-pair-contest",type=int,default=5923); a=p.parse_args()
    classic,manifest=build_classic_history(pd.read_csv(a.history),first_pair_contest=a.first_pair_contest)
    Path(a.out_history).parent.mkdir(parents=True,exist_ok=True); Path(a.manifest).parent.mkdir(parents=True,exist_ok=True)
    classic.to_csv(a.out_history,index=False); Path(a.manifest).write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2))
if __name__=="__main__": main()
