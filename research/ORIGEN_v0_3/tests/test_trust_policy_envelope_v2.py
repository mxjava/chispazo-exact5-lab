"""Synthetic adversarial tests for domain-bound policy V2 integration."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.trust_policy_envelope_v2 import (
    SCHEMA_VERSION_V2,
    verify_signed_trust_policy_v2,
)
from origen.trust_policy_integration_v2 import inspect_signed_root_attestation_chain_v2
from test_trust_verifier_v1 import signed_receipt

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
ROOT_KEY_ID = "offline-root-2026"
POLICY_DOMAIN = "origen.chispazo.classic.provenance"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def fixture(domain=POLICY_DOMAIN):
    receipt_bytes, issuer_public_bytes, _ = signed_receipt()
    root = Ed25519PrivateKey.generate()
    document = {
        "schema_version": SCHEMA_VERSION_V2,
        "policy_domain": domain,
        "policy_version": "policy-2026-11",
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
        root.sign(canonical(unsigned))
    ).decode("ascii")
    root_public = root.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return receipt_bytes, canonical(document), root_public, document


class TestTrustPolicyEnvelopeV2(unittest.TestCase):
    def verify(self, raw, root_public, **kwargs):
        values = {
            "pinned_root_public_key_bytes": root_public,
            "expected_root_key_id": ROOT_KEY_ID,
            "expected_policy_domain": POLICY_DOMAIN,
            "minimum_policy_sequence": 7,
            "verification_time": NOW,
        }
        values.update(kwargs)
        return verify_signed_trust_policy_v2(raw, **values)

    def test_valid_domain_bound_policy_verifies(self):
        _, raw, root_public, _ = fixture()
        result = self.verify(raw, root_public)
        self.assertEqual(result.policy_domain, POLICY_DOMAIN)
        self.assertEqual(result.policy_sequence, 7)
        self.assertEqual(result.policy.issuer_keys[0].issuer_id, "independent-verifier")

    def test_valid_policy_cannot_be_replayed_into_another_domain(self):
        _, raw, root_public, _ = fixture(domain="origen.chispazo.de-lastres.provenance")
        with self.assertRaisesRegex(ValueError, "does not match externally expected"):
            self.verify(raw, root_public)

    def test_domain_is_covered_by_root_signature(self):
        _, raw, root_public, document = fixture()
        document["policy_domain"] = "origen.chispazo.de-lastres.provenance"
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(
                canonical(document),
                root_public,
                expected_policy_domain="origen.chispazo.de-lastres.provenance",
            )

    def test_v1_schema_is_not_accepted_as_v2(self):
        _, raw, root_public, document = fixture()
        document["schema_version"] = "origen.trust-policy-envelope.v1"
        with self.assertRaisesRegex(ValueError, "unsupported trust-policy envelope schema"):
            self.verify(canonical(document), root_public)

    def test_policy_domain_is_required(self):
        _, raw, root_public, document = fixture()
        document.pop("policy_domain")
        with self.assertRaisesRegex(ValueError, "fields mismatch"):
            self.verify(canonical(document), root_public)

    def test_duplicate_json_keys_are_rejected(self):
        _, raw, root_public, _ = fixture()
        duplicate = raw[:-1] + b',"policy_sequence":7}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            self.verify(duplicate, root_public)

    def test_noncanonical_json_is_rejected(self):
        _, raw, root_public, _ = fixture()
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            self.verify(b" " + raw, root_public)

    def test_wrong_root_is_rejected(self):
        _, raw, _, _ = fixture()
        attacker = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(raw, attacker)

    def test_sequence_below_external_floor_is_rejected(self):
        _, raw, root_public, _ = fixture()
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.verify(raw, root_public, minimum_policy_sequence=8)


class TestTrustPolicyIntegrationV2(unittest.TestCase):
    def inspect(self, receipt, policy, root, **kwargs):
        values = {
            "pinned_root_public_key_bytes": root,
            "expected_root_key_id": ROOT_KEY_ID,
            "expected_policy_domain": POLICY_DOMAIN,
            "minimum_policy_sequence": 7,
            "verification_time": NOW,
        }
        values.update(kwargs)
        return inspect_signed_root_attestation_chain_v2(
            receipt, policy, **values
        )

    def test_policy_and_receipt_verify_but_independent_provenance_stays_blocked(self):
        receipt, policy, root, _ = fixture()
        result = self.inspect(receipt, policy, root)
        self.assertEqual(result.policy_domain, POLICY_DOMAIN)
        self.assertTrue(result.policy_signature_verified_against_supplied_anchor)
        self.assertTrue(result.receipt_signature_verified_under_policy)
        self.assertEqual(result.deployment_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.anti_rollback_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_wrong_domain_fails_before_receipt_can_be_accepted(self):
        receipt, policy, root, _ = fixture()
        with self.assertRaisesRegex(ValueError, "does not match externally expected"):
            self.inspect(
                receipt, policy, root,
                expected_policy_domain="origen.chispazo.de-lastres.provenance",
            )

    def test_caller_constructed_policy_object_is_not_accepted(self):
        receipt, _, root, _ = fixture()
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            self.inspect(receipt, object(), root)


if __name__ == "__main__":
    unittest.main()
