from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_verifier_v1 import (
    ROLE_AUTHORIZATION_UNVERIFIED,
    canonical_physical_manifest_signature_payload,
    verify_physical_evidence_signatures,
)
from origen.trust_policy_envelope_v1 import SCHEMA_VERSION
from test_physical_evidence_manifest_v1 import encode, valid_document

NOW = datetime(2026, 11, 24, 18, 55, tzinfo=timezone.utc)
ROOT_KEY_ID = "synthetic-root-2026"
POLICY_SEQUENCE = 7


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _raw_public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _signed_policy(private_by_identity, *, omit_identity=None, revoked_identity=None):
    root_private = Ed25519PrivateKey.generate()
    issuer_keys = []
    for (subject_id, key_id), private_key in sorted(private_by_identity.items()):
        if (subject_id, key_id) == omit_identity:
            continue
        issuer_keys.append({
            "issuer_id": subject_id,
            "key_id": key_id,
            "public_key_b64": base64.b64encode(
                _raw_public_key(private_key)
            ).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": (subject_id, key_id) == revoked_identity,
        })
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "policy-physical-evidence-test",
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-24T00:00:00Z",
        "not_before_utc": "2026-11-24T00:00:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": issuer_keys,
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = copy.deepcopy(document)
    unsigned.pop("signature")
    signature = root_private.sign(json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii"))
    document["signature"]["signature_b64"] = base64.b64encode(
        signature
    ).decode("ascii")
    return encode(document), _raw_public_key(root_private)


def fixture(*, omit_identity=None, revoked_identity=None):
    document = valid_document()
    artifact_bytes_by_sha256 = {}
    old_to_new = {}
    for index, artifact in enumerate(document["artifacts"]):
        original = bytes([index + 1]) * artifact["byte_length"]
        old_digest = artifact["sha256"]
        new_digest = _sha(original)
        old_to_new[old_digest] = new_digest
        artifact["sha256"] = new_digest
        artifact_bytes_by_sha256[new_digest] = original
    for signature_claim in document["signatures"]:
        signature_claim["artifact_sha256"] = old_to_new[
            signature_claim["artifact_sha256"]
        ]

    private_by_identity = {}
    for signature_claim in document["signatures"]:
        identity = (signature_claim["subject_id"], signature_claim["key_id"])
        private_by_identity[identity] = Ed25519PrivateKey.generate()

    # Placeholder digests are unique and valid; they are omitted from the
    # common signing payload to avoid a circular dependency.
    placeholder_raw = encode(document)
    payload = canonical_physical_manifest_signature_payload(placeholder_raw)
    signature_bytes_by_sha256 = {}
    for signature_claim in document["signatures"]:
        identity = (signature_claim["subject_id"], signature_claim["key_id"])
        signature_bytes = private_by_identity[identity].sign(payload)
        signature_digest = _sha(signature_bytes)
        signature_claim["signature_sha256"] = signature_digest
        signature_bytes_by_sha256[signature_digest] = signature_bytes

    raw_manifest_bytes = encode(document)
    assert canonical_physical_manifest_signature_payload(raw_manifest_bytes) == payload
    policy_bytes, root_public = _signed_policy(
        private_by_identity,
        omit_identity=omit_identity,
        revoked_identity=revoked_identity,
    )
    return {
        "document": document,
        "raw_manifest_bytes": raw_manifest_bytes,
        "artifact_bytes_by_sha256": artifact_bytes_by_sha256,
        "signature_bytes_by_sha256": signature_bytes_by_sha256,
        "signed_policy_envelope_bytes": policy_bytes,
        "pinned_root_public_key_bytes": root_public,
        "private_by_identity": private_by_identity,
    }


def inspect(data, **overrides):
    values = {
        "signed_policy_envelope_bytes": data["signed_policy_envelope_bytes"],
        "pinned_root_public_key_bytes": data["pinned_root_public_key_bytes"],
        "expected_root_key_id": ROOT_KEY_ID,
        "minimum_policy_sequence": POLICY_SEQUENCE,
        "verification_time": NOW,
    }
    values.update(overrides)
    return verify_physical_evidence_signatures(
        data["raw_manifest_bytes"],
        data["artifact_bytes_by_sha256"],
        data["signature_bytes_by_sha256"],
        **values,
    )


class PhysicalEvidenceSignatureVerifierV1Tests(unittest.TestCase):
    def test_exact_artifact_bytes_and_all_nested_signatures_verify(self):
        data = fixture()
        result = inspect(data)
        self.assertEqual(result.artifact_count, len(data["artifact_bytes_by_sha256"]))
        self.assertEqual(result.signatures_verified, len(data["signature_bytes_by_sha256"]))
        self.assertTrue(all(item.signature_verified for item in result.signature_results))
        self.assertEqual(result.role_authorization_status, ROLE_AUTHORIZATION_UNVERIFIED)
        self.assertEqual(result.trust_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.anti_rollback_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.verification_clock_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.trusted_time_status, "UNVERIFIED_RFC3161_REQUIRED")
        self.assertEqual(result.ledger_status, "UNVERIFIED_EXTERNAL_INCLUSION_REQUIRED")
        self.assertEqual(result.custody_status, "UNVERIFIED_INDEPENDENT_RECEIPTS_REQUIRED")
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_artifact_byte_mutation_is_rejected(self):
        data = fixture()
        first_digest = next(iter(data["artifact_bytes_by_sha256"]))
        data["artifact_bytes_by_sha256"][first_digest] += b"x"
        with self.assertRaisesRegex(ValueError, "artifact byte length mismatch|artifact SHA-256 mismatch"):
            inspect(data)

    def test_signature_digest_mismatch_is_rejected(self):
        data = fixture()
        first_digest = next(iter(data["signature_bytes_by_sha256"]))
        data["signature_bytes_by_sha256"][first_digest] += b"x"
        with self.assertRaisesRegex(ValueError, "signature SHA-256"):
            inspect(data)

    def test_rehashed_but_invalid_nested_signature_is_rejected(self):
        data = fixture()
        document = copy.deepcopy(data["document"])
        old_digest = document["signatures"][0]["signature_sha256"]
        old_bytes = data["signature_bytes_by_sha256"].pop(old_digest)
        invalid_bytes = bytes([old_bytes[0] ^ 1]) + old_bytes[1:]
        new_digest = _sha(invalid_bytes)
        document["signatures"][0]["signature_sha256"] = new_digest
        data["signature_bytes_by_sha256"][new_digest] = invalid_bytes
        data["document"] = document
        data["raw_manifest_bytes"] = encode(document)
        with self.assertRaisesRegex(ValueError, "nested Ed25519 signature verification failed"):
            inspect(data)

    def test_role_claim_is_covered_by_every_signature(self):
        data = fixture()
        document = copy.deepcopy(data["document"])
        acta = [
            item for item in document["signatures"]
            if item["artifact_sha256"] == next(
                artifact["sha256"] for artifact in document["artifacts"]
                if artifact["artifact_type"] == "DRAW-ACTA"
            )
        ]
        acta[0]["role"], acta[1]["role"] = acta[1]["role"], acta[0]["role"]
        data["raw_manifest_bytes"] = encode(document)
        with self.assertRaisesRegex(ValueError, "nested Ed25519 signature verification failed"):
            inspect(data)

    def test_signer_missing_from_verified_policy_is_rejected(self):
        initial = fixture()
        first_claim = initial["document"]["signatures"][0]
        identity = (first_claim["subject_id"], first_claim["key_id"])
        data = fixture(omit_identity=identity)
        with self.assertRaisesRegex(ValueError, "absent from verified policy"):
            inspect(data)

    def test_revoked_signer_key_is_rejected(self):
        initial = fixture()
        first_claim = initial["document"]["signatures"][0]
        identity = (first_claim["subject_id"], first_claim["key_id"])
        data = fixture(revoked_identity=identity)
        with self.assertRaisesRegex(ValueError, "signer key is revoked"):
            inspect(data)

    def test_wrong_policy_root_is_rejected(self):
        data = fixture()
        attacker = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            inspect(data, pinned_root_public_key_bytes=_raw_public_key(attacker))

    def test_artifact_map_must_be_exact(self):
        data = fixture()
        data["artifact_bytes_by_sha256"]["f" * 64] = b"unexpected"
        with self.assertRaisesRegex(ValueError, "exactly the manifest artifact digests"):
            inspect(data)

    def test_role_and_provenance_are_never_promoted(self):
        data = fixture()
        result = inspect(data)
        self.assertTrue(all(
            item.role_authorization_status == "UNVERIFIED_CLAIM_ONLY"
            for item in result.signature_results
        ))
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)


if __name__ == "__main__":
    unittest.main()
