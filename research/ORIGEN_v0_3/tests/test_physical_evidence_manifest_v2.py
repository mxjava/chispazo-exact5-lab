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


def document_for(modality: str) -> dict:
    doc = copy.deepcopy(valid_document())
    doc["schema_version"] = SCHEMA_VERSION
    target_id = "12395" if modality == "DE_LAS_TRES" else "12396"
    for artifact in doc["artifacts"]:
        artifact["contest_id"] = target_id
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
    if modality == "DE_LAS_TRES":
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

    def test_de_las_tres_rejects_nightly_only_mjf_artifacts(self):
        doc = document_for("DE_LAS_TRES")
        classic = document_for("CLASSIC")
        mjf = copy.deepcopy(next(
            item for item in classic["artifacts"]
            if item["artifact_type"] == "MJF-TRANSACTION-FILE"
        ))
        mjf["contest_id"] = "12395"
        doc["artifacts"].append(mjf)
        with self.assertRaisesRegex(ValueError, "do not match DE_LAS_TRES requirements"):
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


if __name__ == "__main__":
    unittest.main()
