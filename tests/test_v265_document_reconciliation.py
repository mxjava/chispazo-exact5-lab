from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit_v265_document_reconciliation", ROOT / "scripts" / "audit_v265_document_reconciliation.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

def test_document_reconciliation_is_consistent_and_non_predictive():
    result = MODULE.validate()
    assert result["valid"] is True
    assert result["matrix_rows"] == 12
    assert result["classification"] == "MECHANISM_DOCUMENTATION_ONLY"
