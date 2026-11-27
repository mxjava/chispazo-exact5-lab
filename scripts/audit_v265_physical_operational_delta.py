#!/usr/bin/env python3
"""Deterministic audit of the public V265 physical/operational evidence map.

The script checks the committed transcription and reads the current V265
evaluator source. It does not download official PDFs, inspect draw records,
read draw outcomes, or run statistical tests.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAP = ROOT / "docs/evidence/V265_PUBLIC_PHYSICAL_OPERATIONAL_MAP_20261127.md"
V265 = ROOT / "src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"

REQUIRED_ANCHORS = {
    "electronic_scope": "Chispazo Clásico se clasifica como sorteo electrónico",
    "cs02_preclose": "CS-02: inspección del equipo antes del cierre",
    "weighing_postclose": "Tira de Pesaje: medición individual después del cierre SICAL verificado",
    "cs11_distribution": "CS-11: cuatro ejemplares; tercera copia al operador del área de Control de Datos",
    "rfid_inventory": "El Informe 2018–2024 reporta 14 máquinas con RFID",
    "rfid_count_discrepancy": "El mismo informe declara 60 juegos de esferas para siete productos",
    "maintenance_058": "El contrato 058-2024 incluye mantenimiento de 21 máquinas y Chispazo",
    "electrical_invitation_222": "La invitación IA-06-HJY-006HJY001-N-222-2026 cubre equipos eléctricos de inmuebles",
    "no_draw_records": "No se obtuvieron originales por concurso de CS-02",
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
    map_text = SOURCE_MAP.read_text(encoding="utf-8")
    source_checks = {key: phrase in map_text for key, phrase in REQUIRED_ANCHORS.items()}

    source = V265.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(V265))
    main = _function(tree, "main")
    guard = _return_dict(_function(tree, "physical_evidence_guard"))
    validator = _function(tree, "validate_preclose_metadata")
    required_fields = ast.literal_eval(_assignment(main, "req_m"))
    validator_text = ast.get_source_segment(source, validator) or ""
    provenance_terms = (
        "source_document", "source_url", "source_sha256", "signature_verified",
        "custody", "rfid", "sphere_weight", "extraction_order", "per_extraction_timestamp",
    )
    provenance_checks = {term: term in validator_text for term in provenance_terms}

    v265 = {
        "required_metadata_fields": required_fields,
        "machine_id_label_consumed": "machine_id" in required_fields,
        "sphere_set_id_label_consumed": "sphere_set_id" in required_fields,
        "per_sphere_weights_consumed": guard["per_sphere_weights_consumed"],
        "per_sphere_rfid_mapping_consumed": guard["per_sphere_rfid_mapping_consumed"],
        "extraction_order_consumed": guard["extraction_order_consumed"],
        "per_extraction_timestamps_consumed": guard["per_extraction_timestamps_consumed"],
        "source_provenance_required": guard["source_provenance_required"],
        "preclose_validator_checks_source_provenance": any(provenance_checks.values()),
        "preclose_validator_provenance_terms": provenance_checks,
        "physical_bias_evidence": guard["physical_bias_evidence"],
        "actionable_for_betting": guard["actionable_for_betting"],
        "anytime_evalue_gate_implemented": guard["anytime_evalue_gate_implemented"],
    }

    result = {
        "audit_id": "V265_PHYSICAL_OPERATIONAL_DELTA_20261127",
        "classification": "DOCUMENTED_MECHANISM_ONLY",
        "source_map_checks": source_checks,
        "all_source_map_checks_pass": all(source_checks.values()),
        "v265_evaluator": v265,
        "evidence": {
            "rfid_reported_historically": True,
            "rfid_per_sphere_mapping_obtained": False,
            "reported_set_count_internally_inconsistent": True,
            "contract_058_2024_includes_chispazo": True,
            "contract_058_2024_per_asset_service_records_obtained": False,
            "invitation_222_2026_scope_is_electrical_infrastructure": True,
            "invitation_222_2026_award_or_service_reports_obtained": False,
            "current_scale_calibration_certificate_obtained": False,
            "current_public_calibration_interval_verified": False,
            "cs11_prescribed_distribution_complete": True,
            "cs11_per_contest_delivery_receipts_obtained": False,
            "draw_level_original_records_obtained": False,
            "official_pdf_binary_sha256_captured": False,
        },
        "analysis": {
            "type": "PUBLIC_DOCUMENT_STATIC_CROSSWALK",
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
        "prospective_status": "BLOCKED_PENDING_AUTHENTICATED_PRE_CLOSE_PHYSICAL_RECORDS",
        "all_checks_pass": all(source_checks.values()) and (
            v265["physical_bias_evidence"] is False
            and v265["actionable_for_betting"] is False
            and v265["anytime_evalue_gate_implemented"] is False
            and v265["per_sphere_weights_consumed"] is False
            and v265["per_sphere_rfid_mapping_consumed"] is False
            and v265["extraction_order_consumed"] is False
            and v265["per_extraction_timestamps_consumed"] is False
        ),
    }
    return result


if __name__ == "__main__":
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["all_checks_pass"] else 1)
