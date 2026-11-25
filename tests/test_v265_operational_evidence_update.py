from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v265_operational_evidence_update.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_operational_evidence_update", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

def test_operational_evidence_update_is_valid_and_non_predictive():
    result = MODULE.validate()
    assert result["valid"] is True
    assert result["classification"] == "MECHANISM_DOCUMENTATION_ONLY"
    assert result["V265"] == "ASSOCIATION_SCREEN_ONLY"

def test_cs11_copy_distribution_gap_is_explicit():
    import json
    report = json.loads(MODULE.REPORT.read_text(encoding="utf-8"))
    cs11 = report["sources"]["SGVO-PRO-05"]["CS11"]
    assert cs11["printed_copies_activity_13_1"] == 4
    assert cs11["unnamed_copy_count"] == 1

def test_digital_manifest_does_not_replace_physical_annexes():
    import json
    report = json.loads(MODULE.REPORT.read_text(encoding="utf-8"))
    dvd = report["sources"]["SGVO-PRO-05"]["digital_weekly_DVD_manifest"]
    assert {"Tira_de_Pesaje", "CS-11", "Sumario_de_cierre"}.issubset(set(dvd["not_enumerated_in_DVD_list"]))

def test_no_physical_records_or_predictive_gates_are_claimed():
    import json
    report = json.loads(MODULE.REPORT.read_text(encoding="utf-8"))
    assert report["physical_records_obtained"] == []
    assert report["analysis"]["physical_effect_estimated"] is False
    assert report["analysis"]["OOS_gate_passed"] is False
    assert report["analysis"]["multiplicity_gate_passed"] is False
    assert report["analysis"]["anytime_evalue_gate_passed"] is False
