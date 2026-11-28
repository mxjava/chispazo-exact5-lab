from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_v265_sphere_set_substitution_timing.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_sphere_set_substitution_timing", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_official_sequence_anchors_are_complete():
    report = MODULE.build_report()
    assert report["all_anchors_pass"] is True
    assert all(report["anchors"].values())
    assert report["official_sequence"]["failed_weight_can_replace_set_after_close"] is True
    assert report["anchors"]["traditional_motor_procedure_excluded"] is True
    assert report["anchors"]["manual_project_not_current"] is True


def test_sgvo_man02_project_is_not_treated_as_current_instruction():
    report = MODULE.build_report()
    status = report["manual_status"]
    assert status["listed_as_current_vigente"] is False
    assert status["listed_as_project"] is True
    assert status["pdf_content_retrieved"] is False
    assert status["used_as_binding_instruction"] is False


def test_v265_has_one_ambiguous_sphere_set_field():
    report = MODULE.build_report()
    contract = report["v265_contract"]
    assert contract["single_sphere_set_id_field"] is True
    assert contract["planned_vs_actual_fields_present"] is False
    assert contract["preclose_timestamp_comparison_present"] is True


def test_cs11_cannot_be_used_as_preclose_source_for_final_set():
    report = MODULE.build_report()
    assert report["interpretation"]["if_id_source_is_cs11"] == "POST_DRAW_NOT_PRE_CLOSE"
    assert report["interpretation"]["if_id_source_is_activity_3_1"] == "PRE_CLOSE_PLAN_ONLY_NOT_FINAL_AFTER_SUBSTITUTION"


def test_v265_guard_never_claims_physical_bias_or_actionability():
    report = MODULE.build_report()
    contract = report["v265_contract"]
    assert contract["physical_bias_evidence"] is False
    assert contract["actionable_for_betting"] is False
    assert contract["per_sphere_weights_consumed"] is False
    assert contract["per_sphere_rfid_mapping_consumed"] is False
    assert contract["extraction_order_consumed"] is False
    assert contract["per_extraction_timestamps_consumed"] is False
    assert contract["source_provenance_required"] is False
    assert contract["anytime_evalue_gate_implemented"] is False


def test_no_outcomes_synthetic_records_or_project_gates_are_claimed():
    report = MODULE.build_report()
    assert report["analysis"]["uses_draw_outcomes"] is False
    assert report["analysis"]["uses_synthetic_records"] is False
    assert report["analysis"]["statistical_tests_run"] == []
    assert report["analysis"]["oos_gate_passed"] is False
    assert report["analysis"]["multiplicity_gate_passed"] is False
    assert report["analysis"]["anytime_evalue_gate_passed"] is False


def test_preservation_guards_are_explicit():
    report = MODULE.build_report()
    assert report["preservation"] == {
        "canonical_history_touched": False,
        "v294_touched": False,
        "main_written": False,
        "merge_or_promotion": False,
    }


def test_checked_in_json_matches_reproducible_audit():
    report = MODULE.build_report()
    saved = ROOT / "reports/V265_SPHERE_SET_SUBSTITUTION_TIMING_20261128.json"
    assert json.loads(saved.read_text(encoding="utf-8")) == report
