from __future__ import annotations
from pathlib import Path
import argparse, json


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--registration",required=True)
    ap.add_argument("--result",required=True,nargs=5,type=int)
    ap.add_argument("--out")
    a=ap.parse_args()
    reg=json.loads(Path(a.registration).read_text(encoding="utf-8"))
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
