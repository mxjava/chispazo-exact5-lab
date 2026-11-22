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
mapping = {}
for key, choices in aliases.items():
    matches = [i for i, name in enumerate(normalized) if name in choices]
    if len(matches) == 1:
        mapping[key] = matches[0]

report = {
    "status": "SCHEMA_DISCOVERY_ONLY",
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
    "canonical_history_modified": False,
    "v294_modified": False,
    "production_authorized": False,
}
(OUT / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
if not all(k in mapping for k in ("draw_id", "date", "n1", "n2", "n3", "n4", "n5")):
    print("SCHEMA REVIEW REQUIRED: one or more required columns were not uniquely identified.", file=sys.stderr)
