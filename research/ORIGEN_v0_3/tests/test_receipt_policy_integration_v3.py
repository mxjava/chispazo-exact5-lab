"""Adversarial tests for V3 receipt-policy composition (synthetic keys only)."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_verifier_v2 import CLASSIC_PHYSICAL_POLICY_DOMAIN
from origen.receipt_policy_integration_v3 import (
    RECEIPT_ATTESTATION_ARTIFACT_TYPE,
    RECEIPT_ATTESTER_ROLE,
    RECEIPT_ROLE_STATUS,
    verify_receipt_attestation_with_policy_v3,
)
from test_trust_receipt_v1 import encode
from test_trust_verifier_v1 import NOW, signed_receipt


ROOT_KEY_ID = "synthetic-classic-policy-root"
POLICY_SEQUENCE = 17
POLICY_VERSION = "policy-2026-11"
ISSUER_ID = "independent-verifier"
ISSUER_KEY_ID = "verifier-key-1"


def raw_public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def signed_v3_policy(
    receipt_public_key_bytes,
    *,
    role=RECEIPT_ATTESTER_ROLE,
    artifact_types=(RECEIPT_ATTESTATION_ARTIFACT_TYPE,),
    policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
    root_private=None,
):
    if root_private is None:
        root_private = Ed25519PrivateKey.generate()
    document = {
        "schema_version": "origen.trust-policy-envelope.v3",
        "policy_domain": policy_domain,
        "policy_version": POLICY_VERSION,
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-22T00:00:00Z",
        "not_before_utc": "2026-11-22T00:00:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": [
            {
                "issuer_id": ISSUER_ID,
                "key_id": ISSUER_KEY_ID,
                "public_key_b64": base64.b64encode(receipt_public_key_bytes).decode("ascii"),
                "valid_from_utc": "2026-01-01T00:00:00Z",
                "valid_until_utc": "2027-01-01T00:00:00Z",
                "revoked": False,
                "authorizations": [
                    {
                        "role": role,
                        "artifact_types": sorted(set(artifact_types)),
                    }
                ],
            }
        ],
    }
    unsigned = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["signature"] = {
        "algorithm": "ed25519",
        "signature_b64": base64.b64encode(root_private.sign(unsigned)).decode("ascii"),
    }
    envelope = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return envelope, raw_public_key(root_private)


class _StatefulOffsetTimezone(tzinfo):
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=-2 if self.calls == 1 else 2)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "stateful-integration-test"


class TestReceiptPolicyIntegrationV3(unittest.TestCase):
    def setUp(self):
        self.receipt_bytes, self.receipt_public_key, _ = signed_receipt()
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key
        )

    def inspect(self, **overrides):
        args = {
            "original_receipt_bytes": self.receipt_bytes,
            "signed_policy_envelope_bytes": self.policy_bytes,
            "pinned_root_public_key_bytes": self.root_public_key,
            "expected_root_key_id": ROOT_KEY_ID,
            "minimum_policy_sequence": POLICY_SEQUENCE,
            "verification_time": NOW,
        }
        args.update(overrides)
        return verify_receipt_attestation_with_policy_v3(**args)

    def test_valid_signed_policy_and_receipt_signature_still_remain_blocked(self):
        result = self.inspect()
        self.assertTrue(result.root_attestation_signature_verified)
        self.assertEqual(result.policy_domain, CLASSIC_PHYSICAL_POLICY_DOMAIN)
        self.assertEqual(result.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.verified_issuer_id, ISSUER_ID)
        self.assertEqual(result.verified_key_id, ISSUER_KEY_ID)
        self.assertEqual(result.role_authorization_status, RECEIPT_ROLE_STATUS)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn("RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED", result.remaining_blockers)
        self.assertIn("CUSTODY_RECEIPT_SIGNATURES_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED", result.remaining_blockers)

    def test_policy_root_key_cannot_be_reused_as_receipt_issuer_key(self):
        receipt_bytes, receipt_public, shared_private = signed_receipt()
        policy_bytes, root_public = signed_v3_policy(
            receipt_public, root_private=shared_private
        )
        self.assertEqual(root_public, receipt_public)
        with self.assertRaisesRegex(ValueError, "must not also be delegated"):
            verify_receipt_attestation_with_policy_v3(
                receipt_bytes,
                policy_bytes,
                pinned_root_public_key_bytes=root_public,
                expected_root_key_id=ROOT_KEY_ID,
                minimum_policy_sequence=POLICY_SEQUENCE,
                verification_time=NOW,
            )

    def test_valid_root_signature_without_receipt_role_authorization_is_rejected(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key, role="PHYSICAL-RECORDS-SIGNER"
        )
        with self.assertRaisesRegex(ValueError, "not authorized by the signed V3 policy"):
            self.inspect()

    def test_valid_root_signature_without_receipt_artifact_type_authorization_is_rejected(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            artifact_types=("PHYSICAL-ACTA",),
        )
        with self.assertRaisesRegex(ValueError, "not authorized by the signed V3 policy"):
            self.inspect()

    def test_policy_from_non_classic_domain_is_rejected_even_when_root_signature_is_valid(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            policy_domain="origen.chispazo.de-las-tres.provenance",
        )
        with self.assertRaisesRegex(ValueError, "does not match externally expected deployment domain"):
            self.inspect()

    def test_policy_sequence_below_external_floor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.inspect(minimum_policy_sequence=POLICY_SEQUENCE + 1)

    def test_wrong_root_pin_is_rejected(self):
        wrong_root = raw_public_key(Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.inspect(pinned_root_public_key_bytes=wrong_root)

    def test_receipt_tampering_is_rejected_before_provenance_gate(self):
        import json
        from test_trust_receipt_v1 import encode

        document = json.loads(self.receipt_bytes)
        document["artifacts"][0]["sha256"] = "f" * 64
        tampered = encode(document)
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.inspect(original_receipt_bytes=tampered)

    def test_stateful_timezone_offset_is_sampled_once_across_policy_and_receipt(self):
        tz = _StatefulOffsetTimezone()
        supplied = datetime(2026, 11, 23, 4, 0, tzinfo=tz)
        result = self.inspect(verification_time=supplied)
        self.assertEqual(tz.calls, 1)
        self.assertEqual(
            result.verification_time_utc,
            datetime(2026, 11, 23, 6, 0, tzinfo=timezone.utc),
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_v2_envelope_is_not_implicitly_accepted(self):
        self.policy_bytes = b'{"schema_version":"origen.trust-policy-envelope.v2"}'
        with self.assertRaisesRegex(ValueError, "fields mismatch"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
