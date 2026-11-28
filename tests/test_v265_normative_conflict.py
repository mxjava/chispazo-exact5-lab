from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_v265_normative_conflict.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_normative_conflict", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_current_and_legacy_normative_status_are_not_conflated():
    r = MODULE.build_report()
    n = r["normative_status"]
    assert n["sgvo_pro_05_current_normateca_entry"] is True
    assert n["sgvo_pro_05_revision"] == 39
    assert n["sgm_pro_06_public_copy_accessible"] is True
    assert n["sgm_pro_06_current_normateca_entry"] is False
    assert n["sgvo_man_02_in_project_history"] is True
    assert n["sgvo_man_02_current_normateca_entry"] is False
    assert n["sgvo_man_02_pdf_obtained"] is False


def test_current_sequence_wins_over_unconfirmed_legacy_2115_sequence():
    r = MODULE.build_report()
    c = r["chronology"]
    assert c["cs02_and_case_confirmation_before_close"] is True
    assert c["sical_closed_before_weighing_under_current_sgvo_pro_05"] is True
    assert c["weighing_after_close"] is True
    assert c["legacy_sgm_pro_06_says_preferably_before_2115"] is True
    assert c["legacy_timing_used_for_current_model"] is False


def test_segob_regulation_makes_acta_the_official_result_record():
    r = MODULE.build_report()
    legal = r["segob_legal_basis"]
    assert legal["chispazo_regulation_last_reform"] == "2012-03-07"
    assert legal["article_9_close_then_signed_participation_file_pre_draw"] is True
    assert legal["article_9_28_spheres_and_five_extractions"] is True
    assert legal["article_15_acta_contains_background_results_incidents"] is True
    assert legal["article_8_official_results_are_acta_only"] is True
    assert legal["terminal_web_and_mask_are_informational"] is True
    assert legal["cs11_is_acta"] is False


def test_calibration_requirement_is_not_confused_with_actual_compliance():
    r = MODULE.build_report()
    c = r["calibration"]
    assert c["annual_requirement_in_current_sgvo_policy_25"] is True
    assert c["actual_calendar_obtained"] is False
    assert c["asset_specific_certificate_obtained"] is False
    assert c["calibration_measurements_consumed_by_v265"] is False


def test_v265_is_only_a_label_association_screen_without_provenance():
    r = MODULE.build_report()
    v = r["v265_evaluator"]
    assert v["machine_id_label_consumed"] is True
    assert v["sphere_set_id_label_consumed"] is True
    assert v["preclose_timestamp_declared_required"] is True
    assert v["source_provenance_required"] is False
    assert v["validator_checks_source_provenance"] is False
    assert v["per_sphere_weights_consumed"] is False
    assert v["per_sphere_rfid_mapping_consumed"] is False
    assert v["extraction_order_consumed"] is False
    assert v["per_extraction_timestamps_consumed"] is False
    assert v["physical_bias_evidence"] is False
    assert v["actionable_for_betting"] is False
    assert v["anytime_evalue_gate_implemented"] is False


def test_no_physical_draw_records_or_statistical_gates_are_claimed():
    r = MODULE.build_report()
    a = r["analysis"]
    assert a["uses_authentic_draw_level_physical_records"] is False
    assert a["uses_draw_outcomes"] is False
    assert a["uses_synthetic_records"] is False
    assert a["statistical_tests_run"] == []
    assert a["oos_gate_passed"] is False
    assert a["multiplicity_gate_passed"] is False
    assert a["anytime_evalue_gate_passed"] is False


def test_preservation_guards_remain_explicit():
    assert MODULE.build_report()["preservation"] == {
        "canonical_history_touched": False,
        "v294_touched": False,
        "main_written": False,
        "merge_or_promotion": False,
    }


def test_checked_in_json_matches_reproducible_audit():
    saved = ROOT / "reports/V265_NORMATIVE_CONFLICT_RECONCILIATION_20261128.json"
    assert json.loads(saved.read_text(encoding="utf-8")) == MODULE.build_report()
