#!/usr/bin/env python3
"""Static, deterministic audit of V265 claim semantics.

Reads the checked-in evaluator source only. It does not read draw outcomes,
construct records, run statistical tests, or infer physical bias.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V265 = ROOT / "src" / "v265" / "CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def _return_dict(function: ast.FunctionDef) -> dict:
    for node in ast.walk(function):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{function.name} has no literal dict return")


def _assignment(function: ast.FunctionDef, name: str) -> ast.AST:
    for node in ast.walk(function):
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return node.value
    raise AssertionError(f"{function.name} has no assignment to {name}")


def build_report() -> dict:
    source = V265.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(V265))
    main = _function(tree, "main")
    guard = _return_dict(_function(tree, "physical_evidence_guard"))
    validator = _function(tree, "validate_preclose_metadata")
    required_fields = ast.literal_eval(_assignment(main, "req_m"))
    research_edge_expr = ast.unparse(_assignment(main, "research_edge"))
    validator_text = ast.get_source_segment(source, validator) or ""

    provenance_terms = (
        "source_document", "source_url", "source_sha256",
        "signature_verified", "custody", "rfid", "sphere_weight",
        "extraction_order", "per_extraction_timestamp",
    )
    validator_provenance_checks = {
        term: term in validator_text for term in provenance_terms
    }

    result = {
        "audit_id": "V265_RESEARCH_EDGE_SEMANTICS_AUDIT_20261126",
        "classification": "ASSOCIATION_SCREEN_ONLY",
        "required_metadata_fields": required_fields,
        "research_edge_expression": research_edge_expr,
        "research_edge_is_physical_bias_evidence": guard["physical_bias_evidence"],
        "actionable_for_betting": guard["actionable_for_betting"],
        "anytime_evalue_gate_implemented": guard["anytime_evalue_gate_implemented"],
        "guard": {
            key: guard[key] for key in (
                "evidence_class",
                "physical_bias_evidence",
                "actionable_for_betting",
                "anytime_evalue_gate_implemented",
                "per_sphere_weights_consumed",
                "per_sphere_rfid_mapping_consumed",
                "extraction_order_consumed",
                "per_extraction_timestamps_consumed",
                "source_provenance_required",
            )
        },
        "preclose_validator_checks_source_provenance": any(validator_provenance_checks.values()),
        "preclose_validator_provenance_terms": validator_provenance_checks,
        "interpretation": (
            "The research_edge field is an association-screen flag computed from OOS sample size, "
            "mean log-lift and an optional Holm-adjusted p-value. It is not a physical-bias or "
            "actionable-prediction result. Caller-supplied machine/set labels and timestamps are "
            "not authenticated by this evaluator; the pre-close validator checks chronology only."
        ),
        "uses_draw_outcomes": False,
        "uses_synthetic_records": False,
        "physical_records_obtained": [],
        "statistical_tests_run": [],
        "oos_gate_passed": False,
        "multiplicity_gate_passed": False,
        "anytime_evalue_gate_passed": False,
    }
    return result


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, indent=2, sort_keys=True))
