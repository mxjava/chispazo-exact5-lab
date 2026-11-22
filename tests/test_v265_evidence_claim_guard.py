from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v265_evidence_contract.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_evidence_contract", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_v265_guard_never_claims_physical_bias_or_actionability():
    report = MODULE.build_report()
    assert report["evidence_class"] == "ASSOCIATION_SCREEN_ONLY"
    assert report["physical_bias_evidence"] is False
    assert report["actionable_for_betting"] is False
    assert report["anytime_evalue_gate_implemented"] is False


def test_v265_template_measurements_are_not_evaluator_inputs():
    report = MODULE.build_report()
    assert len(report["template_per_sphere_weight_columns"]) == 28
    assert report["template_rfid_columns"] == ["rfid_verified"]
    assert report["template_source_provenance_columns"] == [
        "source_document", "source_url", "source_sha256"
    ]
    assert report["evaluator_consumes"]["machine_id"] is True
    assert report["evaluator_consumes"]["sphere_set_id"] is True
    assert report["evaluator_consumes"]["per_sphere_weights"] is False
    assert report["evaluator_consumes"]["per_sphere_rfid_mapping"] is False
    assert report["evaluator_consumes"]["extraction_order"] is False
    assert report["evaluator_consumes"]["per_extraction_timestamps"] is False
    assert report["evaluator_consumes"]["source_provenance"] is False


def test_v265_multiplicity_is_optional_and_anytime_gate_is_absent():
    report = MODULE.build_report()
    assert report["one_sided_t_test_present"] is True
    assert report["holm_adjustment_present"] is True
    assert report["p_family_optional"] is True
    assert report["anytime_evalue_gate_implemented"] is False
