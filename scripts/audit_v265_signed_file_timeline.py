#!/usr/bin/env python3
"""Deterministic semantic audit of the SGVO-PRO-05 rev.39 document map."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MAP = ROOT / "docs/evidence/SGVO_PRO05_REV39_TIMELINE_EXTRACT_20261126.md"

REQUIRED = {
    "official_revision": "SGVO-PRO-05 revision 39",
    "sical_closed_before_annex_signature": "Verify Sumario status Closed; receive participation/cancellation files and electronic signatures",
    "signature_deposited_pre_draw": "deposited by SEGOB Inspector in a safe before the draw",
    "signature_not_preclose": "Do not call it pre-close",
    "weighing_after_close": "then weighing starts",
    "cs11_copy_count": "four copies are printed",
    "cs11_third_copy_recipient": "Control Data operator (who enters winning numbers",
    "mjf_after_2100": "After 21:00",
    "mjf_exact_draw_end_unknown": "does not specify exact relation to the physical draw's end",
    "no_original_draw_records": "not an original signed record or proof of a particular contest's execution",
}


def build_report() -> dict:
    text = SOURCE_MAP.read_text(encoding="utf-8")
    checks = {key: phrase in text for key, phrase in REQUIRED.items()}
    return {
        "audit_id": "V265_SIGNED_FILE_TIMELINE_20261126",
        "source_document": "SGVO-PRO-05 revision 39, DN-07 v09",
        "source_url": "https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf",
        "classification": "DOCUMENTED_MECHANISM_ONLY",
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "key_findings": {
            "participation_signature_stage": "AFTER_SICAL_CLOSE_CHECK_BEFORE_DRAW",
            "participation_signature_is_preclose": False,
            "weighing_stage": "AFTER_VERIFIED_SICAL_CLOSE",
            "cs11_copy_distribution_complete": True,
            "cs11_third_copy_recipient": "CONTROL_DATA_OPERATOR",
            "cs11_actual_delivery_receipts_obtained": False,
            "mjf_archive_stage": "AFTER_21_00_DAILY_CLOSE; EXACT_RELATION_TO_DRAW_END_UNSPECIFIED",
            "physical_bias_evidence": False,
            "predictive_edge_evidence": False,
        },
        "draw_level_original_records_obtained": False,
        "official_pdf_bytes_and_sha256_captured": False,
        "oos_gate_passed": False,
        "multiplicity_gate_passed": False,
        "anytime_evalue_gate_passed": False,
    }


if __name__ == "__main__":
    report = build_report()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if report["all_checks_pass"] else 1)
