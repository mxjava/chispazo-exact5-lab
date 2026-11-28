#!/usr/bin/env python3
"""Deterministic static crosswalk for V265 Acta/annex/custody chronology."""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/evidence/V265_ACTA_CUSTODY_CHAIN_20261128.md"
V265 = ROOT / "src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"
ANCHORS = {
    "acta_official_hierarchy": "El artículo 15 del Reglamento exige Acta con antecedentes, resultados e incidentes",
    "weekly_annex_archive": "entregarlos semanalmente (lunes a domingo)",
    "sical_discrepancy_route": "el Acta use la pantalla del sistema administrativo de Selección de Ganadores y agregue la pantalla SICAL",
    "incident_definition": "cualquier incidencia de una etapa que salga del procedimiento y afecte resultados",
    "deferred_acta_signature": "máximo cinco días hábiles, sólo si no fue posible imprimirla y los resultados no se comprometen",
    "acta_scan_to_oic": "escanear el Acta firmada y enviarla al OIC",
    "optional_cs18": "CS-18 es opcional",
    "cs12_access": "registrar participantes mediante CS-12",
    "continuous_video_scope": "grabación desde el pesaje hasta el sorteo",
    "room_camera_capture": "cámaras de sala captan y graban los números expresados por el presentador",
    "no_master_video": "No se obtuvo máster, metadatos, hash ni cadena de custodia por concurso",
    "no_preclose_prediction": "No; post-cierre/pre-sorteo",
}


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function {name}")


def _literal_return_dict(fn: ast.FunctionDef) -> dict:
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{fn.name} has no literal dict return")


def _required_metadata(source: str) -> list[str]:
    tree = ast.parse(source, filename=str(V265))
    main = _find_function(tree, "main")
    for node in ast.walk(main):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "req_m" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("V265 required metadata list not found")


def build_report() -> dict:
    doc = DOC.read_text(encoding="utf-8")
    anchors = {key: phrase in doc for key, phrase in ANCHORS.items()}
    source = V265.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(V265))
    guard = _literal_return_dict(_find_function(tree, "physical_evidence_guard"))
    fields = _required_metadata(source)
    return {
        "audit_id": "V265_ACTA_CUSTODY_CHAIN_20261128",
        "classification": "DOCUMENTED_MECHANISM_ONLY",
        "all_document_anchors_pass": all(anchors.values()),
        "document_anchors": anchors,
        "acta_chain": {
            "acta_is_official_result_record": True,
            "cs11_is_separate_record_not_acta": True,
            "weekly_annex_dvd_delivery": True,
            "sical_discrepancy_requires_both_screens_and_provider_clarification": True,
            "incidents_recorded_in_acta": True,
            "acta_signature_can_be_deferred_max_five_business_days_under_exception": True,
            "signed_acta_scanned_to_oic": True,
            "cs18_is_optional_risk_communication": True,
            "cs12_is_access_record": True,
            "continuous_recording_from_weighing_to_draw": True,
            "room_cameras_record_exhibitor_numbers": True,
            "original_video_master_obtained": False,
            "weekly_dvd_or_delivery_office_obtained": False,
            "draw_level_acta_and_annexes_obtained": False,
        },
        "v265_evaluator": {
            "required_metadata_fields": fields,
            "source_provenance_required": guard["source_provenance_required"],
            "physical_bias_evidence": guard["physical_bias_evidence"],
            "actionable_for_betting": guard["actionable_for_betting"],
            "per_sphere_weights_consumed": guard["per_sphere_weights_consumed"],
            "per_sphere_rfid_mapping_consumed": guard["per_sphere_rfid_mapping_consumed"],
            "extraction_order_consumed": guard["extraction_order_consumed"],
            "per_extraction_timestamps_consumed": guard["per_extraction_timestamps_consumed"],
            "anytime_evalue_gate_implemented": guard["anytime_evalue_gate_implemented"],
        },
        "analysis": {
            "type": "PUBLIC_DOCUMENT_STATIC_CROSSWALK_AND_AST_CONTRACT_AUDIT",
            "uses_draw_outcomes": False,
            "uses_authentic_draw_level_physical_records": False,
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
    }


if __name__ == "__main__":
    print(json.dumps(build_report(), ensure_ascii=False, indent=2, sort_keys=True))
