from __future__ import annotations

import hashlib
import json
import unittest

from origen.independent_trust_adapter import ProvenanceStatus, verify_independent_provenance
from origen.mapping_artifact_binding import verify_mapping_artifact_byte_binding
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
            "media_type": (
                "video/mp4" if artifact_type.startswith("DRAW-RECORDING-")
                else "text/csv" if artifact_type == "SPHERE-NUMBER-MAPPING-REGISTER"
                else "application/pdf"
            ),
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
        "WINNER-RELATION-REPORT-WITH-SIGNATURE": (
            "INFORMATION-TECHNOLOGY-REPRESENTATIVE",
        ),
        "MJF-SIGNATURE-PRINTED-FORM": (
            "INFORMATION-TECHNOLOGY-REPRESENTATIVE",
        ),
        "CS02-DAILY-EQUIPMENT-INSPECTION": (
            "EQUIPMENT-OPERATOR",
            "SUBDIRECTORATE-GENERAL-SALES-OPERATIONS-REPRESENTATIVE",
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


def replace_artifact_bytes(document: dict, artifact: dict, raw: bytes) -> None:
    """Keep manifest-internal references consistent when a fixture artifact changes."""
    old_digest = artifact["sha256"]
    new_digest = hashlib.sha256(raw).hexdigest()
    artifact["sha256"] = new_digest
    artifact["byte_length"] = len(raw)
    for signature in document["signatures"]:
        if signature["artifact_sha256"] == old_digest:
            signature["artifact_sha256"] = new_digest
    for event in document["custody_events"]:
        if event["artifact_sha256"] == old_digest:
            event["artifact_sha256"] = new_digest


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
        media_by_type = {item.artifact_type: item.media_type for item in parsed.artifacts}
        self.assertEqual(media_by_type["DRAW-RECORDING-FULL"], "video/mp4")
        self.assertEqual(media_by_type["SPHERE-NUMBER-MAPPING-REGISTER"], "text/csv")
        self.assertFalse(hasattr(parsed, "authenticated"))
        self.assertIs(
            verify_independent_provenance(raw),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_missing_required_artifact_is_rejected(self):
        document = valid_document()
        document["artifacts"].pop()
        with self.assertRaisesRegex(ValueError, rf"array with {len(REQUIRED_ARTIFACT_TYPES)}..{len(REQUIRED_ARTIFACT_TYPES)}"):
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

    def test_acta_required_roles_cannot_be_claimed_by_one_subject(self):
        document = valid_document()
        acta_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "DRAW-ACTA"
        )
        acta_signatures = [
            item for item in document["signatures"]
            if item["artifact_sha256"] == acta_sha
        ]
        self.assertEqual(len(acta_signatures), 4)
        for item in acta_signatures:
            item["subject_id"] = "ONE-CLAIMED-SUBJECT"
        with self.assertRaisesRegex(ValueError, "a subject may declare only one signature per artifact"):
            parse_unverified_physical_manifest(encode(document))

    def test_cs02_inspection_requires_operator_and_sgvo_roles(self):
        document = valid_document()
        artifact_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "CS02-DAILY-EQUIPMENT-INSPECTION"
        )
        document["signatures"] = [
            item for item in document["signatures"]
            if not (
                item["artifact_sha256"] == artifact_sha
                and item["role"] == "EQUIPMENT-OPERATOR"
            )
        ]
        with self.assertRaisesRegex(ValueError, "CS02-DAILY-EQUIPMENT-INSPECTION signatures are missing"):
            parse_unverified_physical_manifest(encode(document))

    def test_winner_relation_report_requires_it_signature(self):
        document = valid_document()
        artifact_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "WINNER-RELATION-REPORT-WITH-SIGNATURE"
        )
        document["signatures"] = [
            item for item in document["signatures"]
            if item["artifact_sha256"] != artifact_sha
        ]
        with self.assertRaisesRegex(ValueError, "must have at least one declared signature"):
            parse_unverified_physical_manifest(encode(document))

    def test_mjf_signature_form_requires_it_signature(self):
        document = valid_document()
        artifact_sha = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "MJF-SIGNATURE-PRINTED-FORM"
        )
        document["signatures"] = [
            item for item in document["signatures"]
            if item["artifact_sha256"] != artifact_sha
        ]
        with self.assertRaisesRegex(ValueError, "must have at least one declared signature"):
            parse_unverified_physical_manifest(encode(document))

    def test_recording_full_and_edited_are_distinct_required_artifacts(self):
        document = valid_document()
        recording_types = {
            item["artifact_type"] for item in document["artifacts"]
            if item["artifact_type"].startswith("DRAW-RECORDING-")
        }
        self.assertEqual(recording_types, {"DRAW-RECORDING-FULL", "DRAW-RECORDING-EDITED"})
        document["artifacts"] = [
            item for item in document["artifacts"]
            if item["artifact_type"] != "DRAW-RECORDING-FULL"
        ]
        with self.assertRaisesRegex(ValueError, rf"array with {len(REQUIRED_ARTIFACT_TYPES)}..{len(REQUIRED_ARTIFACT_TYPES)}"):
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
        with self.assertRaisesRegex(ValueError, rf"array with {len(REQUIRED_ARTIFACT_TYPES)}..4096"):
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

    def test_custody_event_id_must_match_referenced_time_proof_event_id(self):
        document = valid_document()
        document["trusted_time_proofs"][0]["event_id"] = "DIFFERENT-EVENT"
        with self.assertRaisesRegex(ValueError, "custody event ID must match"):
            parse_unverified_physical_manifest(encode(document))

    def test_duplicate_custody_event_id_is_rejected_across_custodians(self):
        document = valid_document()
        document["custody_events"][1]["event_id"] = document["custody_events"][0]["event_id"]
        with self.assertRaisesRegex(ValueError, "duplicate event IDs"):
            parse_unverified_physical_manifest(encode(document))

    def test_signature_digest_cannot_be_reused_across_claims(self):
        document = valid_document()
        document["signatures"][1]["signature_sha256"] = document["signatures"][0]["signature_sha256"]
        with self.assertRaisesRegex(ValueError, "duplicate signature digests"):
            parse_unverified_physical_manifest(encode(document))

    def test_signer_key_id_cannot_alias_two_subjects(self):
        document = valid_document()
        document["signatures"][1]["key_id"] = document["signatures"][0]["key_id"]
        with self.assertRaisesRegex(ValueError, "key_id cannot be bound to multiple subject IDs"):
            parse_unverified_physical_manifest(encode(document))

    def test_invalid_media_type_is_rejected(self):
        document = valid_document()
        document["artifacts"][0]["media_type"] = "application"
        with self.assertRaisesRegex(ValueError, "canonical MIME type"):
            parse_unverified_physical_manifest(encode(document))

    def test_recording_mime_claims_must_match_artifact_semantics(self):
        cases = (
            ("DRAW-RECORDING-FULL", "application/pdf"),
            ("DRAW-ACTA", "video/mp4"),
        )
        for artifact_type, media_type in cases:
            with self.subTest(artifact_type=artifact_type, media_type=media_type):
                document = valid_document()
                artifact = next(
                    item for item in document["artifacts"]
                    if item["artifact_type"] == artifact_type
                )
                artifact["media_type"] = media_type
                with self.assertRaisesRegex(ValueError, "media_type is incompatible"):
                    parse_unverified_physical_manifest(encode(document))

    def test_unrecognized_custodian_role_remains_an_untrusted_declaration(self):
        # The role is a schema label only. It cannot establish identity,
        # authorization, or independence; the parsed type exposes no such claim.
        document = valid_document()
        document["custody_events"][0]["custodian_role"] = "ROOT-ADMIN"
        parsed = parse_unverified_physical_manifest(encode(document))
        self.assertEqual(parsed.custody_events[0].custodian_role, "ROOT-ADMIN")
        self.assertFalse(hasattr(parsed, "authenticated"))
        self.assertEqual(type(parsed).__name__, "UnverifiedPhysicalEvidenceManifest")

    def test_custodian_subject_cannot_alias_signer_subject(self):
        document = valid_document()
        document["custody_events"][0]["custodian_subject_id"] = document["signatures"][0]["subject_id"]
        with self.assertRaisesRegex(ValueError, "signer and custodian claims must be separate"):
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

    def test_artifact_source_cannot_alias_signer_custodian_or_time_authority(self):
        aliases = (
            ("signer", lambda document: document["signatures"][0]["subject_id"]),
            ("custodian", lambda document: document["custody_events"][0]["custodian_subject_id"]),
            ("trusted time authority", lambda document: document["trusted_time_proofs"][0]["authority_id"]),
        )
        for label, identity in aliases:
            with self.subTest(alias=label):
                document = valid_document()
                document["artifacts"][0]["source_id"] = identity(document)
                with self.assertRaisesRegex(
                    ValueError,
                    "artifact source IDs must be distinct from signers, custodians, and trusted time authorities",
                ):
                    parse_unverified_physical_manifest(encode(document))

    def test_repeated_source_id_across_artifacts_remains_valid(self):
        document = valid_document()
        for artifact in document["artifacts"]:
            artifact["source_id"] = "LOTERIA-NACIONAL"
        parsed = parse_unverified_physical_manifest(encode(document))
        self.assertEqual({item.source_id for item in parsed.artifacts}, {"LOTERIA-NACIONAL"})

    def test_ledger_id_cannot_alias_any_declared_trust_participant(self):
        aliases = (
            ("artifact source", lambda document: document["artifacts"][0]["source_id"]),
            ("signer", lambda document: document["signatures"][0]["subject_id"]),
            ("custodian", lambda document: document["custody_events"][0]["custodian_subject_id"]),
            ("trusted time authority", lambda document: document["trusted_time_proofs"][0]["authority_id"]),
        )
        for label, identity in aliases:
            with self.subTest(alias=label):
                document = valid_document()
                document["ledger_anchor"]["ledger_id"] = identity(document)
                with self.assertRaisesRegex(
                    ValueError,
                    "ledger ID must be distinct from artifact sources, signers, custodians, and trusted time authorities",
                ):
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


    def test_mapping_binding_extracts_claim_from_exact_original_manifest_bytes(self):
        mapping_bytes = b"original institutional mapping-register bytes"
        document = valid_document()
        mapping_claim = next(
            item for item in document["artifacts"]
            if item["artifact_type"] == "SPHERE-NUMBER-MAPPING-REGISTER"
        )
        replace_artifact_bytes(document, mapping_claim, mapping_bytes)
        manifest_bytes = encode(document)
        rows = [
            {
                "target_contest_id": document["target"]["contest_id"],
                "mapping_artifact_ref": mapping_claim["source_object_id"],
                "mapping_artifact_sha256": mapping_claim["sha256"],
                "sphere_id": f"SPHERE-{number:02d}",
                "printed_number": str(number),
            }
            for number in range(1, 29)
        ]

        result = verify_mapping_artifact_byte_binding(
            rows, manifest_bytes, mapping_bytes
        )

        self.assertEqual(result.status, "MAPPING_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED")
        self.assertEqual(result.manifest_sha256, hashlib.sha256(manifest_bytes).hexdigest())
        self.assertEqual(result.source_object_id, mapping_claim["source_object_id"])
        self.assertEqual(result.row_count, 28)

    def test_mapping_binding_rejects_caller_constructed_claim_instead_of_manifest_bytes(self):
        document = valid_document()
        mapping_claim = next(
            item for item in document["artifacts"]
            if item["artifact_type"] == "SPHERE-NUMBER-MAPPING-REGISTER"
        )
        from origen.physical_evidence_manifest_v1 import PhysicalArtifactClaim
        caller_claim = PhysicalArtifactClaim(
            artifact_type=mapping_claim["artifact_type"],
            sha256=mapping_claim["sha256"],
            byte_length=mapping_claim["byte_length"],
            contest_id=mapping_claim["contest_id"],
            source_id=mapping_claim["source_id"],
            source_object_id=mapping_claim["source_object_id"],
            media_type=mapping_claim["media_type"],
        )
        with self.assertRaisesRegex(TypeError, "original_manifest_bytes"):
            verify_mapping_artifact_byte_binding([], caller_claim, b"opaque")

    def test_mapping_binding_rejects_rows_not_bound_to_manifest_extracted_claim(self):
        mapping_bytes = b"original institutional mapping-register bytes"
        document = valid_document()
        mapping_claim = next(
            item for item in document["artifacts"]
            if item["artifact_type"] == "SPHERE-NUMBER-MAPPING-REGISTER"
        )
        replace_artifact_bytes(document, mapping_claim, mapping_bytes)
        manifest_bytes = encode(document)
        rows = [
            {
                "target_contest_id": document["target"]["contest_id"],
                "mapping_artifact_ref": mapping_claim["source_object_id"],
                "mapping_artifact_sha256": mapping_claim["sha256"],
                "sphere_id": f"SPHERE-{number:02d}",
                "printed_number": str(number),
            }
            for number in range(1, 29)
        ]
        rows[0]["mapping_artifact_ref"] = "CALLER-SUBSTITUTED-OBJECT"
        with self.assertRaisesRegex(ValueError, "reference does not match"):
            verify_mapping_artifact_byte_binding(rows, manifest_bytes, mapping_bytes)


if __name__ == "__main__":
    unittest.main()
