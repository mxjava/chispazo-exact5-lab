from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_v265_physical_operational_delta.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_physical_operational_delta", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_public_source_map_anchors_are_complete():
    report = MODULE.build_report()
    assert report["all_source_map_checks_pass"] is True
    assert all(report["source_map_checks"].values())


def test_cs11_distribution_is_corrected_but_receipts_remain_unavailable():
    report = MODULE.build_report()
    assert report["evidence"]["cs11_prescribed_distribution_complete"] is True
    assert report["evidence"]["cs11_per_contest_delivery_receipts_obtained"] is False


def test_rfid_and_maintenance_are_not_misrepresented_as_draw_level_data():
    report = MODULE.build_report()
    assert report["evidence"]["rfid_reported_historically"] is True
    assert report["evidence"]["rfid_per_sphere_mapping_obtained"] is False
    assert report["evidence"]["reported_set_count_internally_inconsistent"] is True
    assert report["evidence"]["contract_058_2024_per_asset_service_records_obtained"] is False
    assert report["evidence"]["invitation_222_2026_award_or_service_reports_obtained"] is False
    assert report["evidence"]["current_scale_calibration_certificate_obtained"] is False
    assert report["evidence"]["current_public_calibration_interval_verified"] is False


def test_v265_does_not_consume_required_physical_inputs_or_authorize_betting():
    report = MODULE.build_report()
    v265 = report["v265_evaluator"]
    assert v265["machine_id_label_consumed"] is True
    assert v265["sphere_set_id_label_consumed"] is True
    assert v265["per_sphere_weights_consumed"] is False
    assert v265["per_sphere_rfid_mapping_consumed"] is False
    assert v265["extraction_order_consumed"] is False
    assert v265["per_extraction_timestamps_consumed"] is False
    assert v265["source_provenance_required"] is False
    assert v265["preclose_validator_checks_source_provenance"] is False
    assert v265["physical_bias_evidence"] is False
    assert v265["actionable_for_betting"] is False
    assert v265["anytime_evalue_gate_implemented"] is False


def test_no_draw_analysis_or_gate_is_claimed():
    report = MODULE.build_report()
    assert report["analysis"]["type"] == "PUBLIC_DOCUMENT_STATIC_CROSSWALK"
    assert report["analysis"]["uses_draw_outcomes"] is False
    assert report["analysis"]["uses_synthetic_records"] is False
    assert report["analysis"]["statistical_tests_run"] == []
    assert report["analysis"]["oos_gate_passed"] is False
    assert report["analysis"]["multiplicity_gate_passed"] is False
    assert report["analysis"]["anytime_evalue_gate_passed"] is False
    assert report["evidence"]["draw_level_original_records_obtained"] is False


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
    saved = ROOT / "reports/V265_PHYSICAL_OPERATIONAL_DELTA_20261127.json"
    assert json.loads(saved.read_text(encoding="utf-8")) == report
