from pathlib import Path
from typing import Any
import json, hashlib

def append_event(path: str | Path, event: dict[str, Any]) -> str:
    required={"event_id","timestamp_utc","event_type","frame_id","details"}; missing=required-set(event)
    if missing: raise ValueError("missing_fields:"+",".join(sorted(missing)))
    payload=json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    digest=hashlib.sha256(payload.encode("utf-8")).hexdigest(); p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps({"event":event,"event_sha256":digest},ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
    return digest

def audit_ledger(path: str | Path) -> dict:
    p=Path(path); errors=[]; count=0; seen=set()
    if not p.exists(): raise FileNotFoundError(p)
    for line_no,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
        try:
            row=json.loads(line); event=row["event"]
            payload=json.dumps(event,ensure_ascii=False,sort_keys=True,separators=(",",":"))
            actual=hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if actual!=row["event_sha256"]: errors.append({"line":line_no,"error":"hash_mismatch"})
            if event["event_id"] in seen: errors.append({"line":line_no,"error":"duplicate_event_id"})
            seen.add(event["event_id"]); count+=1
        except Exception as exc: errors.append({"line":line_no,"error":"invalid_event","detail":str(exc)})
    return {"events":count,"errors":errors,"state":"PASS" if count and not errors else "BLOCKED"}
