from __future__ import annotations
from pathlib import Path
import argparse
import csv
from datetime import datetime, timezone
import pandas as pd

PRIMES = {2,3,5,7,11,13,17,19,23}

def main() -> int:
    ap = argparse.ArgumentParser(description="Append one externally verified Chispazo result without breaking causal history")
    ap.add_argument("--history", required=True)
    ap.add_argument("--contest", required=True, type=int)
    ap.add_argument("--date", required=True, help="YYYY-MM-DD")
    ap.add_argument("--numbers", required=True, nargs=5, type=int)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--provenance", default="data/history/provenance.csv")
    a = ap.parse_args()

    p = Path(a.history)
    df = pd.read_csv(p)
    cc = "CONCURSO" if "CONCURSO" in df.columns else "concurso"
    ncols = [c for c in ["R1","R2","R3","R4","R5"] if c in df.columns]
    if len(ncols) != 5:
        raise SystemExit("History must contain R1..R5")
    mx = int(pd.to_numeric(df[cc]).max())
    if a.contest != mx + 1:
        raise SystemExit(f"Refusing append: contest={a.contest}, expected exactly {mx+1}")
    nums = sorted(a.numbers)
    if len(set(nums)) != 5 or any(n < 1 or n > 28 for n in nums):
        raise SystemExit("Numbers must be 5 distinct integers in 1..28")
    pd.to_datetime(a.date, format="%Y-%m-%d", errors="raise")

    prev = set(pd.to_numeric(df.sort_values(cc, ascending=False).iloc[0][ncols]).astype(int).tolist())
    row = {c: pd.NA for c in df.columns}
    row[cc] = a.contest
    if "ID" in row: row["ID"] = pd.NA
    for c,n in zip(ncols, nums): row[c] = n
    if "FECHA" in row: row["FECHA"] = a.date
    if "PRIMOS" in row: row["PRIMOS"] = sum(n in PRIMES for n in nums)
    if "REPETIDOS" in row: row["REPETIDOS"] = len(prev.intersection(nums))
    if "MEDIA" in row: row["MEDIA"] = sum(nums)/5.0
    out = pd.concat([pd.DataFrame([row]), df], ignore_index=True)
    out.to_csv(p, index=False)

    prov = Path(a.provenance)
    prov.parent.mkdir(parents=True, exist_ok=True)
    exists = prov.exists()
    with prov.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["contest","date","numbers","source_url","verified_at_utc"])
        w.writerow([a.contest, a.date, "-".join(f"{n:02d}" for n in nums), a.source_url, datetime.now(timezone.utc).isoformat()])
    print(f"Appended contest {a.contest}: {nums}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
