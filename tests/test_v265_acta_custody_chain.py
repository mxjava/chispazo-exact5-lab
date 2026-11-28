from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_v265_acta_custody_chain.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_acta_custody_chain", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_all_new_acta_chain_anchors_are_present():
    report = MODULE.build_report()
    assert report["all_document_anchors_pass"] is True
    assert all(report["document_anchors"].values())


def test_acta_and_cs11_are_not_conflated():
    chain = MODULE.build_report()["acta_chain"]
    assert chain["acta_is_official_result_record"] is True
    assert chain["cs11_is_separate_record_not_acta"] is True
    assert chain["draw_level_acta_and_annexes_obtained"] is False


def test_weekly_archive_and_delayed_acta_signatures_are_retrospective():
    chain = MODULE.build_report()["acta_chain"]
    assert chain["weekly_annex_dvd_delivery"] is True
    assert chain["weekly_dvd_or_delivery_office_obtained"] is False
    assert chain["acta_signature_can_be_deferred_max_five_business_days_under_exception"] is True
    assert chain["signed_acta_scanned_to_oic"] is True


def test_discrepancy_incident_risk_and_access_records_are_distinct():
    chain = MODULE.build_report()["acta_chain"]
    assert chain["sical_discrepancy_requires_both_screens_and_provider_clarification"] is True
    assert chain["incidents_recorded_in_acta"] is True
    assert chain["cs18_is_optional_risk_communication"] is True
    assert chain["cs12_is_access_record"] is True


def test_video_sources_are_not_collapsed_into_one_artifact():
    chain = MODULE.build_report()["acta_chain"]
    assert chain["continuous_recording_from_weighing_to_draw"] is True
    assert chain["room_cameras_record_exhibitor_numbers"] is True
    assert chain["original_video_master_obtained"] is False


def test_v265_stays_non_predictive_and_does_not_consume_raw_physical_evidence():
    v = MODULE.build_report()["v265_evaluator"]
    assert "machine_id" in v["required_metadata_fields"]
    assert "sphere_set_id" in v["required_metadata_fields"]
    assert v["source_provenance_required"] is False
    assert v["physical_bias_evidence"] is False
    assert v["actionable_for_betting"] is False
    assert v["per_sphere_weights_consumed"] is False
    assert v["per_sphere_rfid_mapping_consumed"] is False
    assert v["extraction_order_consumed"] is False
    assert v["per_extraction_timestamps_consumed"] is False
    assert v["anytime_evalue_gate_implemented"] is False


def test_no_outcome_or_synthetic_analysis_and_all_gates_remain_closed():
    a = MODULE.build_report()["analysis"]
    assert a["uses_draw_outcomes"] is False
    assert a["uses_authentic_draw_level_physical_records"] is False
    assert a["uses_synthetic_records"] is False
    assert a["statistical_tests_run"] == []
    assert a["oos_gate_passed"] is False
    assert a["multiplicity_gate_passed"] is False
    assert a["anytime_evalue_gate_passed"] is False


def test_preservation_contract_is_explicit():
    assert MODULE.build_report()["preservation"] == {
        "canonical_history_touched": False,
        "v294_touched": False,
        "main_written": False,
        "merge_or_promotion": False,
    }


def test_checked_in_json_matches_reproducible_script():
    expected = ROOT / "reports/V265_ACTA_CUSTODY_CHAIN_20261128.json"
    assert json.loads(expected.read_text(encoding="utf-8")) == MODULE.build_report()
