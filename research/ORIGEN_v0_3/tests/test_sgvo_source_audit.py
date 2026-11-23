from __future__ import annotations

import copy
import json
from pathlib import Path

from origen.sgvo_source_audit import audit_source_snapshot

SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "official-overlays"
    / "2026-11-23_sgvo_pro05_source_contract.json"
)


def load_snapshot():
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_detects_policy_8_cross_reference_error_without_claiming_bias():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["POLICY_5_2_AND_QUALITY_PLAN_CROSS_REFERENCE_MISMATCH"] is True
    assert result["classification"] == "MECHANISM_EVIDENCE_ONLY"
    assert result["physical_bias_claim"] is False
    assert result["predictive_advantage_claim"] is False


def test_detects_tira_signatory_role_label_discrepancy():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["TIRA_SIGNATORY_ROLE_LABEL_MISMATCH"] is True


def test_cs11_time_finding_is_scoped_to_public_plan_not_actual_template():
    snapshot = load_snapshot()
    result = audit_source_snapshot(snapshot)
    assert result["findings"]["CS11_TEMPLATE_NOT_EMBEDDED_IN_PUBLIC_PRO05"] is True
    assert result["findings"]["CS11_TIME_FIELD_NOT_SPECIFIED_IN_PUBLIC_PLAN"] is True
    assert "Hora" not in snapshot["authoritative_excerpts"]["quality_plan_cs11_fields"]["fields"]


def test_reserved_manual_never_becomes_current_authority():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["SGVO_MAN_02_IS_RESERVED_PROJECT_LEAD_ONLY"] is True
    assert result["manual_draft_fields_authoritative"] is False


def test_article_9_sequence_conflict_is_explicitly_blocked_for_interpretation():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["REGULATION_ARTICLE_9_VS_PRO05_SEQUENCE_REQUIRES_CLARIFICATION"] is True


def test_signature_is_not_a_preclose_physical_covariate():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["ELECTRONIC_SIGNATURE_IS_POST_CLOSE_PRE_DRAW"] is True


def test_maintenance_and_rfid_claims_fail_closed_without_draw_level_records():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["CURRENT_MACHINE_MAINTENANCE_STATUS_UNKNOWN"] is True
    assert result["findings"]["RFID_EXISTS_BUT_DRAW_LEVEL_TRACE_IS_MISSING"] is True


def test_traditional_procedure_and_building_electrical_tender_are_excluded():
    result = audit_source_snapshot(load_snapshot())
    assert result["findings"]["PRO34_TRADITIONAL_SCOPE_EXCLUDED_FROM_CHISPAZO"] is True
    assert result["findings"]["2026_222_ELECTRICAL_BUILDING_MAINTENANCE_EXCLUDED"] is True


def test_corrected_source_reference_removes_policy_mismatch():
    snapshot = load_snapshot()
    snapshot["authoritative_excerpts"]["activity_5_2"]["policy_reference"] = 6
    snapshot["authoritative_excerpts"]["quality_plan_weighing"]["policy_reference"] = 6
    result = audit_source_snapshot(snapshot)
    assert result["findings"]["POLICY_5_2_AND_QUALITY_PLAN_CROSS_REFERENCE_MISMATCH"] is False


def test_matching_signatory_role_labels_remove_role_mismatch():
    snapshot = load_snapshot()
    snapshot["authoritative_excerpts"]["activity_5_4_signatures"]["role_label"] = (
        snapshot["authoritative_excerpts"]["glossary_tira_signatory_role"]["role_label"]
    )
    result = audit_source_snapshot(snapshot)
    assert result["findings"]["TIRA_SIGNATORY_ROLE_LABEL_MISMATCH"] is False
