"""Reproducible audit of a frozen official-source excerpt snapshot.

This module checks documentary cross-references and source-status boundaries only.
It does not parse or authenticate the source PDFs, ingest draw-specific records,
measure physical bias, or estimate predictive performance.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def audit_source_snapshot(snapshot: Mapping[str, Any], raw_bytes: bytes | None = None) -> dict[str, Any]:
    sources = snapshot["sources"]
    excerpts = snapshot["authoritative_excerpts"]
    manual = snapshot["reserved_manual_leads_only"]
    regulation = snapshot["regulation_sequence"]
    report = sources["management_report"]
    procurement = sources["procurement_2026_222"]

    policy_6 = excerpts["policy_6_weight_spec"]
    policy_8 = excerpts["policy_8_electronic_signature"]
    activity_5_2 = excerpts["activity_5_2"]
    quality_weighing = excerpts["quality_plan_weighing"]
    activity_role = excerpts["activity_5_4_signatures"]["role_label"]
    glossary_role = excerpts["glossary_tira_signatory_role"]["role_label"]
    cs11 = excerpts["quality_plan_cs11_fields"]

    policy_8_is_signature = "Firma Electrónica" in policy_8["text"]
    policy_6_is_weight = "Smartballs" in policy_6["text"] and "Ping Pong" in policy_6["text"]
    cross_reference_mismatch = (
        policy_6_is_weight
        and policy_8_is_signature
        and activity_5_2["policy_reference"] == 8
        and quality_weighing["policy_reference"] == 8
        and quality_weighing["weight_limits_repeat_policy_6"] is True
    )
    role_mismatch = activity_role != glossary_role
    cs11_template_missing = cs11["cs11_blank_template_embedded_in_pro05"] is False
    cs11_time_unspecified = cs11["explicit_time_field_listed"] is False
    manual_is_reserved_project = (
        sources["sgvo_man_02"]["normateca_bucket"] == "PROYECTOS_NORMATIVOS"
        and sources["sgvo_man_02"]["cover_type"] == "RESERVADO"
        and sources["sgvo_man_02"]["use_as_current_operational_authority"] is False
    )
    maintenance_status_unknown = (
        report["maintenance_contract_058_2024"]["status_by_2024_06"] == "CONCLUDED"
        and report["maintenance_contract_058_2024"]["current_status_after_2024_06"] == "UNKNOWN"
    )
    rfid_trace_missing = report["rfid_declared_for_machines_and_spheres"] and all(
        phrase in snapshot["evidence_gaps"]
        for phrase in (
            "No RFID tag-to-sphere-number mapping or raw reader event log obtained.",
            "No machine serial-to-contest assignment obtained.",
        )
    )
    traditional_scope_excluded = sources["sgvo_pro_34"]["scope"] == "EXCLUSIVELY_TRADITIONAL_WOODEN_BALLS_AND_ABACUS"
    regulation_order_conflict = bool(regulation["article_9"]["order_conflict_with_pro05"])
    signature_is_postclose_pre_draw = (
        excerpts["activity_7_electronic_signature"]["sequence"]
        == "AFTER_SALES_CLOSE_AND_WEIGHING_BEFORE_DRAW"
    )
    electrical_procurement_excluded = procurement["draw_machine_maintenance_evidence"] is False

    findings = {
        "POLICY_5_2_AND_QUALITY_PLAN_CROSS_REFERENCE_MISMATCH": cross_reference_mismatch,
        "TIRA_SIGNATORY_ROLE_LABEL_MISMATCH": role_mismatch,
        "CS11_TEMPLATE_NOT_EMBEDDED_IN_PUBLIC_PRO05": cs11_template_missing,
        "CS11_TIME_FIELD_NOT_SPECIFIED_IN_PUBLIC_PLAN": cs11_time_unspecified,
        "SGVO_MAN_02_IS_RESERVED_PROJECT_LEAD_ONLY": manual_is_reserved_project,
        "REGULATION_ARTICLE_9_VS_PRO05_SEQUENCE_REQUIRES_CLARIFICATION": regulation_order_conflict,
        "ELECTRONIC_SIGNATURE_IS_POST_CLOSE_PRE_DRAW": signature_is_postclose_pre_draw,
        "CURRENT_MACHINE_MAINTENANCE_STATUS_UNKNOWN": maintenance_status_unknown,
        "RFID_EXISTS_BUT_DRAW_LEVEL_TRACE_IS_MISSING": rfid_trace_missing,
        "PRO34_TRADITIONAL_SCOPE_EXCLUDED_FROM_CHISPAZO": traditional_scope_excluded,
        "2026_222_ELECTRICAL_BUILDING_MAINTENANCE_EXCLUDED": electrical_procurement_excluded,
    }
    if not all(type(value) is bool for value in findings.values()):
        raise ValueError("all audit findings must be exact booleans")

    result = {
        "snapshot_id": snapshot["snapshot_id"],
        "status": "DOCUMENTARY_SOURCE_AUDIT_COMPLETE",
        "classification": "MECHANISM_EVIDENCE_ONLY",
        "findings": findings,
        "finding_codes": sorted(code for code, present in findings.items() if present),
        "predictive_advantage_claim": False,
        "physical_bias_claim": False,
        "draw_specific_physical_data_used": False,
        "frequency_pair_triple_transition_analysis_run": False,
        "manual_draft_fields_authoritative": False,
        "notes": [
            "The audit validates a frozen transcript of official source excerpts; it does not authenticate the original PDF bytes.",
            "The CS-11 time-field result is scoped to the field list published in the SGVO-PRO-05 quality plan; the blank CS-11 template was not embedded in the procedure PDF.",
            "The SGVO-MAN-02 content is retained as a reserved project lead only and is not treated as current approved operating authority.",
            "No draw-specific physical measurements, RFID events, asset assignments, maintenance work orders, or original audiovisual files were obtained.",
        ],
    }
    if raw_bytes is not None:
        result["source_snapshot_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    return result


def audit_snapshot_file(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    raw = source_path.read_bytes()
    snapshot = json.loads(raw.decode("utf-8"))
    return audit_source_snapshot(snapshot, raw_bytes=raw)
