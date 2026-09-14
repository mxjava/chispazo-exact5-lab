from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import argparse
import json
import math
import pandas as pd

NUM_MIN = 1
NUM_MAX = 28
DRAW_SIZE = 5
EXACT5_UNIVERSE = math.comb(NUM_MAX, DRAW_SIZE)

@dataclass
class Check:
    name: str
    status: str
    detail: str
    critical: bool = True


def _detect_number_columns(df: pd.DataFrame) -> list[str]:
    candidates = []
    for pattern in [
        ["r1", "r2", "r3", "r4", "r5"],
        ["n1", "n2", "n3", "n4", "n5"],
        ["num1", "num2", "num3", "num4", "num5"],
        ["numero1", "numero2", "numero3", "numero4", "numero5"],
    ]:
        if all(c in df.columns for c in pattern):
            return pattern
    # last resort: first five numeric-ish columns excluding contest/date identifiers
    banned = {"concurso", "contest", "id", "fecha", "date", "sorteo"}
    for c in df.columns:
        if c.lower() in banned:
            continue
        try:
            pd.to_numeric(df[c].dropna().head(20))
            candidates.append(c)
        except Exception:
            pass
    return candidates[:5]


def validate_history(history: Path, target: int | None) -> tuple[list[Check], pd.DataFrame]:
    checks: list[Check] = []
    try:
        df = pd.read_csv(history)
        checks.append(Check("history_readable", "PASS", f"rows={len(df)}"))
    except Exception as exc:
        return [Check("history_readable", "FAIL", repr(exc))], pd.DataFrame()

    contest_col = next((c for c in ["concurso", "contest", "CONCURSO"] if c in df.columns), None)
    if contest_col is None:
        checks.append(Check("contest_column", "FAIL", "No contest column found"))
    else:
        s = pd.to_numeric(df[contest_col], errors="coerce")
        bad = int(s.isna().sum())
        dup = int(s.duplicated().sum())
        checks.append(Check("contest_numeric", "PASS" if bad == 0 else "FAIL", f"invalid={bad}"))
        checks.append(Check("contest_unique", "PASS" if dup == 0 else "FAIL", f"duplicates={dup}"))
        if target is not None and bad == 0:
            future = int((s >= target).sum())
            checks.append(Check("no_future_leakage", "PASS" if future == 0 else "FAIL", f"rows_with_contest>=target={future}"))

    ncols = _detect_number_columns(df)
    if len(ncols) != 5:
        checks.append(Check("number_columns", "FAIL", f"detected={ncols}"))
    else:
        vals = df[ncols].apply(pd.to_numeric, errors="coerce")
        nulls = int(vals.isna().sum().sum())
        out_of_range = int(((vals < NUM_MIN) | (vals > NUM_MAX)).sum().sum())
        duplicate_rows = int(sum(len(set(row.dropna().astype(int))) != DRAW_SIZE for _, row in vals.iterrows()))
        checks.append(Check("numbers_numeric", "PASS" if nulls == 0 else "FAIL", f"invalid_cells={nulls}"))
        checks.append(Check("numbers_range_1_28", "PASS" if out_of_range == 0 else "FAIL", f"out_of_range={out_of_range}"))
        checks.append(Check("five_unique_numbers", "PASS" if duplicate_rows == 0 else "FAIL", f"bad_rows={duplicate_rows}"))

    return checks, df


def validate_ranking(ranking: Path | None) -> list[Check]:
    if ranking is None:
        return [Check("exact5_ranking_present", "FAIL", "No ranking supplied")]
    try:
        df = pd.read_csv(ranking)
    except Exception as exc:
        return [Check("exact5_ranking_present", "FAIL", repr(exc))]

    checks = [Check("exact5_ranking_present", "PASS", f"rows={len(df)}")]
    score_cols = [c for c in df.columns if "exact5" in c.lower() and "score" in c.lower()]
    if not score_cols:
        checks.append(Check("exact5_scores_detected", "FAIL", "No Exact5 score columns"))
        return checks

    live = 0
    detail = []
    for c in score_cols:
        s = pd.to_numeric(df[c], errors="coerce")
        finite = s.replace([math.inf, -math.inf], pd.NA).dropna()
        nunique = finite.nunique(dropna=True)
        std = float(finite.std()) if len(finite) else 0.0
        is_live = len(finite) == len(df) and nunique > 1 and std > 1e-12 and not bool((finite == 0).all())
        live += int(is_live)
        detail.append(f"{c}:{'LIVE' if is_live else 'DEAD'}")
    checks.append(Check("exact5_min_two_live", "PASS" if live >= 2 else "FAIL", f"live={live}; " + ", ".join(detail)))
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", required=True)
    ap.add_argument("--target", type=int)
    ap.add_argument("--ranking")
    ap.add_argument("--out", default="preflight_report.json")
    args = ap.parse_args()

    checks, _ = validate_history(Path(args.history), args.target)
    checks += validate_ranking(Path(args.ranking) if args.ranking else None)

    critical_fail = any(c.critical and c.status != "PASS" for c in checks)
    report = {
        "target": args.target,
        "universe": EXACT5_UNIVERSE,
        "uniform_single_combo_probability": 1 / EXACT5_UNIVERSE,
        "uniform_top30_probability": 30 / EXACT5_UNIVERSE,
        "state": "BLOCKED" if critical_fail else "PASS",
        "checks": [asdict(c) for c in checks],
    }
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 4 if critical_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
