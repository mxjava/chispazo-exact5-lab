"""Composition tests for signed trust policy -> root-attested receipt.

Every key below is generated in-process for tests. No fixture key is an
institutional trust anchor or may be copied into deployment configuration.
"""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.deployment_trust_bootstrap import _ProvisionedTrustBootstrap
from origen.independent_trust_adapter import (
    ProvenanceStatus,
    _verify_root_attestation_layer,
    verify_independent_provenance,
)
from origen.trust_policy_envelope_v1 import SCHEMA_VERSION
from origen.trust_verifier_v1 import CryptographicallyVerifiedReceipt
from test_trust_receipt_v1 import encode, valid_document
from test_trust_verifier_v1 import sign_document

NOW = datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc)
ROOT_ID = "offline-root-synthetic-only"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def raw_public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def synthetic_bootstrap(*, minimum_sequence=7, wrong_root=False):
    """Build a complete, synthetic policy/receipt pair for unit tests only."""
    root = Ed25519PrivateKey.generate()
    issuer = Ed25519PrivateKey.generate()
    issuer_public = raw_public_key(issuer)
    policy_document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "policy-2026-11",
        "policy_sequence": 7,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_ID,
        "issued_at_utc": "2026-11-23T02:00:00Z",
        "not_before_utc": "2026-11-23T03:00:00Z",
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
    unsigned_policy = dict(policy_document)
    unsigned_policy.pop("signature")
    policy_document["signature"]["signature_b64"] = base64.b64encode(
        root.sign(canonical(unsigned_policy))
    ).decode("ascii")

    receipt_document = valid_document()
    receipt_bytes = sign_document(receipt_document, issuer)
    pinned_root = raw_public_key(root)
    if wrong_root:
        pinned_root = raw_public_key(Ed25519PrivateKey.generate())

    bootstrap = _ProvisionedTrustBootstrap(
        policy_envelope_bytes=canonical(policy_document),
        pinned_root_public_key_bytes=pinned_root,
        expected_root_key_id=ROOT_ID,
        minimum_policy_sequence=minimum_sequence,
        verification_time=NOW,
    )
    return bootstrap, receipt_bytes


class TestTrustPolicyReceiptComposition(unittest.TestCase):
    def test_signed_policy_is_verified_then_used_for_receipt_attestation(self):
        bootstrap, receipt_bytes = synthetic_bootstrap()
        verified_policy, verified_receipt = _verify_root_attestation_layer(
            receipt_bytes, bootstrap
        )
        self.assertEqual(verified_policy.policy_sequence, 7)
        self.assertEqual(verified_policy.root_key_id, ROOT_ID)
        self.assertIsInstance(verified_receipt, CryptographicallyVerifiedReceipt)
        self.assertEqual(verified_receipt.verified_issuer_id, "independent-verifier")
        self.assertEqual(verified_receipt.verified_key_id, "verifier-key-1")

    def test_wrong_out_of_band_root_pin_fails_composition(self):
        bootstrap, receipt_bytes = synthetic_bootstrap(wrong_root=True)
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            _verify_root_attestation_layer(receipt_bytes, bootstrap)

    def test_external_minimum_sequence_rejects_signed_policy_rollback(self):
        bootstrap, receipt_bytes = synthetic_bootstrap(minimum_sequence=8)
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            _verify_root_attestation_layer(receipt_bytes, bootstrap)

    def test_receipt_tampering_after_policy_verification_is_rejected(self):
        bootstrap, receipt_bytes = synthetic_bootstrap()
        document = json.loads(receipt_bytes)
        document["artifacts"][0]["sha256"] = "f" * 64
        tampered = encode(document)
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            _verify_root_attestation_layer(tampered, bootstrap)

    def test_bootstrap_must_be_exact_internal_snapshot_type(self):
        _, receipt_bytes = synthetic_bootstrap()
        with self.assertRaisesRegex(TypeError, "exact deployment bootstrap"):
            _verify_root_attestation_layer(receipt_bytes, object())

    def test_helper_does_not_accept_preconstructed_verified_policy(self):
        bootstrap, receipt_bytes = synthetic_bootstrap()
        verified_policy, _ = _verify_root_attestation_layer(receipt_bytes, bootstrap)
        with self.assertRaises(TypeError):
            _verify_root_attestation_layer(receipt_bytes, verified_policy)

    def test_public_adapter_stays_blocked_without_deployment_provisioning(self):
        bootstrap, receipt_bytes = synthetic_bootstrap()
        self.assertIs(
            verify_independent_provenance(receipt_bytes),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_valid_synthetic_root_chain_still_cannot_promote_public_adapter(self):
        bootstrap, receipt_bytes = synthetic_bootstrap()
        with patch(
            "origen.independent_trust_adapter._load_provisioned_trust_bootstrap",
            return_value=bootstrap,
        ):
            self.assertIs(
                verify_independent_provenance(receipt_bytes),
                ProvenanceStatus.BLOCKED_PROVENANCE,
            )

    def test_invalid_provisioned_root_chain_fails_closed(self):
        bootstrap, receipt_bytes = synthetic_bootstrap(wrong_root=True)
        with patch(
            "origen.independent_trust_adapter._load_provisioned_trust_bootstrap",
            return_value=bootstrap,
        ):
            self.assertIs(
                verify_independent_provenance(receipt_bytes),
                ProvenanceStatus.BLOCKED_PROVENANCE,
            )

    def test_caller_cannot_supply_bootstrap_or_verifier_to_public_adapter(self):
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                b"receipt", bootstrap=synthetic_bootstrap()[0]
            )
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(b"receipt", verifier=lambda *_: True)


if __name__ == "__main__":
    unittest.main()
