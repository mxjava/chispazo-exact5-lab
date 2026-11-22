#!/usr/bin/env python3
"""Run the existing V263 fail-closed structural hedge path (operational entrypoint v1).

This intentionally creates no model prediction: the repository currently has
no current, source-verified Clásico history or healthy 98,280-row parent score
matrix. The generated universe is used only to exercise V263's explicit
DEGRADED_NULL_HEDGE path and produce a balanced 30-line coverage artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import pandas as pd

from src.v263.CHISPAZO_V263_INTEGRITY_ISLAND_DRO import V263Config, run


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--seed", type=int, default=777)
    ap.add_argument("--iterations", type=int, default=30000)
    ap.add_argument("--restarts", type=int, default=4)
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    universe = out / "temporary_complete_universe.csv"
    combos = ("-".join(f"{n:02d}" for n in c)
              for c in itertools.combinations(range(1, 29), 5))
    pd.DataFrame({"combo": list(combos)}).to_csv(universe, index=False)

    cfg = V263Config(seed=args.seed, hedge_iterations=args.iterations,
                     hedge_restarts=args.restarts)
    try:
        rc = run(universe, args.target, out, cfg, allow_degraded_hedge=True)
    finally:
        universe.unlink(missing_ok=True)
    if rc != 0:
        raise SystemExit(rc)

    portfolio = out / f"v263_DEGRADED_NULL_HEDGE_30_target_{args.target}.csv"
    manifest = out / f"v263_manifest_target_{args.target}.json"
    report = {
        "schema": "EXACT5_OPERATIONAL_NULL_HEDGE_RUN_V1",
        "target_label_only": args.target,
        "state": "RESEARCH_ONLY_NULL_HEDGE_NOT_A_PREDICTION",
        "engine": "V263 existing null_hedge implementation",
        "portfolio_file": portfolio.name,
        "portfolio_sha256": sha256(portfolio),
        "manifest_file": manifest.name,
        "manifest_sha256": sha256(manifest),
        "lines": int(len(pd.read_csv(portfolio))),
        "source_history_used": False,
        "source_parent_scores_used": False,
        "canonical_history_modified": False,
        "v294_modified": False,
        "production_authorized": False,
        "limitations": [
            "This is a structural coverage hedge, not a predictive ranking.",
            "It has exactly the same 30/98,280 exact-5 probability mass as any other 30 distinct lines under the uniform null.",
            "The target is a label only; no pre-close timestamp or independent custody receipt is created.",
            "Do not submit this artifact as an authenticated prospective registration."
        ]
    }
    report_path = out / f"operational_run_target_{args.target}.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sums = out / "SHA256SUMS.txt"
    sums.write_text(
        f"{sha256(portfolio)}  {portfolio.name}\n"
        f"{sha256(manifest)}  {manifest.name}\n"
        f"{sha256(report_path)}  {report_path.name}\n",
        encoding="ascii"
    )
    print(json.dumps(report, indent=2))
    print(pd.read_csv(portfolio).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
