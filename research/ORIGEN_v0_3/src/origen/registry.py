import json
from pathlib import Path
from .models import canonical_json
REQUIRED={"frame_id","domain","lens","representation","assumptions","observables","falsifiable_claim","null_or_rival","prospective_test","failure_conditions","status","version"}

def append_frames(path, frames):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); seen=set()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip(): seen.add(json.loads(line)["frame_id"])
    n=0
    with p.open("a",encoding="utf-8",newline="\n") as f:
        for frame in frames:
            if frame.frame_id not in seen:
                f.write(canonical_json(frame.to_dict())+"\n"); seen.add(frame.frame_id); n+=1
    return n

def audit_registry(path):
    p=Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    ids=set(); errors=[]; lenses={}; rows=0
    for no,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        rows+=1
        try:
            obj=json.loads(line); missing=REQUIRED-set(obj)
            if missing: errors.append({"line":no,"error":"missing_fields","fields":sorted(missing)})
            fid=obj.get("frame_id")
            if fid in ids: errors.append({"line":no,"error":"duplicate_frame_id","frame_id":fid})
            ids.add(fid); lens=obj.get("lens","UNKNOWN"); lenses[lens]=lenses.get(lens,0)+1
            for key in ("assumptions","observables","failure_conditions"):
                if not isinstance(obj.get(key),list) or not obj[key]: errors.append({"line":no,"error":"invalid_list","field":key})
        except Exception as e: errors.append({"line":no,"error":"invalid_json","detail":str(e)})
    return {"rows":rows,"unique_ids":len(ids),"lenses":lenses,"errors":errors,"state":"PASS" if rows and not errors else "BLOCKED"}
