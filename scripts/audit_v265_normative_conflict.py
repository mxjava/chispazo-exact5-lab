#!/usr/bin/env python3
"""Deterministic public-document crosswalk for the V265 physical evidence line."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAP = ROOT / "docs/evidence/V265_NORMATIVE_CONFLICT_RECONCILIATION_20261128.md"
V265 = ROOT / "src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"

ANCHORS = {
    "current_sgvo_listed": "SGVO-PRO-05, revisión 39, es la norma sustantiva vigente",
    "manual_support_project_only": "Manual de Apoyo SGVO-MAN-02 en la página **Proyectos Normativos Históricas**",
    "legacy_sgm_not_current_index": "no aparece en la lista actual de Normas Sustantivas Vigentes",
    "legacy_preclose_2115": "pesaje preferentemente antes del cierre de ventas de 21:15",
    "current_postclose_sequence": "Después del cierre, pesaje de esferas una a una y en orden numérico",
    "annual_calibration": "política 25 exige calibración de las básculas",
    "video_scope": "Grabación desde pesaje hasta sorteo",
    "cs11_postdraw": "CS-11",
    "no_authentic_records": "No se obtuvo calendario, marca/modelo/serie de báscula usada en Chispazo",
    "segob_art9_sequence": "Su artículo 9 describe 28 esferas numeradas, cierre de ventas",
    "segob_art15_acta": "El artículo 15 del Reglamento establece que el Acta debe recoger antecedentes, resultados e incidentes",
    "segob_art8_official_results": "los resultados oficiales son los asentados en esa Acta",
    "cs11_is_not_acta": "el formato CS-11 “Números Ganadores de los Sorteos” es un anexo/registro de resultados dentro del expediente, no sustituye al Acta",
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
    text = SOURCE_MAP.read_text(encoding="utf-8")
    anchors = {key: phrase in text for key, phrase in ANCHORS.items()}

    source = V265.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(V265))
    main = _function(tree, "main")
    guard = _return_dict(_function(tree, "physical_evidence_guard"))
    validator = _function(tree, "validate_preclose_metadata")
    required = ast.literal_eval(_assignment(main, "req_m"))
    validator_text = ast.get_source_segment(source, validator) or ""
    provenance_fields = (
        "source_document", "source_url", "source_sha256", "signature_verified",
        "custody", "rfid", "sphere_weight", "extraction_order", "per_extraction_timestamp",
    )
    provenance_checks = {name: name in validator_text for name in provenance_fields}

    v265 = {
        "required_metadata_fields": required,
        "machine_id_label_consumed": "machine_id" in required,
        "sphere_set_id_label_consumed": "sphere_set_id" in required,
        "preclose_timestamp_declared_required": "metadata_known_time_local" in required and "close_time_local" in required,
        "source_provenance_required": guard["source_provenance_required"],
        "validator_checks_source_provenance": any(provenance_checks.values()),
        "provenance_fields_checked": provenance_checks,
        "per_sphere_weights_consumed": guard["per_sphere_weights_consumed"],
        "per_sphere_rfid_mapping_consumed": guard["per_sphere_rfid_mapping_consumed"],
        "extraction_order_consumed": guard["extraction_order_consumed"],
        "per_extraction_timestamps_consumed": guard["per_extraction_timestamps_consumed"],
        "physical_bias_evidence": guard["physical_bias_evidence"],
        "actionable_for_betting": guard["actionable_for_betting"],
        "anytime_evalue_gate_implemented": guard["anytime_evalue_gate_implemented"],
    }

    return {
        "audit_id": "V265_NORMATIVE_CONFLICT_RECONCILIATION_20261128",
        "classification": "DOCUMENTED_MECHANISM_ONLY",
        "source_map_checks": anchors,
        "all_source_map_checks_pass": all(anchors.values()),
        "normative_status": {
            "sgvo_pro_05_revision": 39,
            "sgvo_pro_05_current_normateca_entry": True,
            "sgvo_pro_05_last_update": "2026-03-20",
            "sgm_pro_06_current_normateca_entry": False,
            "sgm_pro_06_public_copy_accessible": True,
            "sgm_pro_06_revision": 22,
            "sgm_pro_06_last_change": "2017-06",
            "sgvo_man_02_in_project_history": True,
            "sgvo_man_02_current_normateca_entry": False,
            "sgvo_man_02_pdf_obtained": False,
            "cs02_instructive_approved_current_copy_obtained": False,
        },
        "chronology": {
            "cs02_and_case_confirmation_before_close": True,
            "sical_closed_before_weighing_under_current_sgvo_pro_05": True,
            "weighing_after_close": True,
            "legacy_sgm_pro_06_says_preferably_before_2115": True,
            "current_schedule_classic_2100": True,
            "legacy_timing_used_for_current_model": False,
        },
        "segob_legal_basis": {
            "chispazo_regulation_last_reform": "2012-03-07",
            "article_9_close_then_signed_participation_file_pre_draw": True,
            "article_9_28_spheres_and_five_extractions": True,
            "article_15_acta_contains_background_results_incidents": True,
            "article_8_official_results_are_acta_only": True,
            "terminal_web_and_mask_are_informational": True,
            "cs11_is_acta": False,
        },
        "calibration": {
            "annual_requirement_in_current_sgvo_policy_25": True,
            "actual_calendar_obtained": False,
            "asset_specific_certificate_obtained": False,
            "calibration_measurements_consumed_by_v265": False,
        },
        "v265_evaluator": v265,
        "analysis": {
            "type": "PUBLIC_DOCUMENT_STATIC_CROSSWALK_AND_AST_CONTRACT_AUDIT",
            "uses_authentic_draw_level_physical_records": False,
            "uses_draw_outcomes": False,
            "uses_synthetic_records": False,
            "statistical_tests_run": [],
            "oos_gate_passed": False,
            "multiplicity_gate_passed": False,
            "anytime_evalue_gate_passed": False,
        },
        "blockers": [
            "approved current SGVO-MAN-02 and CS-02 technical instructive",
            "draw-level signed CS-02 and source timestamps",
            "individual sphere weights and scale identity",
            "asset-specific calibration certificates and maintenance logs",
            "RFID tag-to-asset/sphere/number mapping and timestamped reads",
            "load/extraction order and per-extraction timestamps",
            "signed CS-11 and four-copy delivery receipts",
            "original continuous video, hashes and chain of custody",
            "CS-09, CS-12 and CS-18 original records",
            "original Acta and complete attachments for each contest",
        ],
        "preservation": {
            "canonical_history_touched": False,
            "v294_touched": False,
            "main_written": False,
            "merge_or_promotion": False,
        },
        "prospective_status": "BLOCKED_PENDING_AUTHENTICATED_PRE_CLOSE_PHYSICAL_RECORDS",
        "all_checks_pass": all(anchors.values()) and (
            v265["source_provenance_required"] is False
            and v265["validator_checks_source_provenance"] is False
            and v265["per_sphere_weights_consumed"] is False
            and v265["per_sphere_rfid_mapping_consumed"] is False
            and v265["extraction_order_consumed"] is False
            and v265["per_extraction_timestamps_consumed"] is False
            and v265["physical_bias_evidence"] is False
            and v265["actionable_for_betting"] is False
            and v265["anytime_evalue_gate_implemented"] is False
        ),
    }


if __name__ == "__main__":
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["all_checks_pass"] else 1)
