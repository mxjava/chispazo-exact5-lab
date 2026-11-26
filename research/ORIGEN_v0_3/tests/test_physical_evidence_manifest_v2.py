"""Synthetic-only tests for modality-aware physical manifest V2."""
from __future__ import annotations

import copy
import json
import unittest

from origen.physical_evidence_manifest_v1 import REQUIRED_ARTIFACT_TYPES
from origen.physical_evidence_manifest_v2 import (
    SCHEMA_VERSION,
    UnverifiedPhysicalEvidenceManifestV2,
    parse_unverified_physical_manifest_v2,
)
from test_physical_evidence_manifest_v1 import encode, valid_document

NIGHTLY_ONLY = {"MJF-TRANSACTION-FILE", "MJF-SIGNATURE-PRINTED-FORM"}


def document_for(modality: str, include_mjf: bool = False) -> dict:
    doc = copy.deepcopy(valid_document())
    doc["schema_version"] = SCHEMA_VERSION
    target_id = "12395" if modality == "DE_LAS_TRES" else "12396"
    for artifact in doc["artifacts"]:
        is_mjf = artifact["artifact_type"] in NIGHTLY_ONLY
        artifact["scope"] = "DAILY" if is_mjf else "DRAW"
        artifact["scope_date_local"] = "2026-11-25"
        artifact["contest_id"] = None if is_mjf else target_id
    doc["target"] = {
        "modality": modality,
        "contest_id": target_id,
        "draw_date_local": "2026-11-25",
        "sales_close_at_utc": (
            "2026-11-25T21:00:00Z" if modality == "DE_LAS_TRES"
            else "2026-11-26T03:00:00Z"
        ),
        "draw_event_at_utc": (
            "2026-11-25T21:03:00Z" if modality == "DE_LAS_TRES"
            else "2026-11-26T03:04:00Z"
        ),
    }
    if modality == "CLASSIC" or include_mjf:
        mjf_digests = {
            item["sha256"] for item in doc["artifacts"]
            if item["artifact_type"] in NIGHTLY_ONLY
        }
        for event in doc["custody_events"]:
            if event["artifact_sha256"] in mjf_digests:
                event["received_at_utc"] = "2026-11-26T03:10:00Z"
                for proof in doc["trusted_time_proofs"]:
                    if proof["event_id"] == event["event_id"]:
                        proof["event_at_utc"] = event["received_at_utc"]
    if modality == "DE_LAS_TRES" and not include_mjf:
        removed = {
            item["sha256"] for item in doc["artifacts"]
            if item["artifact_type"] in NIGHTLY_ONLY
        }
        doc["artifacts"] = [
            item for item in doc["artifacts"]
            if item["artifact_type"] not in NIGHTLY_ONLY
        ]
        doc["signatures"] = [
            item for item in doc["signatures"]
            if item["artifact_sha256"] not in removed
        ]
        doc["custody_events"] = [
            item for item in doc["custody_events"]
            if item["artifact_sha256"] not in removed
        ]
        event_ids = {item["event_id"] for item in doc["custody_events"]}
        doc["trusted_time_proofs"] = [
            item for item in doc["trusted_time_proofs"]
            if item["event_id"] in event_ids
        ]
    return doc


class PhysicalEvidenceManifestV2Tests(unittest.TestCase):
    def test_classic_requires_nightly_mjf_records_and_21_slot(self):
        parsed = parse_unverified_physical_manifest_v2(encode(document_for("CLASSIC")))
        self.assertIsInstance(parsed, UnverifiedPhysicalEvidenceManifestV2)
        self.assertEqual(parsed.target.modality, "CLASSIC")
        self.assertEqual(parsed.target.contest_id, "12396")
        self.assertEqual(
            {item.artifact_type for item in parsed.artifacts} & NIGHTLY_ONLY,
            NIGHTLY_ONLY,
        )

    def test_de_las_tres_uses_15_slot_without_nightly_mjf_records(self):
        parsed = parse_unverified_physical_manifest_v2(encode(document_for("DE_LAS_TRES")))
        self.assertEqual(parsed.target.modality, "DE_LAS_TRES")
        self.assertEqual(parsed.target.contest_id, "12395")
        self.assertEqual(
            {item.artifact_type for item in parsed.artifacts} & NIGHTLY_ONLY,
            set(),
        )

    def test_classic_rejects_15_slot(self):
        doc = document_for("CLASSIC")
        doc["target"]["sales_close_at_utc"] = "2026-11-25T21:00:00Z"
        with self.assertRaisesRegex(ValueError, "CLASSIC sales_close"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_de_las_tres_rejects_21_slot(self):
        doc = document_for("DE_LAS_TRES")
        doc["target"]["sales_close_at_utc"] = "2026-11-26T03:00:00Z"
        with self.assertRaisesRegex(ValueError, "DE_LAS_TRES sales_close"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_draw_event_cannot_precede_sales_close(self):
        doc = document_for("DE_LAS_TRES")
        doc["target"]["draw_event_at_utc"] = "2026-11-25T20:59:59Z"
        with self.assertRaisesRegex(ValueError, "cannot precede"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_draw_event_must_remain_on_local_target_date(self):
        doc = document_for("CLASSIC")
        doc["target"]["draw_event_at_utc"] = "2026-11-26T06:00:00Z"
        with self.assertRaisesRegex(ValueError, "target Mexico City draw date"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_de_las_tres_rejects_partial_daily_mjf_pair(self):
        doc = document_for("DE_LAS_TRES", include_mjf=True)
        doc["artifacts"] = [
            item for item in doc["artifacts"]
            if item["artifact_type"] != "MJF-SIGNATURE-PRINTED-FORM"
        ]
        with self.assertRaisesRegex(ValueError, "complete.*pair"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_classic_rejects_missing_nightly_mjf_artifact(self):
        doc = document_for("CLASSIC")
        doc["artifacts"] = [
            item for item in doc["artifacts"]
            if item["artifact_type"] != "MJF-TRANSACTION-FILE"
        ]
        with self.assertRaisesRegex(ValueError, "do not match CLASSIC requirements"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_v1_stays_classic_only(self):
        doc = document_for("DE_LAS_TRES")
        with self.assertRaisesRegex(ValueError, "unsupported physical manifest schema_version"):
            from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest
            parse_unverified_physical_manifest(encode(doc))

    def test_only_exact_supported_modalities_are_accepted(self):
        doc = document_for("CLASSIC")
        doc["target"]["modality"] = "TRIS_CLASICO"
        with self.assertRaisesRegex(ValueError, "must be DE_LAS_TRES or CLASSIC"):
            parse_unverified_physical_manifest_v2(encode(doc))


    def test_ledger_identity_cannot_alias_artifact_source(self):
        doc = document_for("CLASSIC")
        doc["ledger_anchor"]["ledger_id"] = "LOTERIA-NACIONAL"
        with self.assertRaisesRegex(ValueError, "ledger ID must be distinct"):
            parse_unverified_physical_manifest_v2(encode(doc))


    def test_mjf_is_daily_scope_and_not_bound_to_one_contest(self):
        parsed = parse_unverified_physical_manifest_v2(encode(document_for("CLASSIC")))
        mjf = [
            item for item in parsed.artifacts
            if item.artifact_type in NIGHTLY_ONLY
        ]
        self.assertEqual(len(mjf), 2)
        self.assertTrue(all(item.scope == "DAILY" for item in mjf))
        self.assertTrue(all(item.contest_id is None for item in mjf))
        self.assertTrue(all(item.scope_date_local == "2026-11-25" for item in mjf))

    def test_classic_rejects_mjf_falsely_bound_to_draw_scope(self):
        doc = document_for("CLASSIC")
        item = next(
            item for item in doc["artifacts"]
            if item["artifact_type"] == "MJF-TRANSACTION-FILE"
        )
        item["scope"] = "DRAW"
        item["contest_id"] = "12396"
        with self.assertRaisesRegex(ValueError, "must use DAILY scope"):
            parse_unverified_physical_manifest_v2(encode(doc))

    def test_classic_rejects_mjf_custody_before_21_close(self):
        doc = document_for("CLASSIC")
        mjf_digests = {
            item["sha256"] for item in doc["artifacts"]
            if item["artifact_type"] in NIGHTLY_ONLY
        }
        for event in doc["custody_events"]:
            if event["artifact_sha256"] in mjf_digests:
                event["received_at_utc"] = "2026-11-26T02:59:59Z"
                for proof in doc["trusted_time_proofs"]:
                    if proof["event_id"] == event["event_id"]:
                        proof["event_at_utc"] = event["received_at_utc"]
        with self.assertRaisesRegex(ValueError, "at or after the 21:00"):
            parse_unverified_physical_manifest_v2(encode(doc))


    def test_de_las_tres_can_link_daily_mjf_after_21_close(self):
        parsed = parse_unverified_physical_manifest_v2(
            encode(document_for("DE_LAS_TRES", include_mjf=True))
        )
        mjf = [
            item for item in parsed.artifacts
            if item.artifact_type in NIGHTLY_ONLY
        ]
        self.assertEqual(len(mjf), 2)
        self.assertTrue(all(item.scope == "DAILY" for item in mjf))
        self.assertTrue(all(item.contest_id is None for item in mjf))
        self.assertTrue(all(item.scope_date_local == "2026-11-25" for item in mjf))

    def test_de_las_tres_mjf_custody_must_be_after_21_daily_close(self):
        doc = document_for("DE_LAS_TRES", include_mjf=True)
        mjf_digests = {
            item["sha256"] for item in doc["artifacts"]
            if item["artifact_type"] in NIGHTLY_ONLY
        }
        for event in doc["custody_events"]:
            if event["artifact_sha256"] in mjf_digests:
                event["received_at_utc"] = "2026-11-26T02:59:59Z"
                for proof in doc["trusted_time_proofs"]:
                    if proof["event_id"] == event["event_id"]:
                        proof["event_at_utc"] = event["received_at_utc"]
        with self.assertRaisesRegex(ValueError, "21:00 Mexico City daily close"):
            parse_unverified_physical_manifest_v2(encode(doc))


if __name__ == "__main__":
    unittest.main()
