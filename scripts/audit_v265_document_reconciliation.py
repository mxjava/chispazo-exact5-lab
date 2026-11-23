#!/usr/bin/env python3
"""Deterministic validator for the 2026-11-23 official-document reconciliation."""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "V265_DOCUMENT_RECONCILIATION_20261123.json"
MATRIX = ROOT / "reports" / "V265_PHYSICAL_EVIDENCE_MATRIX_20261123.csv"

def validate() -> dict:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert report["documents"]["SGVO-PRO-05"]["listed_current"] is True
    sgm = report["documents"]["SGM-PRO-06"]
    assert sgm["path_contains_vigentes"] is True and sgm["listed_current"] is False
    assert report["weight_specs"]["reconciled"] is False
    assert report["chronology"]["reconciled"] is False
    assert report["chronology"]["same_draw_weight_eligibility"].startswith("BLOCKED")
    assert report["Tira_schema_if_SGM_PRO_06_applies"]["start_and_end_datetime_printed"] is True
    assert report["Tira_schema_if_SGM_PRO_06_applies"]["extraction_order_or_per_extraction_timestamp"] is False
    assert report["V265"]["physical_bias_evidence"] is False
    assert report["V265"]["anytime_evalue_gate_implemented"] is False
    assert report["classification"] == "MECHANISM_DOCUMENTATION_ONLY"
    assert report["predictive_advantage_claimed"] is False
    assert len(rows) == 15
    assert any(row["variable"] == "sphere_weight_01_to_28" and row["status"] == "NO_AUTHENTIC_TIRA_OBTAINED" for row in rows)
    return {"report_id": report["audit_id"], "matrix_rows": len(rows), "classification": report["classification"], "valid": True}

if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False))
