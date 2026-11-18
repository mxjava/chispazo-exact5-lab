"""Versioned Chispazo modality reconstruction and Classic-only exploratory scoring.

Never edits the canonical source. Labels are derived from the documented
2017 introduction of the second daily draw and the verified contest ordering.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path

TRANSITION_CONTEST = 5923
CANONICAL_SHA256 = "5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a"
NUMBER_COLUMNS = ("R1", "R2", "R3", "R4", "R5")
UNIVERSE = 28
PICK = 5
UNIFORM_LOGP = -math.log(math.comb(UNIVERSE, PICK))


def _strict_int(value: str, field: str, line: int) -> int:
    try:
        if value.strip() != str(int(value)):
            raise ValueError
        return int(value)
    except Exception as exc:
        raise ValueError(f"invalid_integer_{field}_line_{line}") from exc


def read_history(path: str | Path) -> tuple[list[dict], str]:
    p = Path(path)
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    rows = []
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"CONCURSO", "FECHA", *NUMBER_COLUMNS}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("history_missing_required_columns")
        for line, row in enumerate(reader, 2):
            contest = _strict_int(row["CONCURSO"], "CONCURSO", line)
            nums = [_strict_int(row[c], c, line) for c in NUMBER_COLUMNS]
            if contest <= 0 or len(set(nums)) != PICK or any(n < 1 or n > UNIVERSE for n in nums):
                raise ValueError(f"invalid_draw_line_{line}")
            try:
                date.fromisoformat(row["FECHA"])
            except Exception as exc:
                raise ValueError(f"invalid_date_line_{line}") from exc
            rows.append({"contest": contest, "date": row["FECHA"], "numbers": sorted(nums)})
    if not rows:
        raise ValueError("empty_history")
    ids = [r["contest"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_contest")
    ordered = sorted(rows, key=lambda r: r["contest"])
    expected = list(range(ordered[0]["contest"], ordered[-1]["contest"] + 1))
    if [r["contest"] for r in ordered] != expected:
        raise ValueError("non_contiguous_contests")
    return ordered, digest


def assign_modality(rows: list[dict]) -> tuple[list[dict], dict]:
    by_date: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_date[row["date"]].append(row)
    anomalies = []
    pre_single_dates = post_pair_dates = 0
    for day, group in by_date.items():
        group.sort(key=lambda r: r["contest"])
        if group[0]["contest"] < TRANSITION_CONTEST:
            if len(group) != 1:
                anomalies.append({"date": day, "contests": [r["contest"] for r in group], "reason": "pre_transition_not_single"})
            else:
                pre_single_dates += 1
        else:
            valid_pair = (len(group) == 2 and group[0]["contest"] % 2 == 1
                          and group[1]["contest"] == group[0]["contest"] + 1
                          and group[1]["contest"] % 2 == 0)
            final_partial = (len(group) == 1 and group[0]["contest"] == rows[-1]["contest"])
            if valid_pair:
                post_pair_dates += 1
            elif not final_partial:
                anomalies.append({"date": day, "contests": [r["contest"] for r in group], "reason": "post_transition_not_odd_even_pair"})
    if anomalies:
        raise ValueError("modality_date_structure_anomalies:" + json.dumps(anomalies[:10]))
    labelled = []
    for row in rows:
        if row["contest"] < TRANSITION_CONTEST:
            kind, rule = "CLASSIC", "single_daily_draw_before_2017-09-25"
        elif row["contest"] % 2 == 0:
            kind, rule = "CLASSIC", "even_contest_classic_after_2017-09-25"
        else:
            kind, rule = "DE_LAS_TRES", "odd_contest_de_las_tres_after_2017-09-25"
        labelled.append({**row, "draw_type": kind, "mapping_rule": rule,
                         "mapping_status": "STRUCTURAL_RULE_PENDING_ROW_LEVEL_PRIMARY_SOURCE_AUDIT"})
    summary = {
        "transition_contest": TRANSITION_CONTEST,
        "transition_date": "2017-09-25",
        "pre_transition_single_draw_dates": pre_single_dates,
        "post_transition_complete_odd_even_days": post_pair_dates,
        "post_transition_date_anomalies": anomalies,
        "classic_count": sum(r["draw_type"] == "CLASSIC" for r in labelled),
        "de_las_tres_count": sum(r["draw_type"] == "DE_LAS_TRES" for r in labelled),
        "first_contest": rows[0]["contest"], "last_contest": rows[-1]["contest"],
    }
    return labelled, summary


def _log_conditional5(probabilities: list[float], chosen: list[int]) -> float:
    weights = [p / (1.0 - p) for p in probabilities]
    elementary = [1.0] + [0.0] * PICK
    for w in weights:
        for j in range(PICK, 0, -1):
            elementary[j] += w * elementary[j - 1]
    return sum(math.log(weights[n - 1]) for n in chosen) - math.log(elementary[PICK])


def _smoothed_model_logp_from_counts(counts: Counter, draws_seen: int, target: dict, alpha: float = 200.0) -> float:
    base = PICK / UNIVERSE
    probs = [(counts[n] + alpha * base) / (draws_seen + alpha) for n in range(1, UNIVERSE + 1)]
    return _log_conditional5(probs, target["numbers"])


def prequential_marginal_diagnostic(labelled: list[dict], warmup_classic: int = 800, alpha: float = 200.0) -> dict:
    """Fixed, exploratory expanding-window marginal model; not an anytime-valid e-process."""
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    pooled = labelled
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws_for_warmup")
    records = []
    classic_counts = Counter(n for d in classic[:warmup_classic] for n in d["numbers"])
    classic_seen = warmup_classic
    pooled_counts = Counter()
    pooled_index = 0
    for target in classic[warmup_classic:]:
        while pooled_index < len(pooled) and pooled[pooled_index]["contest"] < target["contest"]:
            pooled_counts.update(pooled[pooled_index]["numbers"])
            pooled_index += 1
        classic_lp = _smoothed_model_logp_from_counts(classic_counts, classic_seen, target, alpha)
        pooled_seen = pooled_index
        pooled_lp = _smoothed_model_logp_from_counts(pooled_counts, pooled_seen, target, alpha)
        records.append({
            "contest": target["contest"],
            "classic_only_log_lift": classic_lp - UNIFORM_LOGP,
            "pooled_stream_log_lift": pooled_lp - UNIFORM_LOGP,
        })
        classic_counts.update(target["numbers"])
        classic_seen += 1
    def summarize(key):
        vals = [r[key] for r in records]
        return {"n": len(vals), "mean_log_lift": sum(vals) / len(vals),
                "positive_fraction": sum(v > 0 for v in vals) / len(vals),
                "cumulative_log_lift": sum(vals)}
    return {
        "classification": "EXPLORATORY_RETROSPECTIVE_NOT_EDGE_EVIDENCE",
        "warmup_classic_draws": warmup_classic, "alpha_fixed": alpha,
        "classic_only": summarize("classic_only_log_lift"),
        "pooled_stream_scored_on_same_classic_targets": summarize("pooled_stream_log_lift"),
        "paired_mean_difference_classic_minus_pooled": sum(r["classic_only_log_lift"] - r["pooled_stream_log_lift"] for r in records) / len(records),
        "warning": "This plug-in score is not an anytime-valid e-value, not multiplicity-adjusted, and not prospective confirmation. It is a diagnostic to test whether modality isolation changes the ranking."
    }



def _zscore(values: list[float]) -> list[float]:
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    sd = math.sqrt(variance)
    if sd < 1e-12:
        sd = 1.0
    return [(x - mean) / sd for x in values]


def _v264_transition_signal(draws: list[dict], t: int, window: int = 800) -> list[float]:
    """V264 transition expert with the prior leakage correction: range(start, t-1)."""
    if t < 2:
        return [0.0] * UNIVERSE
    previous = set(draws[t - 1]["numbers"])
    start = max(1, t - window)
    counts = [0.0] * UNIVERSE
    denominator = 0
    # Exclude j=t-1: that row is the context draw itself, not a historical target.
    for j in range(start, t - 1):
        if previous.intersection(draws[j - 1]["numbers"]):
            for number in draws[j]["numbers"]:
                counts[number - 1] += 1.0
            denominator += 1
    return [x / max(1, denominator) for x in counts]


def _v264_transition_logp(draws: list[dict], t: int, beta: float = 0.15) -> float:
    signal = _v264_transition_signal(draws, t, 800)
    z = _zscore(signal)
    weights = [math.exp(beta * x) for x in z]
    elementary = [1.0] + [0.0] * PICK
    for weight in weights:
        for j in range(PICK, 0, -1):
            elementary[j] += weight * elementary[j - 1]
    chosen = draws[t]["numbers"]
    return sum(math.log(weights[n - 1]) for n in chosen) - math.log(elementary[PICK])


def v264_transition_classic_diagnostic(labelled: list[dict], warmup_classic: int = 800, beta: float = 0.15) -> dict:
    """Compare the same fixed V264 transition expert on Classic-only vs pooled streams."""
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    if len(classic) <= warmup_classic:
        raise ValueError("insufficient_classic_draws_for_transition_warmup")
    pooled = labelled
    uniform_logp = UNIFORM_LOGP
    classic_lifts = []
    pooled_lifts = []
    pooled_index = 0
    for i in range(warmup_classic, len(classic)):
        target = classic[i]
        classic_lifts.append(_v264_transition_logp(classic, i, beta) - uniform_logp)
        while pooled_index < len(pooled) and pooled[pooled_index]["contest"] < target["contest"]:
            pooled_index += 1
        pooled_lifts.append(_v264_transition_logp(pooled, pooled_index, beta) - uniform_logp)
    def summary(values):
        return {"n": len(values), "mean_log_lift": sum(values) / len(values),
                "cumulative_log_lift": sum(values),
                "positive_fraction": sum(x > 0 for x in values) / len(values)}
    return {
        "expert": "V264 transition beta=0.15; corrected historical loop excludes current context row",
        "warmup_classic_draws": warmup_classic, "beta_fixed": beta,
        "classic_only": summary(classic_lifts),
        "pooled_stream_scored_on_same_classic_targets": summary(pooled_lifts),
        "paired_mean_difference_classic_minus_pooled": sum(a - b for a, b in zip(classic_lifts, pooled_lifts)) / len(classic_lifts),
        "classification": "EXPLORATORY_RETROSPECTIVE_NOT_EDGE_EVIDENCE",
        "warning": "Single fixed expert comparison; no multiplicity correction, anytime-valid e-value, or prospective confirmation."
    }


def build(history: str | Path, output: str | Path, expected_sha256: str | None = CANONICAL_SHA256) -> dict:
    rows, digest = read_history(history)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("canonical_history_sha256_mismatch")
    labelled, modality = assign_modality(rows)
    out = Path(output); out.mkdir(parents=True, exist_ok=True)
    with (out / "Chispazo_modality_map.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["CONCURSO", "FECHA", "TIPO", *NUMBER_COLUMNS, "REGLA_MAPEO", "ESTADO_AUDITORIA"])
        for r in labelled:
            w.writerow([r["contest"], r["date"], r["draw_type"], *r["numbers"], r["mapping_rule"], r["mapping_status"]])
    classic = [r for r in labelled if r["draw_type"] == "CLASSIC"]
    tres = [r for r in labelled if r["draw_type"] == "DE_LAS_TRES"]
    diagnostics = prequential_marginal_diagnostic(labelled)
    report = {
        "schema": "EXACT5_MODALITY_AUDIT_V1",
        "source_path": str(history), "source_sha256": digest,
        "source_rows": len(rows), "source_immutable": True,
        "modality": modality,
        "external_validation": [
            "Pronósticos 2012-2018 institutional accountability report: second Chispazo draw added 2017-09-25",
            "Official results 2017-11-02: contest 5999 De las Tres; contest 6000 Clásico"
        ],
        "classic_draws": len(classic), "de_las_tres_draws": len(tres),
        "exploratory_prequential_diagnostic": diagnostics,
        "v264_transition_classic_diagnostic": v264_transition_classic_diagnostic(labelled),
        "limitations": [
            "Pre-transition rows are classified as Classic because the institutional report says the second daily draw was only introduced on 2017-09-25; still require independent row-level source audit.",
            "Post-transition odd/even parity is structurally consistent with official examples, but the full historical series is not yet independently cross-checked row by row.",
            "The canonical source ends at contest 12249 (2026-09-13); later draws are not included.",
            "The plug-in marginal score is exploratory and cannot certify an edge."
        ],
        "overall_state": "BLOCKED_PROVENANCE_FOR_EDGE_CLAIMS"
    }
    (out / "modality_audit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history", required=True); p.add_argument("--out", required=True)
    p.add_argument("--skip-canonical-hash", action="store_true")
    a = p.parse_args()
    print(json.dumps(build(a.history, a.out, None if a.skip_canonical_hash else CANONICAL_SHA256), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
