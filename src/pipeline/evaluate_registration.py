from __future__ import annotations
from pathlib import Path
import argparse, hashlib, hmac, json, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def verify_registration_payload(reg: dict) -> bool:
    """Reject altered or structurally invalid prospective registrations before scoring."""
    if not isinstance(reg, dict):
        return False
    claimed = reg.get("registration_sha256")
    if not isinstance(claimed, str) or not re.fullmatch(r"[0-9a-f]{64}", claimed):
        return False
    target = reg.get("target")
    if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
        return False
    if reg.get("history_max") != target - 1 or reg.get("preflight_state") != "PASS":
        return False
    if not isinstance(reg.get("model_version"), str) or not reg["model_version"].strip():
        return False
    if not isinstance(reg.get("commit_sha"), str) or not re.fullmatch(r"[0-9a-f]{40}", reg["commit_sha"]):
        return False
    for key in ("history_sha256", "ranking_sha256"):
        if not isinstance(reg.get(key), str) or not re.fullmatch(r"[0-9a-f]{64}", reg[key]):
            return False
    try:
        utc_dt = datetime.fromisoformat(str(reg.get("registered_at_utc", "")).replace("Z", "+00:00"))
        local_dt = datetime.fromisoformat(str(reg.get("registered_at_mexico_city", "")).replace("Z", "+00:00"))
        mexico_zone = ZoneInfo("America/Mexico_City")
        if utc_dt.tzinfo is None or local_dt.tzinfo is None:
            return False
        if utc_dt.utcoffset() != timezone.utc.utcoffset(utc_dt):
            return False
        if local_dt.utcoffset() != mexico_zone.utcoffset(local_dt):
            return False
        if utc_dt.astimezone(timezone.utc) != local_dt.astimezone(timezone.utc):
            return False
    except (ValueError, OverflowError):
        return False
    lines = reg.get("lines")
    if not isinstance(lines, list) or len(lines) != 30:
        return False
    normalized = []
    for line in lines:
        if not isinstance(line, str):
            return False
        parts = line.split("-")
        if len(parts) != 5 or any(not re.fullmatch(r"\d{2}", p) for p in parts):
            return False
        nums = [int(p) for p in parts]
        if nums != sorted(nums) or len(set(nums)) != 5 or any(n < 1 or n > 28 for n in nums):
            return False
        normalized.append(line)
    if len(set(normalized)) != 30:
        return False
    unsigned = {key: value for key, value in reg.items() if key != "registration_sha256"}
    canonical = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hmac.compare_digest(claimed, hashlib.sha256(canonical).hexdigest())


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--registration",required=True)
    ap.add_argument("--result",required=True,nargs=5,type=int)
    ap.add_argument("--out")
    a=ap.parse_args()
    reg=json.loads(Path(a.registration).read_text(encoding="utf-8"))
    if not verify_registration_payload(reg):
        raise SystemExit("invalid or tampered prospective registration: schema/checksum verification failed")
    result=set(a.result)
    if len(result)!=5 or any(n<1 or n>28 for n in result):
        raise SystemExit("invalid result")
    scores=[]
    for line in reg["lines"]:
        s=set(int(x) for x in line.split("-"))
        scores.append({"combo":line,"hits":len(s & result)})
    scores.sort(key=lambda x:(-x["hits"],x["combo"]))
    report={"target":reg["target"],"result":"-".join(f"{x:02d}" for x in sorted(result)),"best_hits":scores[0]["hits"],"exact5":sum(x["hits"]==5 for x in scores),"lines":scores}
    text=json.dumps(report,indent=2,ensure_ascii=False)
    print(text)
    if a.out: Path(a.out).write_text(text,encoding="utf-8")
    return 0

if __name__=="__main__": raise SystemExit(main())
