#!/usr/bin/env python3
"""Fetch and fingerprint Loteria Nacional's official Chispazo CSV.

This is a source/schema audit only: it never edits canonical history or emits
model inputs. The raw response and audit report are retained as CI artifacts.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://loterianacional.gob.mx/Documentos/Historicos/Chispazo.csv"
OUT = Path("official_csv_audit")
OUT.mkdir(exist_ok=True)

request = urllib.request.Request(
    URL,
    headers={"User-Agent": "Exact5-Official-Source-Audit/1.0", "Accept": "text/csv,*/*"},
)
with urllib.request.urlopen(request, timeout=45) as response:
    raw = response.read()
    final_url = response.geturl()
    content_type = response.headers.get("Content-Type", "")
    last_modified = response.headers.get("Last-Modified")

(OUT / "Chispazo_official_raw.csv").write_bytes(raw)
sha256 = hashlib.sha256(raw).hexdigest()

text = None
encoding_used = None
for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
    try:
        text = raw.decode(encoding)
        encoding_used = encoding
        break
    except UnicodeDecodeError:
        continue
if text is None:
    raise SystemExit("FAIL: official CSV cannot be decoded")

sample = text[:8192]
try:
    dialect = csv.Sniffer().sniff(sample, delimiters=",;|\\t")
    delimiter = dialect.delimiter
except csv.Error:
    delimiter = ","

reader = csv.reader(io.StringIO(text), delimiter=delimiter)
rows = list(reader)
if not rows:
    raise SystemExit("FAIL: official CSV is empty")
header = [h.strip().lstrip("\ufeff") for h in rows[0]]
data_rows = [r for r in rows[1:] if any(cell.strip() for cell in r)]

def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def post_baseline_ids_are_contiguous(draw_ids, baseline_last: int = 12249) -> bool:
    """Check continuity from the first post-baseline draw through the observed maximum."""
    observed = sorted(set(draw_ids))
    if not observed:
        return False
    return observed == list(range(baseline_last + 1, observed[-1] + 1))

def analyze_daily_pair_structure(rows, draw_id_index, date_index, transition_date="25/09/2017"):
    """Describe the post-transition two-draw daily ID structure without assigning modalities."""
    from collections import defaultdict
    from datetime import datetime

    transition = datetime.strptime(transition_date, "%d/%m/%Y").date()
    by_date = defaultdict(list)
    for row in rows:
        try:
            draw_id = int(row[draw_id_index])
            draw_date = datetime.strptime(row[date_index].strip(), "%d/%m/%Y").date()
        except (ValueError, IndexError):
            continue
        if draw_date >= transition:
            by_date[draw_date].append(draw_id)

    anomalies = []
    all_ids = []
    for draw_date, ids in sorted(by_date.items()):
        ordered = sorted(ids)
        all_ids.extend(ordered)
        if len(ordered) != 2 or ordered[1] != ordered[0] + 1 or ordered[0] % 2 != 1:
            anomalies.append({
                "date": draw_date.isoformat(),
                "draw_ids": ordered,
                "reason": "EXPECTED_TWO_CONSECUTIVE_IDS_ODD_THEN_EVEN",
            })

    unique_ids = sorted(set(all_ids))
    contiguous = bool(unique_ids) and unique_ids == list(range(unique_ids[0], unique_ids[-1] + 1))
    return {
        "transition_date_inclusive": transition.isoformat(),
        "observed_dates": len(by_date),
        "dates_with_exactly_two_rows": sum(len(ids) == 2 for ids in by_date.values()),
        "dates_with_other_row_count": sum(len(ids) != 2 for ids in by_date.values()),
        "post_transition_unique_draw_ids": len(unique_ids),
        "post_transition_draw_id_min": unique_ids[0] if unique_ids else None,
        "post_transition_draw_id_max": unique_ids[-1] if unique_ids else None,
        "post_transition_ids_contiguous": contiguous,
        "dates_matching_two_consecutive_odd_even_ids": len(by_date) - len(anomalies),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:100],
        "classification": "STRUCTURAL_PATTERN_ONLY_NO_MODALITY_ASSERTION",
    }


normalized = [norm(x) for x in header]
aliases = {
    "draw_id": {"concurso", "sorteo", "numerodesorteo", "nosorteo", "draw", "drawid"},
    "date": {"fecha", "date", "fechadesorteo"},
    "modality": {"sorteo", "modalidad", "tipo", "juego", "categoria"},
    "n1": {"r1", "n1", "numero1", "num1", "bolilla1"},
    "n2": {"r2", "n2", "numero2", "num2", "bolilla2"},
    "n3": {"r3", "n3", "numero3", "num3", "bolilla3"},
    "n4": {"r4", "n4", "numero4", "num4", "bolilla4"},
    "n5": {"r5", "n5", "numero5", "num5", "bolilla5"},
}
def resolve_column_mapping(header, aliases):
    """Resolve unique source columns; ambiguous or missing required fields fail closed."""
    normalized_header = [norm(value) for value in header]
    mapping = {}
    for key, choices in aliases.items():
        matches = [i for i, name in enumerate(normalized_header) if name in choices]
        if len(matches) == 1:
            mapping[key] = matches[0]
    required = ("draw_id", "date", "n1", "n2", "n3", "n4", "n5")
    missing = [key for key in required if key not in mapping]
    return mapping, missing


mapping, missing_mapping_fields = resolve_column_mapping(header, aliases)
if missing_mapping_fields:
    failure = {
        "status": "BLOCKED_SOURCE_SCHEMA_MAPPING",
        "source_url": URL,
        "final_url": final_url,
        "content_type": content_type,
        "last_modified": last_modified,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "bytes": len(raw),
        "sha256": sha256,
        "encoding": encoding_used,
        "delimiter_repr": repr(delimiter),
        "header": header,
        "candidate_column_mapping_zero_based": mapping,
        "missing_required_mapping_fields": missing_mapping_fields,
        "canonical_history_modified": False,
        "v294_modified": False,
        "production_authorized": False,
    }
    (OUT / "audit.json").write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(failure, ensure_ascii=False, indent=2))
    raise SystemExit("BLOCKED: official CSV schema cannot be mapped unambiguously")

# Read the frozen canonical baseline as a comparison target only.
CANONICAL_URL = (
    "https://raw.githubusercontent.com/mxjava/chispazo-exact5-lab/"
    "research/operational-lab-run-20261121/data/history/Chispazo_through_12249.csv"
)
with urllib.request.urlopen(CANONICAL_URL, timeout=45) as response:
    canonical_raw = response.read()
canonical_text = canonical_raw.decode("utf-8-sig")
canonical_rows = list(csv.DictReader(io.StringIO(canonical_text)))
official_index = {}
official_invalid = []
for line_no, row in enumerate(data_rows, start=2):
    try:
        draw = int(row[mapping["draw_id"]])
        nums = tuple(int(row[mapping[f"n{i}"]]) for i in range(1, 6))
        date = datetime.strptime(row[mapping["date"]].strip(), "%d/%m/%Y").date().isoformat()
        if len(set(nums)) != 5 or any(n < 1 or n > 28 for n in nums) or tuple(sorted(nums)) != nums:
            raise ValueError("numbers must be five unique ascending integers in 1..28")
        if draw in official_index:
            raise ValueError("duplicate draw id")
        official_index[draw] = (nums, date)
    except (ValueError, IndexError, KeyError) as exc:
        official_invalid.append({"line": line_no, "row": row, "error": str(exc)})

canonical_index = {}
canonical_invalid = []
for line_no, row in enumerate(canonical_rows, start=2):
    try:
        draw = int(row["CONCURSO"])
        nums = tuple(int(row[f"R{i}"]) for i in range(1, 6))
        date = datetime.strptime(row["FECHA"].strip(), "%Y-%m-%d").date().isoformat()
        if draw in canonical_index:
            raise ValueError("duplicate draw id")
        canonical_index[draw] = (nums, date)
    except (ValueError, KeyError) as exc:
        canonical_invalid.append({"line": line_no, "row": row, "error": str(exc)})

overlap = sorted(set(canonical_index) & set(official_index))
conflicts = [
    {"draw_id": draw, "canonical": canonical_index[draw], "official": official_index[draw]}
    for draw in overlap if canonical_index[draw] != official_index[draw]
]
canonical_not_in_official = sorted(set(canonical_index) - set(official_index))
official_new_ids = sorted(set(official_index) - set(canonical_index))
official_ids_sorted = sorted(official_index)
official_gaps = [
    [a + 1, b - 1] for a, b in zip(official_ids_sorted, official_ids_sorted[1:]) if b != a + 1
]
post_baseline_ids = sorted(draw for draw in official_index if draw > 12249)
daily_pair_structure = analyze_daily_pair_structure(data_rows, mapping["draw_id"], mapping["date"])
audit_status = "BLOCKED_CANONICAL_CONFLICTS" if (conflicts or official_invalid or canonical_invalid or official_gaps or canonical_not_in_official or not daily_pair_structure["post_transition_ids_contiguous"] or daily_pair_structure["anomaly_count"] > 0) else "SOURCE_RECONCILIATION_CLEAN"
with (OUT / "canonical_official_conflicts.csv").open("w", newline="", encoding="utf-8") as conflict_file:
    writer = csv.writer(conflict_file)
    writer.writerow(["CONCURSO", "FECHA", "CANONICAL_R1_R5", "OFFICIAL_R1_R5"])
    for item in conflicts:
        writer.writerow([item["draw_id"], item["canonical"][1], " ".join(map(str, item["canonical"][0])), " ".join(map(str, item["official"][0]))])

reconciliation = {
    "canonical_source_url": CANONICAL_URL,
    "canonical_sha256": hashlib.sha256(canonical_raw).hexdigest(),
    "canonical_rows": len(canonical_rows),
    "canonical_unique_draw_ids": len(canonical_index),
    "official_unique_draw_ids": len(official_index),
    "overlap_rows_compared": len(overlap),
    "overlap_conflicts": conflicts[:100],
    "overlap_conflict_count": len(conflicts),
    "canonical_draw_ids_missing_from_official": canonical_not_in_official[:100],
    "canonical_missing_from_official_count": len(canonical_not_in_official),
    "official_new_draw_id_count": len(official_new_ids),
    "official_post_baseline_draw_count": len(post_baseline_ids),
    "official_post_baseline_draw_id_min": min(post_baseline_ids) if post_baseline_ids else None,
    "official_post_baseline_draw_id_max": max(post_baseline_ids) if post_baseline_ids else None,
    "official_post_baseline_ids_contiguous": post_baseline_ids_are_contiguous(post_baseline_ids),
    "official_new_draw_id_min": min(official_new_ids) if official_new_ids else None,
    "official_new_draw_id_max": max(official_new_ids) if official_new_ids else None,
    "official_id_gaps": official_gaps[:100],
    "official_invalid_rows": official_invalid[:100],
    "official_invalid_row_count": len(official_invalid),
    "canonical_invalid_rows": canonical_invalid[:100],
    "canonical_invalid_row_count": len(canonical_invalid),
    "merge_performed": False,
    "canonical_history_modified": False,
}
report = {
    "status": audit_status,
    "source_url": URL,
    "final_url": final_url,
    "content_type": content_type,
    "last_modified": last_modified,
    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    "bytes": len(raw),
    "sha256": sha256,
    "encoding": encoding_used,
    "delimiter_repr": repr(delimiter),
    "header": header,
    "row_count_nonempty": len(data_rows),
    "first_rows": data_rows[:5],
    "last_rows": data_rows[-5:],
    "candidate_column_mapping_zero_based": mapping,
    "daily_pair_structure": daily_pair_structure,
    "reconciliation": reconciliation,
    "canonical_history_modified": False,
    "v294_modified": False,
    "production_authorized": False,
}
(OUT / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
if not all(k in mapping for k in ("draw_id", "date", "n1", "n2", "n3", "n4", "n5")) or official_invalid or canonical_invalid or conflicts or canonical_not_in_official or official_gaps:
    print("RECONCILIATION REVIEW REQUIRED: inspect schema, row validity, continuity, and baseline conflicts.", file=sys.stderr)
