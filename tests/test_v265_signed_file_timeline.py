from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_v265_signed_file_timeline.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_signed_file_timeline", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_source_map_timeline_checks_pass():
    report = MODULE.build_report()
    assert report["all_checks_pass"] is True
    assert all(report["checks"].values())


def test_participation_signature_is_postclose_pre_draw_not_preclose():
    report = MODULE.build_report()
    assert report["key_findings"]["participation_signature_stage"] == "AFTER_SICAL_CLOSE_CHECK_BEFORE_DRAW"
    assert report["key_findings"]["participation_signature_is_preclose"] is False


def test_cs11_distribution_ambiguity_is_not_claimed_as_missing_copy():
    report = MODULE.build_report()
    assert report["key_findings"]["cs11_copy_distribution_complete"] is False
    assert report["draw_level_original_records_obtained"] is False


def test_no_predictive_or_physical_bias_claim():
    report = MODULE.build_report()
    assert report["key_findings"]["physical_bias_evidence"] is False
    assert report["key_findings"]["predictive_edge_evidence"] is False
    assert report["oos_gate_passed"] is False
    assert report["multiplicity_gate_passed"] is False
    assert report["anytime_evalue_gate_passed"] is False


def test_checked_in_json_matches_reproducible_audit():
    report = MODULE.build_report()
    saved = ROOT / "reports/V265_SIGNED_FILE_TIMELINE_20261126.json"
    assert json.loads(saved.read_text(encoding="utf-8")) == report
