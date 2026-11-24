"""Synthetic end-to-end tests for the fail-closed signed root-chain inspector."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus, verify_independent_provenance
from origen.trust_policy_integration_v1 import (
    ROOT_CHAIN_REMAINING_BLOCKERS,
    inspect_signed_root_attestation_chain,
)
from origen.trust_policy_envelope_v1 import SCHEMA_VERSION
from test_trust_receipt_v1 import encode
from test_trust_verifier_v1 import signed_receipt

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
POLICY_VERSION = "policy-2026-11"
ROOT_KEY_ID = "offline-root-2026"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def signed_policy(issuer_public_bytes):
    root_private = Ed25519PrivateKey.generate()
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "policy_sequence": 7,
        "issuer_id": "policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-24T10:00:00Z",
        "not_before_utc": "2026-11-24T11:00:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": [{
            "issuer_id": "independent-verifier",
            "key_id": "verifier-key-1",
            "public_key_b64": base64.b64encode(issuer_public_bytes).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
        }],
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = copy.deepcopy(document)
    unsigned.pop("signature")
    document["signature"]["signature_b64"] = base64.b64encode(
        root_private.sign(canonical(unsigned))
    ).decode("ascii")
    root_public = root_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return canonical(document), root_public


def fixture():
    receipt_bytes, issuer_public_bytes, _ = signed_receipt()
    policy_bytes, root_public_bytes = signed_policy(issuer_public_bytes)
    return receipt_bytes, policy_bytes, root_public_bytes


class TestSignedRootChainIntegrationV1(unittest.TestCase):
    def inspect(self, receipt_bytes, policy_bytes, root_public_bytes, **kwargs):
        values = {
            "pinned_root_public_key_bytes": root_public_bytes,
            "expected_root_key_id": ROOT_KEY_ID,
            "minimum_policy_sequence": 7,
            "verification_time": NOW,
        }
        values.update(kwargs)
        return inspect_signed_root_attestation_chain(
            receipt_bytes, policy_bytes, **values
        )

    def test_both_signatures_verify_but_provenance_remains_blocked(self):
        receipt_bytes, policy_bytes, root_public_bytes = fixture()
        result = self.inspect(receipt_bytes, policy_bytes, root_public_bytes)

        self.assertTrue(result.policy_signature_verified_against_supplied_anchor)
        self.assertTrue(result.receipt_signature_verified_under_policy)
        self.assertEqual(result.policy_sequence, 7)
        self.assertEqual(result.policy_root_key_id, ROOT_KEY_ID)
        self.assertEqual(result.verified_issuer_id, "independent-verifier")
        self.assertEqual(result.verified_key_id, "verifier-key-1")
        self.assertEqual(len(result.policy_envelope_sha256), 64)
        self.assertEqual(len(result.receipt_sha256), 64)
        self.assertEqual(len(result.signed_payload_sha256), 64)
        self.assertEqual(
            result.deployment_anchor_source,
            "CALLER_SUPPLIED_UNAUTHENTICATED",
        )
        self.assertEqual(
            result.anti_rollback_source,
            "CALLER_SUPPLIED_UNAUTHENTICATED",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.remaining_blockers, ROOT_CHAIN_REMAINING_BLOCKERS)
        self.assertIs(
            verify_independent_provenance(receipt_bytes),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_receipt_claim_tampering_fails_after_policy_verification(self):
        receipt_bytes, policy_bytes, root_public_bytes = fixture()
        document = json.loads(receipt_bytes)
        document["artifacts"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.inspect(
                encode(document), policy_bytes, root_public_bytes
            )

    def test_wrong_root_anchor_is_rejected(self):
        receipt_bytes, policy_bytes, _ = fixture()
        attacker_root = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.inspect(receipt_bytes, policy_bytes, attacker_root)

    def test_external_minimum_sequence_rejects_policy_rollback(self):
        receipt_bytes, policy_bytes, root_public_bytes = fixture()
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.inspect(
                receipt_bytes,
                policy_bytes,
                root_public_bytes,
                minimum_policy_sequence=8,
            )

    def test_policy_expiry_is_checked_before_receipt_verification(self):
        receipt_bytes, policy_bytes, root_public_bytes = fixture()
        after_expiry = datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "not currently valid"):
            self.inspect(
                receipt_bytes,
                policy_bytes,
                root_public_bytes,
                verification_time=after_expiry,
            )

    def test_caller_constructed_policy_object_is_not_an_input(self):
        receipt_bytes, policy_bytes, root_public_bytes = fixture()
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            self.inspect(
                receipt_bytes,
                object(),
                root_public_bytes,
            )

    def test_no_root_signature_result_can_change_the_adapter_status(self):
        receipt_bytes, policy_bytes, root_public_bytes = fixture()
        result = self.inspect(receipt_bytes, policy_bytes, root_public_bytes)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)


if __name__ == "__main__":
    unittest.main()
