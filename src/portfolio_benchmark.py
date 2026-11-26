"""Matched random-null benchmark for native, frozen 30-line Exact5 registrations.

Research evaluator only. Registration and result hashes must be anchored in
separate externally controlled files; this program cannot authenticate custody.
"""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math, random, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse

OFFICIAL_HOST = "loterianacional.gob.mx"
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")

def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_must_be_string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_utc_timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ValueError("timestamp_must_be_utc")
    return dt

def _line_mask(line: str) -> int:
    if not isinstance(line, str) or not re.fullmatch(r"\d{2}(?:-\d{2}){4}", line):
        raise ValueError("invalid_line_format")
    values = [int(x) for x in line.split("-")]
    if values != sorted(values) or len(set(values)) != 5 or any(x < 1 or x > 28 for x in values):
        raise ValueError("invalid_line_numbers")
    mask = 0
    for value in values:
        mask |= 1 << (value - 1)
    return mask

def canonical_hash(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def canonical_registration_hash(record: dict) -> str:
    return canonical_hash({k: v for k, v in record.items() if k != "registration_sha256"})

def canonical_draw_payload(row: dict) -> dict:
    numbers = sorted(int(row[f"R{i}"]) for i in range(1, 6))
    return {
        "contest": int(row["CONCURSO"]),
        "modality": row["MODALITY"].strip().upper(),
        "numbers": numbers,
        "source_url": row["SOURCE_URL"].strip(),
        "source_sha256": row["SOURCE_SHA256"].strip(),
        "verification": row["VERIFICATION"].strip(),
    }

def canonical_draw_hash(row: dict) -> str:
    return canonical_hash(canonical_draw_payload(row))

def load_draws(path: str | Path, trusted_draw_hashes: dict) -> dict[int, int]:
    draws: dict[int, int] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"CONCURSO", "MODALITY", "R1", "R2", "R3", "R4", "R5",
                    "SOURCE_URL", "SOURCE_SHA256", "VERIFICATION"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("draw_csv_missing_required_columns")
        for row in reader:
            if row["MODALITY"].strip().upper() != "CLASSIC":
                continue
            payload = canonical_draw_payload(row)
            contest = payload["contest"]
            if contest in draws:
                raise ValueError("duplicate_classic_result")
            parsed = urlparse(payload["source_url"])
            if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {OFFICIAL_HOST, "www." + OFFICIAL_HOST}:
                raise ValueError("draw_source_not_official_https_domain")
            if not HEX64.fullmatch(payload["source_sha256"]):
                raise ValueError("invalid_original_source_sha256")
            if payload["verification"] != "OFFICIAL_PAGE_VERIFIED":
                raise ValueError("draw_not_officially_verified")
            if len(set(payload["numbers"])) != 5 or any(n < 1 or n > 28 for n in payload["numbers"]):
                raise ValueError("invalid_draw_numbers")
            claimed = canonical_draw_hash(row)
            if trusted_draw_hashes.get(str(contest)) != claimed:
                raise ValueError("draw_hash_not_in_external_anchor_file")
            draws[contest] = sum(1 << (n - 1) for n in payload["numbers"])
    return draws

def validate_records(portfolios: dict, trusted_registration_hashes: dict,
                     target_cutoffs: dict, draws: dict[int, int]) -> list[dict]:
    if portfolios.get("schema") != "EXACT5_NATIVE_REGISTRATIONS_V1":
        raise ValueError("unsupported_portfolio_schema")
    records = portfolios.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("empty_portfolio_records")
    validated, seen = [], set()
    for record in records:
        target = record.get("target")
        if isinstance(target, bool) or not isinstance(target, int) or target <= 0 or target in seen:
            raise ValueError("invalid_or_duplicate_target")
        seen.add(target)
        if record.get("preflight_state") != "PASS":
            raise ValueError("registration_preflight_not_pass")
        gate_summary = record.get("gate_summary")
        if (not isinstance(gate_summary, dict) or gate_summary.get("state") != "PASS"
                or gate_summary.get("failed_checks") != []):
            raise ValueError("registration_gate_summary_not_pass")
        if record.get("history_max") != target - 1:
            raise ValueError("registration_history_not_target_minus_one")
        if not isinstance(record.get("model_version"), str) or not record["model_version"].strip():
            raise ValueError("invalid_model_version")
        try:
            registered_utc = _utc(record.get("registered_at_utc"))
            registered_local = datetime.fromisoformat(str(record.get("registered_at_mexico_city", "")).replace("Z", "+00:00"))
            mexico_zone = ZoneInfo("America/Mexico_City")
            if registered_local.tzinfo is None or registered_local.utcoffset() != mexico_zone.utcoffset(registered_local):
                raise ValueError("registration_mexico_city_timezone_mismatch")
            if registered_utc != registered_local.astimezone(timezone.utc):
                raise ValueError("registration_timestamps_disagree")
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("invalid_registration_timestamps") from exc
        if not HEX40.fullmatch(str(record.get("commit_sha", ""))):
            raise ValueError("invalid_commit_sha")
        for key in ("history_sha256", "ranking_sha256", "registration_sha256"):
            if not HEX64.fullmatch(str(record.get(key, ""))):
                raise ValueError(f"invalid_{key}")
        claimed = record["registration_sha256"]
        if trusted_registration_hashes.get(str(target)) != claimed:
            raise ValueError("registration_hash_not_in_external_anchor_file")
        if canonical_registration_hash(record) != claimed:
            raise ValueError("registration_hash_mismatch")
        lines = record.get("lines")
        if not isinstance(lines, list) or len(lines) != 30:
            raise ValueError("portfolio_must_have_30_lines")
        masks = [_line_mask(line) for line in lines]
        if len(set(masks)) != 30:
            raise ValueError("portfolio_lines_must_be_distinct")
        cutoff = target_cutoffs.get(str(target))
        if not isinstance(cutoff, dict) or cutoff.get("modality") != "CLASSIC":
            raise ValueError("missing_or_nonclassic_external_cutoff")
        if _utc(record.get("registered_at_utc")) >= _utc(cutoff.get("sales_cutoff_utc")):
            raise ValueError("registration_not_pre_cutoff")
        if target not in draws:
            raise ValueError("missing_externally_anchored_official_classic_result")
        validated.append({"target": target, "masks": masks, "result_mask": draws[target]})
    return sorted(validated, key=lambda x: x["target"])

def score_masks(masks: list[int], result_mask: int) -> int:
    return max((mask & result_mask).bit_count() for mask in masks)

def exact_uniform_portfolio_null(lines: int = 30) -> dict:
    """Exact hypergeometric null for a uniformly sampled set of distinct lines."""
    universe = math.comb(28, 5)
    if isinstance(lines, bool) or not isinstance(lines, int) or not 1 <= lines <= universe:
        raise ValueError("lines_must_be_integer_between_1_and_universe")
    tail = {}
    for threshold in range(1, 6):
        favorable = sum(math.comb(5, j) * math.comb(23, 5-j)
                        for j in range(threshold, 6))
        no_favorable = math.comb(universe - favorable, lines) / math.comb(universe, lines)
        tail[str(threshold)] = 1.0 - no_favorable
    return {
        "universe": universe,
        "lines": lines,
        "probability_best_hits_at_least_k": tail,
        "expected_best_hits": sum(tail.values()),
        "expected_exact5_per_target": tail["5"],
    }

def benchmark(records: list[dict], replicates: int = 5000, seed: int = 20261126) -> dict:
    if not records:
        raise ValueError("no_validated_records")
    if replicates < 999:
        raise ValueError("replicates_must_be_at_least_999")
    universe = [sum(1 << (n - 1) for n in combo) for combo in itertools.combinations(range(1, 29), 5)]
    observed = [score_masks(r["masks"], r["result_mask"]) for r in records]
    observed_mean = mean(observed)
    observed_ge4, observed_exact5 = sum(x >= 4 for x in observed), sum(x == 5 for x in observed)
    rng = random.Random(seed)
    null_means, null_ge4, null_exact5 = [], [], []
    for _ in range(replicates):
        scores = [score_masks(rng.sample(universe, 30), record["result_mask"]) for record in records]
        null_means.append(mean(scores))
        null_ge4.append(sum(x >= 4 for x in scores))
        null_exact5.append(sum(x == 5 for x in scores))
    def upper_p(null: list[float], value: float) -> float:
        return (1 + sum(x >= value for x in null)) / (replicates + 1)
    ordered = sorted(null_means)
    return {
        "schema": "EXACT5_MATCHED_RANDOM_PORTFOLIO_BENCHMARK_V1",
        "state": "RESEARCH_ONLY_NO_EDGE",
        "targets": len(records), "replicates": replicates, "seed": seed,
        "portfolio_lines_per_target": 30,
        "exact_uniform_null": exact_uniform_portfolio_null(30),
        "observed": {"mean_best_hits": observed_mean, "targets_best_ge_4": observed_ge4, "targets_exact5": observed_exact5},
        "matched_random_null": {
            "mean_best_hits_mean": mean(null_means),
            "mean_best_hits_95pct": [ordered[int(.025 * replicates)], ordered[min(replicates-1, int(.975 * replicates))]],
            "targets_best_ge_4_mean": mean(null_ge4), "targets_exact5_mean": mean(null_exact5)},
        "empirical_upper_tail_p": {"mean_best_hits": upper_p(null_means, observed_mean),
            "targets_best_ge_4": upper_p(null_ge4, observed_ge4), "targets_exact5": upper_p(null_exact5, observed_exact5)},
        "limitations": [
            "Retrospective matched-null diagnostic; not prospective evidence or an anytime-valid e-value.",
            "The full model/portfolio selection process must be repeated inside each null replicate if selection used any evaluated outcomes.",
            "Registration, cutoff and draw anchors must be retained independently by a trustworthy custodian; this CLI cannot authenticate custody.",
            "A source URL and self-declared verification field are insufficient without the external draw hash anchor.",
            "No edge is established by this report, even when an empirical p-value is small."
        ]}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registrations", required=True, help="JSON: EXACT5_NATIVE_REGISTRATIONS_V1 with native freeze_prediction records")
    parser.add_argument("--trusted-registration-hashes", required=True, help="external JSON map: target -> registration SHA-256")
    parser.add_argument("--target-cutoffs", required=True, help="external JSON map: target -> {modality, sales_cutoff_utc}")
    parser.add_argument("--draws", required=True, help="CSV includes original source SHA-256 and verification metadata")
    parser.add_argument("--trusted-draw-hashes", required=True, help="external JSON map: target -> canonical draw-record SHA-256")
    parser.add_argument("--out", required=True)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261126)
    args = parser.parse_args()
    registrations = json.loads(Path(args.registrations).read_text(encoding="utf-8"))
    registration_anchors = json.loads(Path(args.trusted_registration_hashes).read_text(encoding="utf-8"))
    cutoffs = json.loads(Path(args.target_cutoffs).read_text(encoding="utf-8"))
    draw_anchors = json.loads(Path(args.trusted_draw_hashes).read_text(encoding="utf-8"))
    draws = load_draws(args.draws, draw_anchors)
    records = validate_records(registrations, registration_anchors, cutoffs, draws)
    result = benchmark(records, args.replicates, args.seed)
    result["gate"] = "INSUFFICIENT_PROSPECTIVE_TARGETS" if len(records) < 100 else "REQUIRES_PREREGISTERED_MULTIPLICITY_AND_CUSTODY_REVIEW"
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
