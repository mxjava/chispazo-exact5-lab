import json
from pathlib import Path
from origen.sgvo_source_audit import audit_source_snapshot

SNAPSHOT = Path(__file__).resolve().parents[1] / "data" / "official-overlays" / "2026-11-23_sgvo_pro05_source_contract.json"

def load():
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))

def test_policy_cross_reference_mismatch_is_detected_without_bias_claim():
    r = audit_source_snapshot(load())
    assert r["findings"]["POLICY_5_2_AND_QUALITY_PLAN_CROSS_REFERENCE_MISMATCH"] is True
    assert r["classification"] == "MECHANISM_EVIDENCE_ONLY"
    assert r["physical_bias_claim"] is False and r["predictive_advantage_claim"] is False

def test_tira_signatory_role_discrepancy_is_detected():
    assert audit_source_snapshot(load())["findings"]["TIRA_SIGNATORY_ROLE_LABEL_MISMATCH"] is True

def test_cs11_glossary_specifies_hour_but_quality_plan_checklist_omits_it():
    r = audit_source_snapshot(load())
    assert r["findings"]["CS11_GLOSSARY_SPECIFIES_DRAW_HOUR"] is True
    assert r["findings"]["CS11_QUALITY_PLAN_CHECKLIST_OMITS_DRAW_HOUR"] is True
    assert r["findings"]["CS11_TEMPLATE_NOT_OBTAINED"] is True

def test_reserved_manual_is_never_treated_as_current_authority():
    r = audit_source_snapshot(load())
    assert r["findings"]["SGVO_MAN_02_IS_RESERVED_PROJECT_LEAD_ONLY"] is True
    assert r["reserved_manual_fields_authoritative"] is False

def test_regulation_and_procedure_sequence_requires_clarification():
    assert audit_source_snapshot(load())["findings"]["REGULATION_ARTICLE_9_VS_PRO05_SEQUENCE_REQUIRES_CLARIFICATION"] is True

def test_electronic_signature_is_not_preclose_physical_covariate():
    assert audit_source_snapshot(load())["findings"]["ELECTRONIC_SIGNATURE_IS_POST_CLOSE_PRE_DRAW"] is True

def test_maintenance_status_and_rfid_trace_fail_closed():
    r = audit_source_snapshot(load())
    assert r["findings"]["CURRENT_MACHINE_MAINTENANCE_STATUS_UNKNOWN"] is True
    assert r["findings"]["RFID_EXISTS_BUT_DRAW_LEVEL_TRACE_IS_MISSING"] is True

def test_traditional_procedure_and_building_tender_are_excluded():
    r = audit_source_snapshot(load())
    assert r["findings"]["PRO34_TRADITIONAL_SCOPE_EXCLUDED_FROM_CHISPAZO"] is True
    assert r["findings"]["2026_222_BUILDING_ELECTRICAL_TENDER_EXCLUDED"] is True

def test_correcting_policy_reference_removes_cross_reference_finding():
    d = load()
    d["authoritative_excerpts"]["activity_5_2"]["policy_reference"] = 6
    d["authoritative_excerpts"]["quality_plan_weighing"]["policy_reference"] = 6
    assert audit_source_snapshot(d)["findings"]["POLICY_5_2_AND_QUALITY_PLAN_CROSS_REFERENCE_MISMATCH"] is False

def test_matching_signatory_roles_remove_role_discrepancy():
    d = load()
    d["authoritative_excerpts"]["activity_5_4_signatures"]["role_label"] = d["authoritative_excerpts"]["glossary_tira_signatory_role"]["role_label"]
    assert audit_source_snapshot(d)["findings"]["TIRA_SIGNATORY_ROLE_LABEL_MISMATCH"] is False
