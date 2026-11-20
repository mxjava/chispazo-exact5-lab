"""Tamper-evident hash-chained research event ledger.

A local hash chain detects edits, reordering and interior deletion. It cannot
prove that an unlogged event never occurred; external custody is still required.
"""
from pathlib import Path
from typing import Any
import json, hashlib

GENESIS = "0" * 64

def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def append_event(path: str | Path, event: dict[str, Any]) -> str:
    required={"event_id","timestamp_utc","event_type","frame_id","details"}
    missing=required-set(event)
    if missing: raise ValueError("missing_fields:"+",".join(sorted(missing)))
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    previous=GENESIS
    if p.exists() and p.stat().st_size:
        audit=audit_ledger(p)
        if audit["state"] != "PASS":
            raise ValueError("cannot_append_to_invalid_or_legacy_ledger")
        last=json.loads(p.read_text(encoding="utf-8").splitlines()[-1])
        if last["event"]["event_id"] == event["event_id"] or any(
            json.loads(line)["event"]["event_id"] == event["event_id"]
            for line in p.read_text(encoding="utf-8").splitlines()[:-1]
        ):
            raise ValueError("duplicate_event_id")
        previous=last["chain_sha256"]
    payload=_canonical(event)
    event_digest=hashlib.sha256(payload.encode("utf-8")).hexdigest()
    chain_digest=hashlib.sha256((previous+event_digest).encode("ascii")).hexdigest()
    record={"event":event,"event_sha256":event_digest,
            "previous_chain_sha256":previous,"chain_sha256":chain_digest,
            "ledger_schema":"ORIGEN_CHAIN_V1"}
    with p.open("a",encoding="utf-8",newline="\n") as f:
        f.write(_canonical(record)+"\n")
    return chain_digest

def audit_ledger(path: str | Path) -> dict:
    p=Path(path)
    if not p.exists(): raise FileNotFoundError(p)
    errors=[]; count=0; seen=set(); previous=GENESIS; legacy=False
    for line_no,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
        try:
            row=json.loads(line); event=row["event"]
            digest=hashlib.sha256(_canonical(event).encode("utf-8")).hexdigest()
            if digest != row.get("event_sha256"):
                errors.append({"line":line_no,"error":"event_hash_mismatch"})
            if event["event_id"] in seen:
                errors.append({"line":line_no,"error":"duplicate_event_id"})
            seen.add(event["event_id"])
            if row.get("ledger_schema") != "ORIGEN_CHAIN_V1":
                legacy=True
                errors.append({"line":line_no,"error":"legacy_unanchored_event"})
            else:
                if row.get("previous_chain_sha256") != previous:
                    errors.append({"line":line_no,"error":"chain_link_mismatch"})
                expected=hashlib.sha256((previous+digest).encode("ascii")).hexdigest()
                if row.get("chain_sha256") != expected:
                    errors.append({"line":line_no,"error":"chain_hash_mismatch"})
                previous=row.get("chain_sha256","")
            count+=1
        except Exception as exc:
            errors.append({"line":line_no,"error":"invalid_event","detail":str(exc)})
    state="PASS" if count and not errors else "BLOCKED"
    return {"events":count,"errors":errors,"legacy_ledger":legacy,
            "final_chain_sha256":previous,"state":state,
            "interpretation":"Hash chaining detects changes within the retained file, but independent external custody is required to detect complete-file replacement or omitted real-world events."}
