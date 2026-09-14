from __future__ import annotations
from pathlib import Path
import argparse, hashlib, json
from datetime import datetime, timezone
import pandas as pd


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_lines(df: pd.DataFrame) -> list[str]:
    if "combo" in df.columns:
        vals = df["combo"].astype(str).tolist()
    else:
        cols = [c for c in ["R1","R2","R3","R4","R5","n1","n2","n3","n4","n5"] if c in df.columns]
        if len(cols) < 5:
            raise ValueError("portfolio requires combo or five number columns")
        cols = cols[:5]
        vals = ["-".join(map(str,row)) for row in df[cols].itertuples(index=False, name=None)]
    out=[]
    for v in vals:
        parts=[int(x) for x in v.replace(","," ").replace("-"," ").split()]
        if len(parts)!=5 or len(set(parts))!=5 or any(x<1 or x>28 for x in parts):
            raise ValueError(f"invalid combo: {v}")
        out.append("-".join(f"{x:02d}" for x in sorted(parts)))
    if len(out)!=30 or len(set(out))!=30:
        raise ValueError(f"portfolio must contain exactly 30 distinct lines; got rows={len(out)}, unique={len(set(out))}")
    return out


def main() -> int:
    ap=argparse.ArgumentParser(description="Freeze an immutable pre-sorteo 30-line registration")
    ap.add_argument("--target",type=int,required=True)
    ap.add_argument("--portfolio",required=True)
    ap.add_argument("--preflight",required=True)
    ap.add_argument("--model-version",required=True)
    ap.add_argument("--ledger-dir",default="data/prospective-ledger")
    a=ap.parse_args()
    pre=json.loads(Path(a.preflight).read_text(encoding="utf-8"))
    if pre.get("state")!="PASS":
        raise SystemExit("Refusing freeze: preflight state is not PASS")
    lines=normalize_lines(pd.read_csv(a.portfolio))
    ledger=Path(a.ledger_dir); ledger.mkdir(parents=True,exist_ok=True)
    dest=ledger/f"target_{a.target}.json"
    if dest.exists():
        raise SystemExit(f"Immutable registration already exists: {dest}")
    payload={
      "target":a.target,
      "registered_at_utc":datetime.now(timezone.utc).isoformat(),
      "model_version":a.model_version,
      "history_max":pre.get("inputs",{}).get("history",{}).get("contest_max"),
      "history_sha256":pre.get("inputs",{}).get("history",{}).get("sha256"),
      "ranking_sha256":pre.get("inputs",{}).get("ranking",{}).get("sha256"),
      "preflight_state":"PASS",
      "lines":lines,
    }
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    payload["registration_sha256"]=sha256_bytes(canonical)
    dest.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8")
    print(dest)
    print(payload["registration_sha256"])
    return 0

if __name__=="__main__":
    raise SystemExit(main())
