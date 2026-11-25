"""Read-only Exact5 adapter: audits history and proposes tests, never predicts or edits source data."""
import argparse,csv,json
from collections import Counter
from pathlib import Path
from .catalog import generate_frames
from .registry import append_frames
from .manifest import sha256_file

CANONICAL_SHA256="5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a"
NUMBER_COLUMNS=("R1","R2","R3","R4","R5")

def load_and_audit_history(path,expected_sha256=CANONICAL_SHA256):
    p=Path(path)
    if not p.is_file(): raise FileNotFoundError(p)
    digest=sha256_file(p)
    if expected_sha256 and digest!=expected_sha256: raise ValueError("canonical_history_hash_mismatch")
    rows=[]
    with p.open("r",encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not {"CONCURSO",*NUMBER_COLUMNS}.issubset(set(reader.fieldnames)): raise ValueError("history_missing_required_columns")
        for line,row in enumerate(reader,2):
            try: contest=int(row["CONCURSO"]); nums=[int(row[c]) for c in NUMBER_COLUMNS]
            except Exception as exc: raise ValueError(f"invalid_numeric_value_line_{line}") from exc
            if contest<=0 or len(set(nums))!=5 or any(n<1 or n>28 for n in nums): raise ValueError(f"invalid_draw_line_{line}")
            rows.append({"contest":contest,"numbers":sorted(nums),"date":row.get("FECHA","")})
    contests=[r["contest"] for r in rows]
    if not rows: raise ValueError("empty_history")
    if len(contests)!=len(set(contests)): raise ValueError("duplicate_contest")
    if sorted(contests)!=list(range(min(contests),max(contests)+1)): raise ValueError("non_contiguous_contests")
    return {"state":"PASS","path":str(p),"sha256":digest,"rows":len(rows),"contest_min":min(contests),"contest_max":max(contests),"order_in_file":"descending" if contests[0]>contests[-1] else "ascending","chronological_draws":sorted(rows,key=lambda x:x["contest"]),"mutated_source":False}

def descriptive_diagnostics(draws):
    freq=Counter(n for d in draws for n in d["numbers"]); sums=[sum(d["numbers"]) for d in draws]
    parity=Counter(sum(n%2 for n in d["numbers"]) for d in draws)
    overlap=Counter(len(set(a["numbers"])&set(b["numbers"])) for a,b in zip(draws,draws[1:])); n=len(draws)
    return {"draws":n,"number_frequency":{str(k):freq[k] for k in range(1,29)},"sum_mean":sum(sums)/n,"sum_min":min(sums),"sum_max":max(sums),"odd_count_distribution":{str(k):parity[k] for k in range(6)},"consecutive_draw_overlap":{str(k):overlap[k] for k in range(6)},"interpretation":"Descriptive retrospective statistics only. No p-values, predictive ranking, or evidence of edge are produced."}

def build_research_packet(history_path,output_dir,expected_sha256=CANONICAL_SHA256):
    audit=load_and_audit_history(history_path,expected_sha256); draws=audit.pop("chronological_draws")
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True); frames=generate_frames("Chispazo Clasico 5-of-28",10)
    registry=out/"origen_frames.jsonl"; added=append_frames(registry,frames)
    packet={"schema_version":"1.0","classification":"RESEARCH_ONLY_NO_EDGE","history_audit":audit,"descriptive_diagnostics":descriptive_diagnostics(draws),"frames_generated":len(frames),"frames_added":added,"registry_path":str(registry),"v294_modified":False,"canonical_history_modified":False,"model_promotion":False,"next_step":"Freeze one protocol before any untouched prospective outcomes are accessed."}
    (out/"research_packet.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return packet

def main():
    p=argparse.ArgumentParser(); p.add_argument("--history",required=True); p.add_argument("--out",required=True); p.add_argument("--allow-noncanonical-hash",action="store_true"); a=p.parse_args()
    expected=None if a.allow_noncanonical_hash else CANONICAL_SHA256
    print(json.dumps(build_research_packet(a.history,a.out,expected),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
