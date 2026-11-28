#!/usr/bin/env python3
"""Reproducible static audit of V265's physical-evidence claim boundary.

This script reads only the checked-in V265 evaluator and its FULL metadata
template. It does not read, synthesize, or score draw outcomes.
"""
from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = ROOT / "src" / "v265" / "CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py"
TEMPLATE = ROOT / "data" / "physical-metadata" / "V265_PHYSICAL_METADATA_TEMPLATE_FULL.csv"


def _required_metadata_columns(source: str) -> list[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == "req_m" for target in node.targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError("req_m must remain a literal list of column names")
            return value
    raise ValueError("V265 required metadata columns (req_m) not found")


def _guard() -> dict:
    spec = importlib.util.spec_from_file_location("v265_audited_evaluator", EVALUATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load V265 evaluator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.physical_evidence_guard()


def build_report() -> dict:
    source = EVALUATOR.read_text(encoding="utf-8")
    with TEMPLATE.open("r", encoding="utf-8", newline="") as handle:
        template_columns = next(csv.reader(handle))

    required = _required_metadata_columns(source)
    weights = [name for name in template_columns if name.startswith("sphere_weight_") and name.endswith("_g")]
    provenance = [name for name in ("source_document", "source_url", "source_sha256") if name in template_columns]
    rfid_columns = [name for name in template_columns if "rfid" in name.lower()]
    guard = _guard()

    return {
        "audit_id": "V265_EVIDENCE_CONTRACT_20261122",
        "audit_type": "static_code_and_schema_audit",
        "uses_draw_outcomes": False,
        "uses_synthetic_draws": False,
        "required_metadata_columns": required,
        "template_column_count": len(template_columns),
        "template_per_sphere_weight_columns": weights,
        "template_rfid_columns": rfid_columns,
        "template_source_provenance_columns": provenance,
        "evaluator_consumes": {
            "machine_id": "machine_id" in source and "machine_id" in required,
            "sphere_set_id": "sphere_set_id" in source and "sphere_set_id" in required,
            "per_sphere_weights": any(name in required for name in weights) and "sphere_weight_" in source,
            "per_sphere_rfid_mapping": any("rfid" in name.lower() for name in required) and "rfid_tag_id" in source,
            "extraction_order": "extraction_order" in required and "extraction_order" in source,
            "per_extraction_timestamps": "extraction_timestamp" in required and "extraction_timestamp" in source,
            "source_provenance": all(name in required for name in provenance),
        },
        "preclose_timestamp_guard_present": "validate_preclose_metadata(m)" in source,
        "one_sided_t_test_present": "one_sided_ttest_greater" in source,
        "holm_adjustment_present": "holm_adjust" in source,
        "p_family_optional": "ap.add_argument('--p-family', help=" in source,
        "anytime_evalue_gate_implemented": guard["anytime_evalue_gate_implemented"],
        "evidence_class": guard["evidence_class"],
        "physical_bias_evidence": guard["physical_bias_evidence"],
        "actionable_for_betting": guard["actionable_for_betting"],
        "guard": guard,
        "interpretation": (
            "V265 is a machine/sphere-set association screen. It does not consume "
            "authenticated per-sphere measurements, RFID-to-ball identity, extraction "
            "order/timestamps, or source provenance; it has no anytime e-value gate. "
            "It cannot establish physical bias or authorize a prospective action."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
