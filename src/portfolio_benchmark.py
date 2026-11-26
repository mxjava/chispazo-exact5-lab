"""Matched random-null benchmark for frozen 30-line Chispazo Classic portfolios.

This is a research evaluator, not a predictor or production gate. It refuses
post-close registrations and requires a separately supplied hash-anchor file.
"""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, random, re
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse

UNIVERSE = 98_280
OFFICIAL_HOST = "loterianacional.gob.mx"

def _utc(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp_must_be_string")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() != timezone.utc.utcoffset(dt):
        raise ValueError("timestamp_must_be_utc")
    return dt

def _line_mask(line: str) -> int:
    if not isinstance(line, str) or not re.fullmatch(r"\\d{2}(?:-\\d{2}){4}", line):
        raise ValueError("invalid_line_format")
    values = [int(x) for x in line.split("-")]
    if values != sorted(values) or len(set(values)) != 5 or any(x < 1 or x > 28 for x in values):
        raise ValueError("invalid_line_numbers")
    mask = 0
    for value in values:
        mask |= 1 << (value - 1)
    return mask

def canonical_registration_hash(record: dict) -> str:
    unsigned = {k: v for k, v in record.items() if k != "registration_sha256"}
    payload = json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def load_draws(path: str | Path) -> dict[int, int]:
    draws: dict[int, int] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = {"CONCURSO", "MODALITY", "R1", "R2", "R3", "R4", "R5", "SOURCE_URL", "VERIFICATION"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("draw_csv_missing_required_columns")
        for row in reader:
            if row["MODALITY"].strip().upper() != "CLASSIC":
                continue
            contest = int(row["CONCURSO"])
            if contest in draws:
                raise ValueError("duplicate_classic_result")
            if row["VERIFICATION"].strip() != "OFFICIAL_PAGE_VERIFIED":
                raise ValueError("draw_not_officially_verified")
            host = (urlparse(row["SOURCE_URL"]).hostname or "").lower()
            if host not in {OFFICIAL_HOST, "www." + OFFICIAL_HOST}:
                raise ValueError("draw_source_not_official_domain")
            nums = [int(row[f"R{i}"]) for i in range(1, 6)]
            if len(set(nums)) != 5 or any(n < 1 or n > 28 for n in nums):
                raise ValueError("invalid_draw_numbers")
            draws[contest] = sum(1 << (n - 1) for n in nums)
    return draws

def validate_records(portfolios: dict, trusted_hashes: dict, draws: dict[int, int]) -> list[dict]:
    if portfolios.get("schema") != "EXACT5_FROZEN_PORTFOLIOS_V1":
        raise ValueError("unsupported_portfolio_schema")
    records = portfolios.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("empty_portfolio_records")
    validated, seen = [], set()
    for record in records:
        target = record.get("target")
        if isinstance(target, bool) or not isinstance(target, int) or target in seen:
            raise ValueError("invalid_or_duplicate_target")
        seen.add(target)
        if record.get("modality") != "CLASSIC":
            raise ValueError("non_classic_target")
        if not re.fullmatch(r"[0-9a-f]{40}", str(record.get("commit_sha", ""))):
            raise ValueError("invalid_commit_sha")
        claimed = record.get("registration_sha256")
        if not re.fullmatch(r"[0-9a-f]{64}", str(claimed or "")):
            raise ValueError("invalid_registration_sha256")
        if trusted_hashes.get(str(target)) != claimed:
            raise ValueError("registration_hash_not_in_external_anchor_file")
        if canonical_registration_hash(record) != claimed:
            raise ValueError("registration_hash_mismatch")
        if len(record.get("lines", [])) != 30:
            raise ValueError("portfolio_must_have_30_lines")
        masks = [_line_mask(line) for line in record["lines"]]
        if len(set(masks)) != 30:
            raise ValueError("portfolio_lines_must_be_distinct")
        if _utc(record.get("registered_at_utc")) >= _utc(record.get("sales_cutoff_utc")):
            raise ValueError("registration_not_pre_cutoff")
        if target not in draws:
            raise ValueError("missing_official_classic_result")
        validated.append({"target": target, "masks": masks, "result_mask": draws[target]})
    return sorted(validated, key=lambda x: x["target"])

def score_masks(masks: list[int], result_mask: int) -> int:
    return max((mask & result_mask).bit_count() for mask in masks)

def benchmark(records: list[dict], replicates: int = 5000, seed: int = 20261126) -> dict:
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
    ordered_means = sorted(null_means)
    return {
        "schema": "EXACT5_MATCHED_RANDOM_PORTFOLIO_BENCHMARK_V1",
        "state": "RESEARCH_ONLY_NO_EDGE",
        "targets": len(records), "replicates": replicates, "seed": seed,
        "portfolio_lines_per_target": 30,
        "observed": {"mean_best_hits": observed_mean, "targets_best_ge_4": observed_ge4, "targets_exact5": observed_exact5},
        "matched_random_null": {
            "mean_best_hits_mean": mean(null_means),
            "mean_best_hits_95pct": [ordered_means[int(.025 * replicates)], ordered_means[min(replicates-1, int(.975 * replicates))]],
            "targets_best_ge_4_mean": mean(null_ge4), "targets_exact5_mean": mean(null_exact5)},
        "empirical_upper_tail_p": {"mean_best_hits": upper_p(null_means, observed_mean),
            "targets_best_ge_4": upper_p(null_ge4, observed_ge4), "targets_exact5": upper_p(null_exact5, observed_exact5)},
        "limitations": [
            "Retrospective matched-null diagnostic; not prospective evidence or an anytime-valid e-value.",
            "If portfolios were selected after examining these target outcomes, the full selection process must be repeated inside every null replicate.",
            "An independent anchor file must be controlled outside the portfolio JSON; this program cannot authenticate its custodian.",
            "No edge is established by this report, even when an empirical p-value is small."
        ]}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portfolios", required=True)
    parser.add_argument("--trusted-hashes", required=True, help="separate externally retained JSON map: target -> registration SHA-256")
    parser.add_argument("--draws", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261126)
    args = parser.parse_args()
    portfolios = json.loads(Path(args.portfolios).read_text(encoding="utf-8"))
    anchors = json.loads(Path(args.trusted_hashes).read_text(encoding="utf-8"))
    draws = load_draws(args.draws)
    records = validate_records(portfolios, anchors, draws)
    result = benchmark(records, args.replicates, args.seed)
    result["gate"] = "INSUFFICIENT_PROSPECTIVE_TARGETS" if len(records) < 100 else "REQUIRES_PREREGISTERED_MULTIPLICITY_AND_CUSTODY_REVIEW"
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
