"""Synthetic adversarial tests for the signed-policy -> receipt chain.

Every Ed25519 key is generated in memory per test. No fixture key or policy
anchor in this module is an institutional credential or deployment trust root.
"""
from __future__ import annotations

import base64
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from origen.trust_policy_envelope_v1 import (
    SCHEMA_VERSION as POLICY_SCHEMA,
    verify_signed_trust_policy,
)
from origen.trust_policy_receipt_chain_v1 import (
    verify_policy_bound_receipt_attestation,
)
from origen.trust_receipt_v1 import parse_unverified_receipt
from origen.trust_verifier_v1 import canonical_attestation_payload
from test_trust_receipt_v1 import encode, valid_document

NOW = datetime(2026, 11, 23, 3, 6, tzinfo=timezone.utc)
ROOT_KEY_ID = "offline-root-test-only"
POLICY_VERSION = "policy-2026-11"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def raw_public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def signed_receipt(policy_version=POLICY_VERSION):
    issuer = Ed25519PrivateKey.generate()
    document = valid_document()
    document["policy_version"] = policy_version
    document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        bytes(64)
    ).decode("ascii")
    unsigned_raw = encode(document)
    payload = canonical_attestation_payload(unsigned_raw)
    document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        issuer.sign(payload)
    ).decode("ascii")
    return encode(document), issuer, raw_public_key(issuer)


def signed_policy(issuer_public, *, sequence=7):
    root = Ed25519PrivateKey.generate()
    document = {
        "schema_version": POLICY_SCHEMA,
        "policy_version": POLICY_VERSION,
        "policy_sequence": sequence,
        "issuer_id": "policy-authority-test-only",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-23T03:00:00Z",
        "not_before_utc": "2026-11-23T03:01:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": [{
            "issuer_id": "independent-verifier",
            "key_id": "verifier-key-1",
            "public_key_b64": base64.b64encode(issuer_public).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
        }],
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = dict(document)
    unsigned.pop("signature")
    document["signature"]["signature_b64"] = base64.b64encode(
        root.sign(canonical(unsigned))
    ).decode("ascii")
    return canonical(document), root, raw_public_key(root)


class TestTrustPolicyReceiptChainV1(unittest.TestCase):
    def setUp(self):
        self.receipt, self.issuer_private, self.issuer_public = signed_receipt()
        self.policy, self.root_private, self.root_public = signed_policy(
            self.issuer_public
        )

    def verify(self, receipt=None, policy=None, **overrides):
        args = {
            "pinned_root_public_key_bytes": self.root_public,
            "expected_root_key_id": ROOT_KEY_ID,
            "minimum_policy_sequence": 7,
            "verification_time": NOW,
        }
        args.update(overrides)
        return verify_policy_bound_receipt_attestation(
            self.receipt if receipt is None else receipt,
            self.policy if policy is None else policy,
            **args,
        )

    def test_signed_policy_is_composed_directly_with_receipt_verifier(self):
        result = self.verify()
        self.assertEqual(result.scope, "ROOT_ATTESTATION_ONLY")
        self.assertEqual(result.policy_sequence, 7)
        self.assertEqual(result.root_key_id, ROOT_KEY_ID)
        self.assertEqual(result.receipt.verified_issuer_id, "independent-verifier")
        self.assertEqual(result.receipt.verified_key_id, "verifier-key-1")
        self.assertEqual(len(result.policy_envelope_sha256), 64)

    def test_policy_tampering_is_rejected_before_receipt_verification(self):
        document = json.loads(self.policy)
        document["issuer_keys"][0]["revoked"] = True
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(policy=canonical(document))

    def test_wrong_pinned_root_is_rejected(self):
        attacker = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(pinned_root_public_key_bytes=raw_public_key(attacker))

    def test_policy_sequence_rollback_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.verify(minimum_policy_sequence=8)

    def test_receipt_claim_tampering_is_rejected_by_issuer_signature(self):
        document = json.loads(self.receipt)
        document["commitments"]["candidate_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(receipt=canonical(document))

    def test_receipt_policy_version_must_match_signed_policy(self):
        mismatched, _, _ = signed_receipt("different-policy")
        with self.assertRaisesRegex(ValueError, "policy_version does not match"):
            self.verify(receipt=mismatched)

    def test_preconstructed_verified_policy_is_not_an_accepted_input(self):
        verified = verify_signed_trust_policy(
            self.policy,
            pinned_root_public_key_bytes=self.root_public,
            expected_root_key_id=ROOT_KEY_ID,
            minimum_policy_sequence=7,
            verification_time=NOW,
        )
        with self.assertRaisesRegex(ValueError, "exact bytes"):
            self.verify(policy=verified)

    def test_parsed_unverified_receipt_is_not_accepted_as_original_bytes(self):
        parsed = parse_unverified_receipt(self.receipt)
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            self.verify(receipt=parsed)

    def test_valid_root_chain_does_not_upgrade_independent_provenance(self):
        result = self.verify()
        self.assertEqual(result.scope, "ROOT_ATTESTATION_ONLY")
        self.assertIs(
            verify_independent_provenance(self.receipt),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)

    def test_independent_adapter_still_rejects_caller_injected_policy(self):
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                self.receipt,
                policy_envelope_bytes=self.policy,
                pinned_root_public_key_bytes=self.root_public,
            )

    def test_signed_policy_sequence_is_bound_to_result(self):
        policy, root, root_public = signed_policy(self.issuer_public, sequence=8)
        result = self.verify(
            policy=policy,
            pinned_root_public_key_bytes=root_public,
            minimum_policy_sequence=8,
        )
        self.assertEqual(result.policy_sequence, 8)
        self.assertEqual(result.root_key_id, ROOT_KEY_ID)


    def test_stateful_timezone_is_sampled_once_for_policy_and_receipt(self):
        class StatefulTimezone(tzinfo):
            def __init__(self):
                self.calls = 0

            def utcoffset(self, dt):
                self.calls += 1
                return timedelta(seconds=max(0, self.calls - 1))

            def dst(self, dt):
                return timedelta(0)

            def tzname(self, dt):
                return "synthetic-stateful"

        clock = StatefulTimezone()
        supplied = datetime(2026, 11, 23, 3, 6, tzinfo=clock)
        result = self.verify(verification_time=supplied)

        self.assertEqual(clock.calls, 1)
        self.assertEqual(
            result.receipt.verified_at_utc,
            datetime(2026, 11, 23, 3, 6, tzinfo=timezone.utc),
        )



if __name__ == "__main__":
    unittest.main()
