from __future__ import annotations
import ast
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_v265_research_edge_semantics.py"
SPEC = importlib.util.spec_from_file_location("audit_v265_research_edge_semantics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_v265_research_edge_is_not_physical_bias_or_actionability():
    report = MODULE.build_report()
    assert report["classification"] == "ASSOCIATION_SCREEN_ONLY"
    assert report["research_edge_is_physical_bias_evidence"] is False
    assert report["actionable_for_betting"] is False
    assert report["anytime_evalue_gate_implemented"] is False


def test_v265_preclose_fields_do_not_authenticate_source_provenance():
    report = MODULE.build_report()
    assert report["required_metadata_fields"] == [
        "CONCURSO", "sphere_set_id", "machine_id", "available_before_close",
        "close_time_local", "metadata_known_time_local",
    ]
    assert report["preclose_validator_checks_source_provenance"] is False
    assert report["guard"]["source_provenance_required"] is False
    assert report["guard"]["per_sphere_weights_consumed"] is False
    assert report["guard"]["per_sphere_rfid_mapping_consumed"] is False
    assert report["guard"]["extraction_order_consumed"] is False
    assert report["guard"]["per_extraction_timestamps_consumed"] is False


def test_research_edge_expression_is_only_an_association_screen():
    report = MODULE.build_report()
    expected = MODULE._stable_ast_dump(
        ast.parse(
            "bool(sample_ok and mean > 0 and adjusted_p is not None and adjusted_p < 0.05)",
            mode="eval",
        ).body
    )
    assert report["research_edge_ast"] == expected
    assert "not authenticated" in report["interpretation"]


def test_checked_in_audit_matches_reproducible_source_audit():
    report = MODULE.build_report()
    checked_in = ROOT / "reports" / "V265_RESEARCH_EDGE_SEMANTICS_AUDIT_20261126.json"
    assert json.loads(checked_in.read_text(encoding="utf-8")) == report
