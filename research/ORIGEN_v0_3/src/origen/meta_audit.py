"""MetaObserver checks for temporal validity of the recorded search path."""
from __future__ import annotations
from datetime import datetime
import json
from pathlib import Path
from .search_ledger import audit_ledger

OUTCOME_ACCESS = {"outcome_access", "result_viewed", "test_outcome_access"}
ADAPTIVE_CHANGES = {"metric_changed", "hypothesis_generated", "frame_dropped", "exclusion_rule_changed", "primary_outcome_changed", "search_parameter_changed", "model_family_changed"}
PREREG_EVENTS = {"protocol_preregistered", "protocol_sealed"}

def audit_search_path(path: str | Path) -> dict:
    integrity = audit_ledger(path)
    events = [json.loads(line)["event"] for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    findings, timestamps = [], []
    for i, event in enumerate(events):
        ts = event.get("timestamp_utc", "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None: findings.append({"severity":"BLOCKER","type":"timestamp_without_timezone","event_id":event.get("event_id")})
            timestamps.append((dt, i, event))
        except Exception: findings.append({"severity":"BLOCKER","type":"invalid_timestamp","event_id":event.get("event_id")})
    for (a, _, ea), (b, _, eb) in zip(timestamps, timestamps[1:]):
        if b < a: findings.append({"severity":"BLOCKER","type":"non_monotonic_event_time","event_ids":[ea.get("event_id"),eb.get("event_id")]})
    first_access = next((i for i,e in enumerate(events) if e.get("event_type") in OUTCOME_ACCESS), None)
    prereg_indices = [i for i,e in enumerate(events) if e.get("event_type") in PREREG_EVENTS]
    if first_access is None: findings.append({"severity":"WARNING","type":"no_outcome_access_event_recorded"})
    elif not prereg_indices or min(prereg_indices) > first_access: findings.append({"severity":"BLOCKER","type":"outcome_access_before_preregistration"})
    else:
        for i,event in enumerate(events):
            if i > first_access and event.get("event_type") in ADAPTIVE_CHANGES:
                findings.append({"severity":"EXPLORATORY_ONLY","type":"post_outcome_adaptation","event_id":event.get("event_id"),"event_type":event.get("event_type")})
    blockers=[x for x in findings if x["severity"]=="BLOCKER"]
    state="BLOCKED" if integrity["state"]!="PASS" or blockers else "REVIEW_REQUIRED" if findings else "PASS"
    return {"state":state,"ledger_integrity":integrity["state"],"events":len(events),"first_outcome_access_index":first_access,"findings":findings,
            "interpretation":"A hash-valid ledger is not proof that every search action was logged. Post-outcome adaptations are exploratory and cannot be retroactively preregistered."}
