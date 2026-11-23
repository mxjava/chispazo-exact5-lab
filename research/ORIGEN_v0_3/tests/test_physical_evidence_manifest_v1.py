from __future__ import annotations

import hashlib
import json
import unittest

from origen.independent_trust_adapter import ProvenanceStatus, verify_independent_provenance
from origen.physical_evidence_manifest_v1 import (
    MAX_PHYSICAL_MANIFEST_JSON_DEPTH,
    REQUIRED_ARTIFACT_TYPES,
    UnverifiedPhysicalEvidenceManifest,
    parse_unverified_physical_manifest,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def valid_document() -> dict:
    contest_id = "12390"
    artifacts = []
    for index, artifact_type in enumerate(sorted(REQUIRED_ARTIFACT_TYPES)):
        artifacts.append({
            "artifact_type": artifact_type,
            "sha256": digest(f"artifact-{index}"),
            "byte_length": 1024 + index,
            "contest_id": contest_id,
            "source_id": "LOTERIA-NACIONAL",
            "source_object_id": f"OBJECT-{index:02d}",
            "media_type": "application/pdf",
        })

    by_type = {item["artifact_type"]: item for item in artifacts}
    signatures = []
    role_sets = {
        "DRAW-ACTA": (
            "GENERAL-DIRECTORATE-REPRESENTATIVE",
            "SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE",
            "INFORMATION-TECHNOLOGY-REPRESENTATIVE",
            "SEGOB-INSPECTOR",
        ),
        "WEIGHING-STRIP": (
            "SPHERE-WEIGHING-RESPONSIBLE",
            "SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE",
            "SEGOB-INSPECTOR",
            "GENERAL-DIRECTORATE-REPRESENTATIVE",
        ),
        "PARTICIPATION-CANCELLATION-SIGNATURE-MEDIA": (
            "INFORMATION-TECHNOLOGY-REPRESENTATIVE",
        ),
    }
    signature_index = 0
    for artifact_type, roles in role_sets.items():
        artifact_sha = by_type[artifact_type]["sha256"]
        for role in roles:
            signatures.append({
                "artifact_sha256": artifact_sha,
                "subject_id": f"SIGNER-{signature_index:02d}",
                "role": role,
                "key_id": f"KEY-{signature_index:02d}",
                "algorithm": "ed25519",
                "signature_sha256": digest(f"signature-{signature_index}"),
            })
            signature_index += 1

    custody_events = []
    time_proofs = []
    for index, artifact in enumerate(artifacts):
        received = f"2026-11-23T04:00:{index:02d}Z"
        authority = f"TSA-{index:02d}"
        event_id = f"EVENT-{index:02d}"
        proof_sha = digest(f"time-proof-{index}")
        custody_events.append({
            "event_id": event_id,
            "artifact_sha256": artifact["sha256"],
            "custodian_subject_id": f"CUSTODIAN-{index:02d}",
            "custodian_role": "INDEPENDENT-ARCHIVE-CUSTODIAN",
            "received_at_utc": received,
            "receipt_sha256": digest(f"custody-receipt-{index}"),
            "timestamp_proof_sha256": proof_sha,
        })
        time_proofs.append({
            "authority_id": authority,
            "event_id": event_id,
            "event_at_utc": received,
            "proof_sha256": proof_sha,
        })

    return {
        "schema_version": "origen.physical-evidence-manifest.v1",
        "target": {
            "modality": "CLASSIC",
            "contest_id": contest_id,
            "draw_date_local": "2026-11-22",
            "draw_close_at_utc": "2026-11-23T03:00:00Z",
        },
        "artifacts": artifacts,
        "signatures": signatures,
        "custody_events": custody_events,
        "trusted_time_proofs": time_proofs,
        "ledger_anchor": {
            "ledger_id": "EXTERNAL-LEDGER",
            "entry_id": "ENTRY-12390",
            "previous_head_sha256": digest("previous-ledger-head"),
            "head_sha256": digest("current-ledger-head"),
            "inclusion_proof_sha256": digest("ledger-inclusion-proof"),
        },
    }


def encode(document: dict) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


class PhysicalEvidenceManifestV1Tests(unittest.TestCase):
    def test_valid_manifest_is_explicitly_unverified_and_adapter_stays_blocked(self):
        raw = encode(valid_document())
        parsed = parse_unverified_physical_manifest(raw)
        self.assertIsInstance(parsed, UnverifiedPhysicalEvidenceManifest)
        self.assertEqual(parsed.target.modality, "CLASSIC")
        self.assertEqual(parsed.target.contest_id, "12390")
        self.assertEqual(len(parsed.artifacts), len(REQUIRED_ARTIFACT_TYPES))
        self.assertEqual(len(parsed.custody_events), len(REQUIRED_ARTIFACT_TYPES))
        self.assertEqual(parsed.raw_sha256, hashlib.sha256(raw).hexdigest())
        self.assertFalse(hasattr(parsed, "authenticated"))
        self.assertIs(
            verify_independent_provenance(raw),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_missing_required_artifact_is_rejected(self):
        document = valid_document()
        document["artifacts"].pop()
        with self.assertRaisesRegex(ValueError, "array with 11..11"):
            parse_unverified_physical_manifest(encode(document))

    def test_duplicate_artifact_type_is_rejected_even_with_another_digest(self):
        document = valid_document()
        document["artifacts"][-1]["artifact_type"] = document["artifacts"][0]["artifact_type"]
        with self.assertRaisesRegex(ValueError, "duplicate artifact types"):
            parse_unverified_physical_manifest(encode(document))

    def test_duplicate_source_object_id_is_rejected(self):
        document = valid_document()
        document["artifacts"][-1]["source_object_id"] = document["artifacts"][0]["source_object_id"]
        with self.assertRaisesRegex(ValueError, "duplicate source_object_id"):
            parse_unverified_physical_manifest(encode(document))

    def test_artifact_for_another_contest_is_rejected(self):
        document = valid_document()
        document["artifacts"][0]["contest_id"] = "12389"
        with self.assertRaisesRegex(ValueError, "bind to the target contest"):
            parse_unverified_physical_manifest(encode(document))

    def test_de_las_tres_1500_slot_is_rejected_for_classic(self):
        document = valid_document()
        document["target"]["draw_close_at_utc"] = "2026-11-22T21:00:00Z"
        with self.assertRaisesRegex(ValueError, "official 21:00"):
            parse_unverified_physical_manifest(encode(document))

    def test_target_local_date_must_match_utc_close(self):
        document = valid_document()
        document["target"]["draw_date_local"] = "2026-11-21"
        with self.assertRaisesRegex(ValueError, "does not match"):
            parse_unverified_physical_manifest(encode(document))

    def test_acta_requires_policy_two_representatives_and_segob(self):
        document = valid_document()
        acta_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "DRAW-ACTA"
        )
        document["signatures"] = [
            item for item in document["signatures"]
            if not (
                item["artifact_sha256"] == acta_sha
                and item["role"] == "INFORMATION-TECHNOLOGY-REPRESENTATIVE"
            )
        ]
        with self.assertRaisesRegex(ValueError, "DRAW-ACTA signatures are missing"):
            parse_unverified_physical_manifest(encode(document))

    def test_weighing_strip_requires_exact_four_activity_5_4_roles(self):
        document = valid_document()
        strip_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "WEIGHING-STRIP"
        )
        document["signatures"] = [
            item for item in document["signatures"]
            if not (
                item["artifact_sha256"] == strip_sha
                and item["role"] == "SEGOB-INSPECTOR"
            )
        ]
        with self.assertRaisesRegex(ValueError, "exactly four distinct signers"):
            parse_unverified_physical_manifest(encode(document))

    def test_weighing_strip_roles_must_have_distinct_subjects(self):
        document = valid_document()
        strip_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "WEIGHING-STRIP"
        )
        strip_signatures = [
            item for item in document["signatures"]
            if item["artifact_sha256"] == strip_sha
        ]
        strip_signatures[1]["subject_id"] = strip_signatures[0]["subject_id"]
        with self.assertRaisesRegex(ValueError, "one signature per artifact"):
            parse_unverified_physical_manifest(encode(document))

    def test_signature_cannot_reference_unknown_artifact(self):
        document = valid_document()
        document["signatures"][0]["artifact_sha256"] = digest("not-in-manifest")
        with self.assertRaisesRegex(ValueError, "absent from the manifest"):
            parse_unverified_physical_manifest(encode(document))

    def test_signed_artifact_requires_a_signature_claim(self):
        document = valid_document()
        strip_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "WEIGHING-STRIP"
        )
        document["signatures"] = [
            item for item in document["signatures"]
            if item["artifact_sha256"] != strip_sha
        ]
        with self.assertRaisesRegex(ValueError, "must have at least one declared signature"):
            parse_unverified_physical_manifest(encode(document))

    def test_every_artifact_requires_a_custody_event(self):
        document = valid_document()
        document["custody_events"].pop()
        with self.assertRaisesRegex(ValueError, "array with 11..4096"):
            parse_unverified_physical_manifest(encode(document))

    def test_custody_time_must_match_referenced_time_proof(self):
        document = valid_document()
        document["custody_events"][0]["received_at_utc"] = "2026-11-23T05:00:00Z"
        with self.assertRaisesRegex(ValueError, "must match its referenced time proof"):
            parse_unverified_physical_manifest(encode(document))

    def test_custody_event_must_reference_declared_time_proof(self):
        document = valid_document()
        document["custody_events"][0]["timestamp_proof_sha256"] = digest("missing-proof")
        with self.assertRaisesRegex(ValueError, "timestamp proof is not declared"):
            parse_unverified_physical_manifest(encode(document))

    def test_duplicate_time_authority_event_identity_is_rejected(self):
        document = valid_document()
        document["trusted_time_proofs"][1]["authority_id"] = document["trusted_time_proofs"][0]["authority_id"]
        document["trusted_time_proofs"][1]["event_id"] = document["trusted_time_proofs"][0]["event_id"]
        with self.assertRaisesRegex(ValueError, "duplicate authority/event identities"):
            parse_unverified_physical_manifest(encode(document))

    def test_time_authority_cannot_alias_signer_or_custodian_subject(self):
        document = valid_document()
        document["trusted_time_proofs"][0]["authority_id"] = document["signatures"][0]["subject_id"]
        with self.assertRaisesRegex(ValueError, "distinct from signers and custodians"):
            parse_unverified_physical_manifest(encode(document))

    def test_ledger_head_must_advance(self):
        document = valid_document()
        document["ledger_anchor"]["head_sha256"] = document["ledger_anchor"]["previous_head_sha256"]
        with self.assertRaisesRegex(ValueError, "must advance"):
            parse_unverified_physical_manifest(encode(document))

    def test_boolean_is_not_accepted_as_byte_length(self):
        document = valid_document()
        document["artifacts"][0]["byte_length"] = True
        with self.assertRaisesRegex(ValueError, "positive integer"):
            parse_unverified_physical_manifest(encode(document))

    def test_duplicate_json_object_key_is_rejected(self):
        raw = b'{"schema_version":"origen.physical-evidence-manifest.v1","schema_version":"origen.physical-evidence-manifest.v1"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_unverified_physical_manifest(raw)

    def test_noncanonical_json_is_rejected(self):
        raw = json.dumps(valid_document(), sort_keys=False, separators=(",", ":")).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            parse_unverified_physical_manifest(raw)

    def test_excessive_nesting_is_rejected_before_json_decode(self):
        raw = b"[" * (MAX_PHYSICAL_MANIFEST_JSON_DEPTH + 1) + b"0" + b"]" * (MAX_PHYSICAL_MANIFEST_JSON_DEPTH + 1)
        with self.assertRaisesRegex(ValueError, "maximum JSON nesting depth"):
            parse_unverified_physical_manifest(raw)


if __name__ == "__main__":
    unittest.main()
