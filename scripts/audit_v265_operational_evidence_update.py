#!/usr/bin/env python3
"""Deterministic validator for the 2026-11-25 official Chispazo evidence update.

Validates normalized facts transcribed from linked official public sources and
the current V265 claim guard. It does not scrape, synthesize physical data,
read draw outcomes, or estimate a predictive effect.
"""
from __future__ import annotations
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "V265_OPERATIONAL_EVIDENCE_UPDATE_20261125.json"
MATRIX = ROOT / "reports" / "V265_OPERATIONAL_EVIDENCE_MATRIX_20261125.csv"
V265 = ROOT / "src" / "v265" / "CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"

def validate() -> dict:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    with MATRIX.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert report["audit_id"] == "V265_OPERATIONAL_EVIDENCE_UPDATE_20261125"
    assert report["classification"] == "MECHANISM_DOCUMENTATION_ONLY"
    assert report["uses_draw_outcomes"] is False
    assert report["uses_synthetic_records"] is False
    assert report["physical_records_obtained"] == []
    norm = report["normateca"]
    assert norm["SGVO_PRO_05"]["listed_current"] is True
    assert norm["SGVO_PRO_05"]["revision"] == 39
    assert norm["SGM_PRO_06_listed_current"] is False
    assert norm["SGVO_MAN_02_listed_current"] is False
    assert {x["code"] for x in norm["traditional_procedures_listed_separately"]} == {"SGVO-PRO-08", "SGVO-PRO-34", "SGVO-PRO-15"}
    src = report["sources"]["SGVO-PRO-05"]
    assert "TIRA DE PESAJE" in src["Chispazo_attachment_matrix"]
    assert src["Tira_de_Pesaje"]["included_as_Chispazo_Acta_annex"] is True
    assert src["Tira_de_Pesaje"]["explicit_start_end_timestamps_in_public_definition"] is False
    assert src["Tira_de_Pesaje"]["explicit_sphere_number_or_RFID_mapping_in_public_definition"] is False
    cs11 = src["CS11"]
    assert cs11["printed_copies_activity_13_1"] == 4
    assert cs11["copies_activity_13_6"] == 3
    assert cs11["unnamed_copy_count"] == 1
    dvd = src["digital_weekly_DVD_manifest"]
    assert "Tira_de_Pesaje" in dvd["not_enumerated_in_DVD_list"]
    assert "CS-11" in dvd["not_enumerated_in_DVD_list"]
    assert src["Acta"]["exceptional_signature_delay"].endswith("5_business_days_if_printing_failure_and_result_not_compromised")
    sig = src["electronic_signatures"]
    assert sig["participations_and_cancellations"] == "generated_immediately_after_sales_close"
    assert sig["winner_relation"] == "generated_after_winner_numbers_are_captured"
    legacy = report["sources"]["SGM_PRO_06_revision_21_project_copy"]
    assert legacy["folder_status"] == "PROJECT"
    assert legacy["authority_status"] == "NOT_CURRENT_LISTED"
    assert legacy["Chispazo_weighing_wording"].endswith("21:15")
    assert report["V265"]["classification"] == "ASSOCIATION_SCREEN_ONLY"
    assert report["V265"]["physical_bias_evidence"] is False
    assert report["V265"]["anytime_evalue_gate_implemented"] is False
    spec = importlib.util.spec_from_file_location("v265_physical", V265)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load V265 evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    guard = module.physical_evidence_guard()
    assert guard["physical_bias_evidence"] is False
    assert guard["actionable_for_betting"] is False
    assert guard["per_sphere_weights_consumed"] is False
    assert guard["per_sphere_rfid_mapping_consumed"] is False
    assert guard["extraction_order_consumed"] is False
    assert guard["per_extraction_timestamps_consumed"] is False
    assert guard["anytime_evalue_gate_implemented"] is False
    assert len(rows) == 27
    assert any(r["variable_or_record"] == "CS-11 winning numbers" and r["same_draw_preclose_usable"] == "No" for r in rows)
    assert any(r["variable_or_record"] == "Traditional wooden-ball procedures" and r["same_draw_preclose_usable"] == "Not applicable" for r in rows)
    assert report["analysis"]["OOS_gate_passed"] is False
    assert report["analysis"]["multiplicity_gate_passed"] is False
    assert report["analysis"]["anytime_evalue_gate_passed"] is False
    assert report["repository_protection"]["V294_changed"] is False
    assert report["repository_protection"]["canonical_history_changed"] is False
    custodian = report["sources"]["SAF_MAN_12"]
    assert custodian["issue_date"] == "2026-02"
    assert custodian["functions"]["physical_and_digital_custody_of_actas_videos_operational_records"] is True
    assert custodian["functions"]["facilitate_original_documents_for_certification"] is True
    maintenance = report["sources"]["Maintenance_contract_058_2024"]
    assert maintenance["contract"] == "058-2024"
    assert maintenance["scope"].find("Chispazo") >= 0
    assert maintenance["per_machine_serials_published"] is False
    assert report["timing_decisions"]["custodial_office"].startswith("SAF-MAN-12")
    assert report["repository_protection"]["main_written"] is False
    return {"audit_id": report["audit_id"], "matrix_rows": len(rows), "new_findings": len(report["new_findings"]), "classification": report["classification"], "V265": guard["evidence_class"], "valid": True}

if __name__ == "__main__":
    print(json.dumps(validate(), ensure_ascii=False, sort_keys=True))
