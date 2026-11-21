#!/usr/bin/env python3
"""Reproducible audit of the public Chispazo Clásico physical-evidence timeline.

This audits published procedure chronology and public-data availability only.
It does not create draw-level records or estimate a mechanical bias.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

VALID_STAGES = {
    "pre_close", "close", "post_close_pre_draw", "draw", "post_draw"
}


def audit(document: dict) -> dict:
    events = document["events"]
    if not events:
        raise ValueError("timeline must contain events")

    raw_orders = [event["order"] for event in events]
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in raw_orders):
        raise ValueError("event order values must be positive integers")
    orders = raw_orders
    if len(set(orders)) != len(orders):
        raise ValueError("event order values must be unique")
    if orders != sorted(orders):
        raise ValueError("events must be stored in chronological procedure order")

    for event in events:
        if event["stage"] not in VALID_STAGES:
            raise ValueError(f"unknown stage: {event['stage']}")
        if not event.get("activity") or not event.get("event"):
            raise ValueError("every event needs an activity and event label")

    close = [e for e in events if e["stage"] == "close"]
    if len(close) != 1:
        raise ValueError("exactly one sales-close event is required")
    close_order = int(close[0]["order"])

    def event_by_activity(prefix: str) -> dict:
        matches = [e for e in events if str(e["activity"]).startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"expected one event for activity prefix {prefix!r}")
        return matches[0]

    inspection = event_by_activity("2.1")
    planned_case = event_by_activity("3.1")
    weighing = event_by_activity("5.1")
    loading = event_by_activity("5.6")
    draw = event_by_activity("11.1")
    cs11 = event_by_activity("13.1")

    if not (inspection["order"] < planned_case["order"] < close_order):
        raise ValueError("CS-02 inspection and planned case confirmation must precede close")
    if not (close_order < weighing["order"] < loading["order"] < draw["order"] < cs11["order"]):
        raise ValueError("weighing, loading, draw and CS-11 chronology is inconsistent")

    public = document["public_data_status"]
    v265 = document["v265_code_audit"]

    preclose_physical_values = []
    if public["draw_level_cs02_records_located"]:
        preclose_physical_values.append("CS-02 draw-level inspection")
    if public["draw_level_sphere_case_ids_located"]:
        preclose_physical_values.append("sphere-case ID")
    if public["draw_level_machine_asset_ids_located"]:
        preclose_physical_values.append("machine asset ID")
    if public["draw_level_rfid_ids_or_read_logs_located"]:
        preclose_physical_values.append("RFID ID/read log")

    blockers = []
    if not public["individual_sphere_weights_located"]:
        blockers.append("no public per-draw individual sphere weights")
    if not public["draw_level_machine_asset_ids_located"]:
        blockers.append("no public per-draw machine asset IDs")
    if not public["draw_level_sphere_case_ids_located"]:
        blockers.append("no public per-draw sphere-case IDs")
    if not public["draw_level_rfid_ids_or_read_logs_located"]:
        blockers.append("no public per-draw RFID IDs/read timestamps")
    if not public["per_sphere_extraction_order_and_timestamps_located"]:
        blockers.append("no public per-sphere extraction order/timestamps")
    if not public["draw_level_cs02_records_located"]:
        blockers.append("no public draw-level CS-02 records")
    if not public["draw_level_cs11_records_located"]:
        blockers.append("no public draw-level CS-11/Acta records")
    if not v265["anytime_e_value_gate"]:
        blockers.append("V265 evaluator has no project anytime e-value gate")
    if not v265["source_timestamp_provenance_gate"]:
        blockers.append("V265 does not verify provenance of field-specific timestamps")

    return {
        "audit_date": document["audit_date"],
        "product": document["product"],
        "procedure": document["primary_procedure"],
        "procedure_chronology_validated": True,
        "preclose_procedure_events": [
            {"activity": e["activity"], "event": e["event"], "record": e["record"]}
            for e in events if e["order"] < close_order
        ],
        "postclose_events": [
            {"activity": e["activity"], "event": e["event"], "record": e["record"]}
            for e in events if close_order < e["order"] and e["stage"] in {"post_close_pre_draw", "draw", "post_draw"}
        ],
        "same_draw_preclose_physical_values_located": preclose_physical_values,
        "any_same_draw_preclose_physical_value_located": bool(preclose_physical_values),
        "documented_operational_controls": True,
        "video_recording_policy_documented": bool(document.get("video_recording_policy", {}).get("required")),
        "video_recording_scope": document.get("video_recording_policy", {}).get("scope"),
        "video_edited_copy_is_acta_attachment": bool(document.get("video_recording_policy", {}).get("acta_attachment")),
        "public_original_recording_located": bool(public["original_room_camera_recordings_located"]),
        "measured_per_draw_mechanism_evidence": False,
        "evidence_of_physical_bias": False,
        "prospective_edge": False,
        "decision": "BLOCKED_PUBLIC_DRAW_LEVEL_PHYSICAL_DATA",
        "blockers": blockers,
        "v265_interpretation": v265["interpretation"],
        "v265_actionability_gate_complete": bool(
            v265["anytime_e_value_gate"]
            and v265["source_timestamp_provenance_gate"]
            and v265["field_specific_availability_timestamps"]
            and v265["extraction_order_gate"]
        ),
        "promotion_rule": (
            "No predictive or betting claim until exact-set prequential OOS, "
            "full multiplicity control, and the project's anytime e-value gate pass; "
            "mechanism claims additionally require per-draw physical measurements, "
            "asset/set IDs, extraction order and event timestamps."
        )
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.input)
    target = Path(args.output)
    document = json.loads(source.read_text(encoding="utf-8"))
    result = audit(document)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
