from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v265_physical_evidence_delta.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_physical_evidence_delta", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_current_document_reconciliation_is_valid_and_non_predictive():
    result = MODULE.validate()
    assert result["valid"] is True
    assert result["classification"] == "MECHANISM_DOCUMENTATION_ONLY"
    assert result["V265_class"] == "ASSOCIATION_SCREEN_ONLY"


def test_current_and_legacy_timing_are_not_collapsed():
    result = MODULE.validate()
    assert result["chronology"] == "UNRESOLVED_PHYSICAL_SEQUENCE"


def test_no_physical_contest_records_are_fabricated():
    report = MODULE.json.loads(MODULE.REPORT.read_text(encoding="utf-8"))
    assert report["physical_records_obtained"] == []
    assert report["analysis"]["uses_synthetic_records"] is False
    assert report["analysis"]["physical_effect_estimated"] is False
