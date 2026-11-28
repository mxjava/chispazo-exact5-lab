#!/usr/bin/env python3
"""Static audit of SGVO-PRO-05 estuche timing versus the V265 metadata contract."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/evidence/V265_SPHERE_SET_SUBSTITUTION_TIMING_20261128.md"
V265 = ROOT / "src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"
ANCHORS = {
    "manual_project_not_current": "Ese manual aparece en **Proyectos Normativos Históricas**",
    "traditional_motor_procedure_excluded": "SGVO-PRO-28 tiene un nombre que podría inducir a confusión",
    "cs02_preclose": "CS-02, antes del cierre",
    "planned_set_preclose": "Estuche inicial, antes del cierre",
    "sical_close_before_weighing": "Pesaje, después del cierre",
    "postclose_set_substitution": "Sustitución posterior al cierre",
    "cs11_retrospective": "CS-11 retrospectivo",
    "planned_and_actual_are_distinct": "planned_sphere_set_id",
    "actual_set_is_distinct": "actual_sphere_set_id",
    "no_draw_level_records": "No se obtuvo ningún CS-02, Tira de Pesaje ni CS-11 original",
    "no_synthetic_data": "No se usaron registros sintéticos",
}

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
    doc = DOC.read_text(encoding="utf-8")
    anchors = {key: phrase in doc for key, phrase in ANCHORS.items()}
    source = V265.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(V265))
    main = _function(tree, "main")
    guard = _return_dict(_function(tree, "physical_evidence_guard"))
    validator = _function(tree, "validate_preclose_metadata")
    required = ast.literal_eval(_assignment(main, "req_m"))
    validator_text = ast.get_source_segment(source, validator) or ""
    has_substitution_fields = any(
        field in required for field in (
            "planned_sphere_set_id", "actual_sphere_set_id", "sphere_set_replaced",
            "sphere_set_change_time_local", "sphere_set_change_reason",
        )
    )
    return {
        "audit_id": "V265_SPHERE_SET_SUBSTITUTION_TIMING_20261128",
        "classification": "DOCUMENTED_MECHANISM_ONLY_EXPOSURE_SCHEMA_AMBIGUITY",
        "anchors": anchors,
        "all_anchors_pass": all(anchors.values()),
        "manual_status": {
            "listed_as_current_vigente": False,
            "listed_as_project": True,
            "project_start": "23/02/2026",
            "project_end": "04/03/2026",
            "pdf_content_retrieved": False,
            "used_as_binding_instruction": False,
        },
        "official_sequence": {
            "cs02_before_close": True,
            "initial_set_confirmed_before_close": True,
            "sical_close_precedes_weighing": True,
            "weighs_each_sphere_in_numeric_order": True,
            "failed_weight_can_replace_set_after_close": True,
            "cs11_records_selected_set_and_results_after_draw": True,
            "actual_set_may_differ_from_preclose_plan": True,
        },
        "v265_contract": {
            "required_metadata_fields": required,
            "single_sphere_set_id_field": required.count("sphere_set_id") == 1,
            "planned_vs_actual_fields_present": has_substitution_fields,
            "preclose_timestamp_comparison_present": "known >= close" in validator_text,
            "source_provenance_required": guard["source_provenance_required"],
            "per_sphere_weights_consumed": guard["per_sphere_weights_consumed"],
            "per_sphere_rfid_mapping_consumed": guard["per_sphere_rfid_mapping_consumed"],
            "extraction_order_consumed": guard["extraction_order_consumed"],
            "per_extraction_timestamps_consumed": guard["per_extraction_timestamps_consumed"],
            "physical_bias_evidence": guard["physical_bias_evidence"],
            "actionable_for_betting": guard["actionable_for_betting"],
            "anytime_evalue_gate_implemented": guard["anytime_evalue_gate_implemented"],
        },
        "interpretation": {
            "risk": "PLANNED_VS_ACTUAL_SPHERE_SET_NOT_DISTINGUISHED",
            "if_id_source_is_cs11": "POST_DRAW_NOT_PRE_CLOSE",
            "if_id_source_is_activity_3_1": "PRE_CLOSE_PLAN_ONLY_NOT_FINAL_AFTER_SUBSTITUTION",
            "same_contest_betting_uses_postclose_actual_set": False,
        },
        "analysis": {
            "type": "PUBLIC_PROCEDURE_STATIC_CROSSWALK_AND_V265_AST_AUDIT",
            "uses_draw_outcomes": False,
            "uses_synthetic_records": False,
            "statistical_tests_run": [],
            "oos_gate_passed": False,
            "multiplicity_gate_passed": False,
            "anytime_evalue_gate_passed": False,
        },
        "preservation": {
            "canonical_history_touched": False,
            "v294_touched": False,
            "main_written": False,
            "merge_or_promotion": False,
        },
        "all_checks_pass": all(anchors.values()) and required.count("sphere_set_id") == 1
            and not has_substitution_fields
            and guard["physical_bias_evidence"] is False
            and guard["actionable_for_betting"] is False
            and guard["anytime_evalue_gate_implemented"] is False,
    }

if __name__ == "__main__":
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["all_checks_pass"] else 1)
