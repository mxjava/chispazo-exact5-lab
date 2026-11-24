#!/usr/bin/env python3
"""Validate the 2026-11-24 Chispazo physical-evidence document reconciliation.

This is a deterministic validator of normalized facts transcribed from the
linked official public documents and the checked-in V265 source/template.
It does not scrape websites, use draw outcomes, synthesize physical records,
or estimate a physical/predictive effect.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "V265_PHYSICAL_EVIDENCE_DELTA_20261124.json"
MATRIX = ROOT / "reports" / "V265_PHYSICAL_EVIDENCE_MATRIX_20261124.csv"
V265_AUDIT_SCRIPT = ROOT / "scripts" / "audit_v265_evidence_contract.py"


def _load_v265_audit() -> dict:
    spec = importlib.util.spec_from_file_location("v265_evidence_contract_audit", V265_AUDIT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing V265 evidence-contract audit")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_report()


def validate() -> dict:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert report["audit_id"] == "V265_PHYSICAL_EVIDENCE_DELTA_20261124"
    assert report["uses_draw_outcomes"] is False
    assert report["uses_synthetic_records"] is False
    assert report["classification"] == "MECHANISM_DOCUMENTATION_ONLY"
    assert report["predictive_advantage_claimed"] is False

    status = report["normative_status"]
    assert status["SGVO-PRO-05"] == "CURRENT_LISTED_REV39"
    assert status["SGVO-MAN-02"] == "PROJECT_AND_DOCUMENT_TYPE_RESERVED"
    assert status["SGM-PRO-06"] == "LEGACY_PUBLIC_COPY_NOT_LISTED_CURRENT"

    chronology = report["chronology_reconciliation"]
    assert chronology["SGVO_same_draw_weighing"] == "POST_CLOSE"
    assert chronology["Regulation_article_9_urn_loading"] == "PRE_CLOSE"
    assert chronology["legacy_SGM-PRO-06_preclose_preference"].startswith("PREFERABLY")
    assert chronology["status"] == "UNRESOLVED_PHYSICAL_SEQUENCE"

    crossref = report["weight_policy_cross_reference"]
    assert crossref["actual_weight_policy"] == 6
    assert crossref["activity_5_2_reference"] == 8
    assert crossref["quality_plan_item_2_reference"] == 8
    assert "electronic signature" in crossref["policy_8_subject"]

    tira = report["Tira_de_Pesaje"]
    assert tira["current_public_schema"]["per_sphere_weight"] is True
    assert tira["current_public_schema"]["explicit_start_timestamp"] is False
    assert tira["current_public_schema"]["explicit_end_timestamp"] is False
    assert tira["legacy_SGM-PRO-06_schema"]["start_and_end_datetime"] is True
    assert tira["legacy_SGM-PRO-06_schema"]["status"] == "NOT_CURRENT_LISTED"

    cs11 = report["CS11"]
    assert cs11["is_the_Acta"] is False
    assert cs11["timing"].startswith("After extraction")

    rfid = report["sources"]["RFID_management_report"]
    assert rfid["reported_machines"]["total"] == 14
    assert rfid["sets_reported"]["arithmetic_consistent"] is False
    assert rfid["expansion_project"]["status_at_2024-06"] == "NOT_AUTHORIZED"
    assert report["rfid_limits"]["case_RFID_confirmed"] is False

    v265 = report["V265"]
    assert v265["evidence_class"] == "ASSOCIATION_SCREEN_ONLY"
    assert v265["physical_bias_evidence"] is False
    assert v265["evaluator_consumes"]["per_sphere_weights"] is False
    assert v265["evaluator_consumes"]["per_sphere_RFID_mapping"] is False
    assert v265["evaluator_consumes"]["extraction_order"] is False
    assert v265["evaluator_consumes"]["per_extraction_timestamps"] is False
    assert v265["evaluator_consumes"]["source_provenance"] is False
    assert v265["holm_family_optional"] is True
    assert v265["anytime_evalue_gate"] is False

    gates = report["analysis"]
    assert gates["OOS_gate_passed"] is False
    assert gates["multiplicity_gate_passed"] is False
    assert gates["anytime_evalue_gate_passed"] is False
    assert report["physical_records_obtained"] == []

    assert len(rows) == 23
    assert all(row["prospective_same_draw"] in {"NO", "conditional", "CONDITIONAL"} for row in rows)
    assert all(row["status"] not in {"AUTHENTIC_RECORD_OBTAINED", "EVIDENCE_OF_BIAS"} for row in rows)

    v265_audit = _load_v265_audit()
    assert v265_audit["evidence_class"] == v265["evidence_class"]
    assert v265_audit["physical_bias_evidence"] is False
    assert v265_audit["evaluator_consumes"] == v265["evaluator_consumes"]
    assert v265_audit["p_family_optional"] is True
    assert v265_audit["anytime_evalue_gate_implemented"] is False

    return {
        "audit_id": report["audit_id"],
        "matrix_rows": len(rows),
        "classification": report["classification"],
        "V265_class": v265["evidence_class"],
        "chronology": chronology["status"],
        "valid": True,
    }


if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, sort_keys=True))
