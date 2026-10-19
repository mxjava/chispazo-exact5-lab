from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
import pandas as pd
from src.pipeline.strict_json import load_json_object

NUM_MIN = 1
NUM_MAX = 28
DRAW_SIZE = 5
EXACT5_UNIVERSE = math.comb(NUM_MAX, DRAW_SIZE)
EXACT5_SCORE_COLUMNS = [
    "score_ltr_ndcg_exact5",
    "score_ltr_adv_exact5",
    "score_ltr_exact5_balanced",
    "score_ltr_exact5_hard",
    "score_ltr_exact5_ultra",
]

@dataclass
class Check:
    name: str
    status: str
    detail: str
    critical: bool = True


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _number_columns(df: pd.DataFrame) -> list[str]:
    lowered = {str(c).lower(): c for c in df.columns}
    for pattern in (
        ["r1", "r2", "r3", "r4", "r5"],
        ["n1", "n2", "n3", "n4", "n5"],
        ["num1", "num2", "num3", "num4", "num5"],
        ["numero1", "numero2", "numero3", "numero4", "numero5"],
    ):
        if all(c in lowered for c in pattern):
            return [lowered[c] for c in pattern]
    return []


def _contest_column(df: pd.DataFrame) -> str | None:
    lowered = {str(c).lower(): c for c in df.columns}
    for name in ("concurso", "contest", "sorteo"):
        if name in lowered:
            return lowered[name]
    return None


def _decimal_value(value: Any) -> Decimal | None:
    """Parse a CSV value without losing fractional digits to float rounding."""
    if pd.isna(value):
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None


def _is_finite(value: Decimal | None) -> bool:
    return value is not None and value.is_finite()


def _is_integer(value: Decimal | None) -> bool:
    if not _is_finite(value):
        return False
    try:
        return value == value.to_integral_value()
    except (InvalidOperation, OverflowError, ValueError):
        return False


def validate_history(path: Path, target: int | None) -> tuple[list[Check], dict[str, Any]]:
    checks: list[Check] = []
    meta: dict[str, Any] = {"path": str(path)}
    if not path.exists():
        return [Check("history_exists", "FAIL", str(path))], meta
    checks.append(Check("history_exists", "PASS", str(path)))
    try:
        # Keep numeric fields as text so values such as 1.00000000000000001
        # cannot be rounded to 1.0 before the strict integer checks below.
        df = pd.read_csv(path, dtype=str)
    except Exception as exc:
        checks.append(Check("history_readable", "FAIL", repr(exc)))
        return checks, meta
    checks.append(Check("history_readable", "PASS", f"rows={len(df)}"))
    meta["sha256"] = sha256_file(path)
    meta["rows"] = len(df)

    cc = _contest_column(df)
    if cc is None:
        checks.append(Check("contest_column", "FAIL", "missing concurso/contest/sorteo"))
        return checks, meta

    contest_values = df[cc].map(_decimal_value)
    numeric_bad = int(contest_values.isna().sum())
    finite = contest_values.map(_is_finite)
    finite_bad = int((~finite).sum())
    integer = contest_values.map(_is_integer)
    integer_bad = int((~integer).sum())
    positive = integer & contest_values.map(lambda value: value > 0 if value is not None and value.is_finite() else False)
    positive_bad = int((~positive).sum())
    checks.append(Check("contest_numeric", "PASS" if numeric_bad == 0 else "FAIL", f"invalid={numeric_bad}"))
    checks.append(Check("contest_finite", "PASS" if finite_bad == 0 else "FAIL", f"invalid={finite_bad}"))
    checks.append(Check("contest_integer", "PASS" if integer_bad == 0 else "FAIL", f"invalid={integer_bad}"))
    checks.append(Check("contest_positive", "PASS" if positive_bad == 0 else "FAIL", f"invalid={positive_bad}"))
    if numeric_bad or finite_bad or integer_bad or positive_bad:
        return checks, meta

    try:
        contests = pd.Series(
            [int(value) for value in contest_values], index=df.index, dtype=object
        )
    except (OverflowError, ValueError, TypeError, MemoryError) as exc:
        checks.append(Check("contest_integer", "FAIL", f"conversion_error={exc!r}"))
        return checks, meta
    dup = int(contests.duplicated().sum())
    checks.append(Check("contest_unique", "PASS" if dup == 0 else "FAIL", f"duplicates={dup}"))
    cmin, cmax = int(contests.min()), int(contests.max())
    meta["contest_min"] = cmin
    meta["contest_max"] = cmax
    expected_count = cmax - cmin + 1
    contiguous = len(set(contests.tolist())) == expected_count
    checks.append(Check("contest_contiguous", "PASS" if contiguous else "FAIL", f"min={cmin}; max={cmax}; rows={len(df)}; expected={expected_count}"))

    if target is not None:
        future = int((contests >= int(target)).sum())
        checks.append(Check("no_future_leakage", "PASS" if future == 0 else "FAIL", f"rows_with_contest>=target={future}"))
        checks.append(Check("history_ends_at_target_minus_1", "PASS" if cmax == int(target) - 1 else "FAIL", f"history_max={cmax}; expected={int(target)-1}"))

    ncols = _number_columns(df)
    if len(ncols) != DRAW_SIZE:
        checks.append(Check("number_columns", "FAIL", f"detected={ncols}"))
        return checks, meta
    vals = df[ncols].apply(lambda column: column.map(_decimal_value))
    numeric_bad = int(vals.isna().sum().sum())
    finite = vals.apply(lambda column: column.map(_is_finite))
    finite_bad = int((~finite).sum().sum())
    integer = vals.apply(lambda column: column.map(_is_integer))
    integer_bad = int((~integer).sum().sum())
    out = int(vals.apply(lambda column: column.map(
        lambda value: value.is_finite() and not NUM_MIN <= value <= NUM_MAX
        if value is not None else False
    )).sum().sum())
    repeated_inside = int(sum(
        len([value for value in row if value is not None and value.is_finite()]) != DRAW_SIZE
        or len(set(value for value in row if value is not None and value.is_finite())) != DRAW_SIZE
        for _, row in vals.iterrows()
    ))
    checks.append(Check("numbers_numeric", "PASS" if numeric_bad == 0 else "FAIL", f"invalid_cells={numeric_bad}"))
    checks.append(Check("numbers_finite", "PASS" if finite_bad == 0 else "FAIL", f"invalid_cells={finite_bad}"))
    checks.append(Check("numbers_integer", "PASS" if integer_bad == 0 else "FAIL", f"invalid_cells={integer_bad}"))
    checks.append(Check("numbers_range_1_28", "PASS" if out == 0 else "FAIL", f"out_of_range={out}"))
    checks.append(Check("five_unique_numbers", "PASS" if repeated_inside == 0 else "FAIL", f"bad_rows={repeated_inside}"))

    date_col = next((c for c in df.columns if str(c).lower() in {"fecha", "date"}), None)
    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        bad_dates = int(dates.isna().sum())
        checks.append(Check("dates_parseable", "PASS" if bad_dates == 0 else "FAIL", f"invalid_dates={bad_dates}", critical=False))
    return checks, meta


def _parse_combo(series: pd.Series) -> pd.Series:
    def norm(x: Any) -> str | None:
        try:
            parts = [int(p) for p in str(x).replace("-", " ").replace(",", " ").split()]
            if len(parts) != 5 or len(set(parts)) != 5 or any(p < 1 or p > 28 for p in parts):
                return None
            return "-".join(f"{p:02d}" for p in sorted(parts))
        except Exception:
            return None
    return series.map(norm)


def validate_ranking(path: Path | None) -> tuple[list[Check], dict[str, Any]]:
    checks: list[Check] = []
    meta: dict[str, Any] = {}
    if path is None:
        return [Check("ranking_present", "FAIL", "No ranking supplied")], meta
    if not path.exists():
        return [Check("ranking_present", "FAIL", str(path))], meta
    checks.append(Check("ranking_present", "PASS", str(path)))
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        checks.append(Check("ranking_readable", "FAIL", repr(exc)))
        return checks, meta
    meta.update({"rows": len(df), "sha256": sha256_file(path)})
    checks.append(Check("ranking_readable", "PASS", f"rows={len(df)}"))
    checks.append(Check("ranking_full_universe", "PASS" if len(df) == EXACT5_UNIVERSE else "FAIL", f"rows={len(df)}; expected={EXACT5_UNIVERSE}"))

    if "combo" in df.columns:
        combos = _parse_combo(df["combo"])
        invalid = int(combos.isna().sum())
        unique = int(combos.nunique(dropna=True))
        checks.append(Check("ranking_combo_valid", "PASS" if invalid == 0 else "FAIL", f"invalid={invalid}"))
        checks.append(Check("ranking_combo_unique", "PASS" if unique == len(df) else "FAIL", f"unique={unique}; rows={len(df)}"))
    else:
        checks.append(Check("ranking_combo_column", "FAIL", "missing combo"))

    available = [c for c in EXACT5_SCORE_COLUMNS if c in df.columns]
    checks.append(Check("exact5_score_columns", "PASS" if len(available) >= 2 else "FAIL", f"found={available}"))
    live = 0
    detail = []
    for c in available:
        s = pd.to_numeric(df[c], errors="coerce").replace([math.inf, -math.inf], pd.NA).dropna()
        std = float(s.std()) if len(s) > 1 else 0.0
        uniq = int(s.nunique())
        is_live = len(s) == len(df) and uniq > 1 and std > 1e-12 and not bool((s == 0).all())
        live += int(is_live)
        detail.append(f"{c}={'LIVE' if is_live else 'DEAD'}(unique={uniq},std={std:.6g})")
    checks.append(Check("exact5_min_two_live", "PASS" if live >= 2 else "FAIL", f"live={live}; " + "; ".join(detail)))
    meta["live_exact5"] = live
    return checks, meta



def validate_evidence(firewall_report: Path | None, exactset_summary: Path | None) -> tuple[list[Check], dict[str, Any]]:
    checks: list[Check] = []
    meta: dict[str, Any] = {}
    allowed_depths = {30, 100, 500, 2500, 5000, 10000}

    def finite_number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) else None

    def integer_value(value: Any) -> int | None:
        parsed = _decimal_value(value)
        if not _is_integer(parsed):
            return None
        try:
            return int(parsed)
        except (ValueError, OverflowError, TypeError):
            return None

    def valid_approved_row(row: Any) -> bool:
        if not isinstance(row, dict):
            return False

        strategy = row.get("strategy")
        depth = integer_value(row.get("depth"))
        n = integer_value(row.get("n"))
        hits = integer_value(row.get("hits"))
        rate = finite_number(row.get("rate"))
        null_rate = finite_number(row.get("null_rate"))
        lift = finite_number(row.get("lift"))
        p_raw = finite_number(row.get("p_raw"))
        p_holm = finite_number(row.get("p_holm"))

        if not isinstance(strategy, str) or not strategy.strip():
            return False
        if depth not in allowed_depths or n is None or n < 100:
            return False
        if hits is None or not 0 <= hits <= n:
            return False
        if None in (rate, null_rate, lift, p_raw, p_holm):
            return False
        if not (0 <= p_raw <= p_holm < 0.05 and lift > 1):
            return False

        expected_rate = hits / n
        expected_null = depth / EXACT5_UNIVERSE
        expected_lift = expected_rate / expected_null

        return (
            math.isclose(rate, expected_rate, rel_tol=1e-9, abs_tol=1e-12)
            and math.isclose(null_rate, expected_null, rel_tol=1e-9, abs_tol=1e-12)
            and math.isclose(lift, expected_lift, rel_tol=1e-6, abs_tol=1e-9)
        )

    if firewall_report is None or not firewall_report.exists():
        checks.append(Check("firewall_report_present", "FAIL", "missing V264 firewall report"))
    else:
        try:
            data = load_json_object(firewall_report)
            if not isinstance(data, dict):
                raise ValueError("firewall report must be a JSON object")
        except (OSError, ValueError, TypeError) as exc:
            data = {}
            checks.append(Check("firewall_report_valid", "FAIL", f"invalid report: {exc}"))
        else:
            checks.append(Check("firewall_report_valid", "PASS", "JSON object"))

        meta["firewall"] = data
        state = data.get("state")
        approved = data.get("oos_approved_tests")
        rows_valid = (
            isinstance(approved, list)
            and len(approved) > 0
            and all(valid_approved_row(row) for row in approved)
        )
        ok = state == "PROMOTE_EXACT5" and rows_valid
        checks.append(Check(
            "v264_oos_evidence",
            "PASS" if ok else "FAIL",
            f"state={state}; approved_tests="
            f"{len(approved) if isinstance(approved, list) else 'invalid'}; "
            f"valid_rows={sum(valid_approved_row(row) for row in approved) if isinstance(approved, list) else 0}"
        ))

    if exactset_summary is None or not exactset_summary.exists():
        checks.append(Check("exactset_summary_present", "FAIL", "missing exact-set anytime summary"))
    else:
        try:
            data = load_json_object(exactset_summary)
            if not isinstance(data, dict):
                raise ValueError("exact-set summary must be a JSON object")
        except (OSError, ValueError, TypeError) as exc:
            checks.append(Check("exactset_summary_valid", "FAIL", f"invalid summary: {exc}"))
        else:
            meta["exactset"] = data
            e = data.get("e_value", data.get("evalue", data.get("final_e_value")))
            if e is not None:
                number = finite_number(e)
                ok = number is not None and number >= 20.0
                detail = f"e_value={number}; threshold=20"
            else:
                log_e = finite_number(data.get("cumulative_log_e"))
                ok = log_e is not None and log_e >= math.log(20.0)
                detail = f"cumulative_log_e={log_e}; threshold={math.log(20.0):.12g}"
            checks.append(Check("exactset_anytime_evalue", "PASS" if ok else "FAIL", detail))

    return checks, meta

def run(history: Path, target: int, ranking: Path | None = None, firewall_report: Path | None = None, exactset_summary: Path | None = None) -> dict[str, Any]:
    checks: list[Check] = []
    hm: dict[str, Any]
    rm: dict[str, Any]
    em: dict[str, Any]
    c, hm = validate_history(history, target); checks.extend(c)
    c, rm = validate_ranking(ranking); checks.extend(c)
    c, em = validate_evidence(firewall_report, exactset_summary); checks.extend(c)
    critical_fail = any(c.critical and c.status != "PASS" for c in checks)
    return {
        "target": int(target),
        "universe": EXACT5_UNIVERSE,
        "uniform_single_combo_probability": 1 / EXACT5_UNIVERSE,
        "uniform_top30_probability": 30 / EXACT5_UNIVERSE,
        "state": "BLOCKED" if critical_fail else "PASS",
        "checks": [asdict(c) for c in checks],
        "inputs": {"history": hm, "ranking": rm, "evidence": em},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="V266 strict pre-sorteo evidence gate")
    ap.add_argument("--history", required=True)
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--ranking")
    ap.add_argument("--firewall-report")
    ap.add_argument("--exactset-summary")
    ap.add_argument("--out", default="preflight_v266.json")
    a = ap.parse_args()
    report = run(
        Path(a.history), a.target,
        Path(a.ranking) if a.ranking else None,
        Path(a.firewall_report) if a.firewall_report else None,
        Path(a.exactset_summary) if a.exactset_summary else None,
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["state"] == "PASS" else 4

if __name__ == "__main__":
    raise SystemExit(main())
