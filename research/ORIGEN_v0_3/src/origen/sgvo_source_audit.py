"""Audit documentary boundaries in a frozen official-source excerpt snapshot.

This does not parse/authenticate source PDF bytes, ingest draw records, measure
physical bias, or estimate predictive performance.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

def audit_source_snapshot(snapshot: Mapping[str, Any], raw_bytes: bytes | None = None) -> dict[str, Any]:
    src = snapshot["sources"]
    ex = snapshot["authoritative_excerpts"]
    p6, p8 = ex["policy_6_weight_spec"], ex["policy_8_electronic_signature"]
    mismatch = ("Smartballs" in p6["text"] and "Ping Pong" in p6["text"]
                and "electronic signature" in p8["text"].lower()
                and ex["activity_5_2"]["policy_reference"] == 8
                and ex["quality_plan_weighing"]["policy_reference"] == 8
                and ex["quality_plan_weighing"]["weight_limits_repeat_policy_6"] is True)
    role_mismatch = ex["activity_5_4_signatures"]["role_label"] != ex["glossary_tira_signatory_role"]["role_label"]
    cs11_plan_omits_time = ex["quality_plan_cs11_fields"]["explicit_time_field_listed"] is False
    cs11_glossary_has_time = ex["glossary_cs11_fields"]["explicit_time_field_specified"] is True
    manual_reserved = (src["sgvo_man_02"]["normateca_bucket"] == "PROYECTOS_NORMATIVOS"
                       and src["sgvo_man_02"]["cover_type"] == "RESERVADO"
                       and src["sgvo_man_02"]["use_as_current_operational_authority"] is False)
    maintenance_unknown = (src["management_report"]["maintenance_contract_058_2024"]["status_by_2024_06"] == "CONCLUDED"
                           and src["management_report"]["maintenance_contract_058_2024"]["current_status_after_2024_06"] == "UNKNOWN")
    rfid_gap = (src["management_report"]["rfid_declared_for_machines_and_spheres"] is True
                and any("RFID tag-to-sphere-number" in x for x in snapshot["evidence_gaps"])
                and any("machine serial-to-contest" in x for x in snapshot["evidence_gaps"]))
    findings = {
        "POLICY_5_2_AND_QUALITY_PLAN_CROSS_REFERENCE_MISMATCH": mismatch,
        "TIRA_SIGNATORY_ROLE_LABEL_MISMATCH": role_mismatch,
        "CS11_TEMPLATE_NOT_OBTAINED": ex["glossary_cs11_fields"]["blank_template_embedded"] is False,
        "CS11_QUALITY_PLAN_CHECKLIST_OMITS_DRAW_HOUR": cs11_plan_omits_time,
        "CS11_GLOSSARY_SPECIFIES_DRAW_HOUR": cs11_glossary_has_time,
        "SGVO_MAN_02_IS_RESERVED_PROJECT_LEAD_ONLY": manual_reserved,
        "REGULATION_ARTICLE_9_VS_PRO05_SEQUENCE_REQUIRES_CLARIFICATION": snapshot["regulation_sequence"]["article_9"]["order_conflict_with_pro05"] is True,
        "ELECTRONIC_SIGNATURE_IS_POST_CLOSE_PRE_DRAW": ex["activity_7_electronic_signature"]["sequence"] == "AFTER_SALES_CLOSE_AND_WEIGHING_BEFORE_DRAW",
        "CURRENT_MACHINE_MAINTENANCE_STATUS_UNKNOWN": maintenance_unknown,
        "RFID_EXISTS_BUT_DRAW_LEVEL_TRACE_IS_MISSING": rfid_gap,
        "PRO34_TRADITIONAL_SCOPE_EXCLUDED_FROM_CHISPAZO": src["sgvo_pro_34"]["scope"] == "EXCLUSIVELY_TRADITIONAL_WOODEN_BALLS_AND_ABACUS",
        "2026_222_BUILDING_ELECTRICAL_TENDER_EXCLUDED": src["procurement_2026_222"]["draw_machine_maintenance_evidence"] is False,
    }
    if not all(type(v) is bool for v in findings.values()):
        raise ValueError("all audit findings must be exact booleans")
    result = {
        "snapshot_id": snapshot["snapshot_id"],
        "status": "DOCUMENTARY_SOURCE_AUDIT_COMPLETE",
        "classification": "MECHANISM_EVIDENCE_ONLY",
        "findings": findings,
        "finding_codes": sorted(k for k, v in findings.items() if v),
        "physical_bias_claim": False,
        "predictive_advantage_claim": False,
        "draw_specific_physical_data_used": False,
        "frequency_pair_triple_transition_analysis_run": False,
        "reserved_manual_fields_authoritative": False,
        "notes": [
            "Audit is over a frozen transcript of official excerpts, not source PDF binary authentication.",
            "CS-11 glossary specifies the draw hour; the Quality Plan checklist omits it; the blank form and completed records were not obtained.",
            "SGVO-MAN-02 is a reserved project copy and is not treated as current approved authority.",
            "No draw-specific weights, RFID events, asset assignments, maintenance work orders or audiovisual masters were obtained.",
        ],
    }
    if raw_bytes is not None:
        result["source_snapshot_sha256"] = hashlib.sha256(raw_bytes).hexdigest()
    return result

def audit_snapshot_file(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return audit_source_snapshot(json.loads(raw.decode("utf-8")), raw_bytes=raw)
