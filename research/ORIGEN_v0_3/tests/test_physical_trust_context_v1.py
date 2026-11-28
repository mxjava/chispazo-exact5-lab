"""Synthetic validation of provider-owned physical trust context."""
from __future__ import annotations

import hashlib
import unittest

from types import SimpleNamespace

from origen.deployment_evidence_composition_v1 import _read_physical_trust_context
from origen.physical_trust_context_v1 import (
    PhysicalTrustContextV1,
    physical_trust_context_sha256,
)


def valid_context(**overrides):
    policy_tsa = b"synthetic-policy-tsa"
    custody_tsa = b"synthetic-custody-tsa"
    values = {
        "policy_tsa_root_certificate_der": policy_tsa,
        "policy_tsa_root_sha256": hashlib.sha256(policy_tsa).hexdigest(),
        "policy_tsa_policy_oid": "1.2.3.4",
        "policy_root_public_key_bytes": b"p" * 32,
        "policy_root_key_id": "policy-root-v1",
        "minimum_policy_sequence": 2,
        "custody_tsa_root_certificate_der": custody_tsa,
        "custody_tsa_root_sha256": hashlib.sha256(custody_tsa).hexdigest(),
        "log_public_key_bytes": b"l" * 32,
        "log_id": "log-classic",
        "log_key_id": "log-key-v1",
        "registry_root_public_key_bytes": b"r" * 32,
        "registry_root_key_id": "registry-root-v1",
        "registry_id": "witness-registry-classic",
        "minimum_registry_sequence": 3,
    }
    values.update(overrides)
    return PhysicalTrustContextV1(**values)


class PhysicalTrustContextTests(unittest.TestCase):
    def test_valid_context_binds_exact_certificate_bytes(self):
        context = valid_context()
        self.assertEqual(
            context.policy_tsa_root_sha256,
            hashlib.sha256(context.policy_tsa_root_certificate_der).hexdigest(),
        )
        self.assertEqual(
            context.custody_tsa_root_sha256,
            hashlib.sha256(context.custody_tsa_root_certificate_der).hexdigest(),
        )

    def test_rejects_certificate_fingerprint_mismatch(self):
        with self.assertRaisesRegex(ValueError, "does not bind the exact certificate bytes"):
            valid_context(policy_tsa_root_sha256="0" * 64)

    def test_rejects_non_ed25519_key_lengths(self):
        with self.assertRaisesRegex(ValueError, "32-byte Ed25519 key"):
            valid_context(log_public_key_bytes=b"short")

    def test_rejects_boolean_sequence_floor(self):
        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            valid_context(minimum_policy_sequence=True)

    def test_rejects_mutable_certificate_input(self):
        with self.assertRaisesRegex(ValueError, "immutable bytes"):
            valid_context(custody_tsa_root_certificate_der=bytearray(b"mutable"))

    def test_nested_bundle_tsa_anchor_is_optional_for_legacy_v1_context(self):
        context = valid_context()
        self.assertIsNone(context.nested_signature_bundle_tsa_root_certificate_der)
        self.assertIsNone(context.nested_signature_bundle_tsa_root_sha256)
        self.assertIsNone(context.nested_signature_bundle_tsa_policy_oid)

    def test_nested_bundle_tsa_pin_requires_all_three_fields(self):
        with self.assertRaisesRegex(ValueError, "must be provisioned together"):
            valid_context(
                nested_signature_bundle_tsa_root_certificate_der=b"nested-tsa-root"
            )

    def test_nested_bundle_tsa_fingerprint_binds_exact_root_der(self):
        with self.assertRaisesRegex(ValueError, "does not bind the exact root DER"):
            valid_context(
                nested_signature_bundle_tsa_root_certificate_der=b"nested-tsa-root",
                nested_signature_bundle_tsa_root_sha256="0" * 64,
                nested_signature_bundle_tsa_policy_oid="1.2.3.4.5",
            )

    def test_nested_bundle_tsa_root_requires_exact_immutable_bytes(self):
        root_der = b"nested-tsa-root"
        with self.assertRaisesRegex(ValueError, "exact immutable DER bytes"):
            valid_context(
                nested_signature_bundle_tsa_root_certificate_der=bytearray(root_der),
                nested_signature_bundle_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
                nested_signature_bundle_tsa_policy_oid="1.2.3.4.5",
            )

    def test_nested_bundle_tsa_policy_oid_must_be_canonical(self):
        root_der = b"nested-tsa-root"
        with self.assertRaisesRegex(ValueError, "canonical numeric dotted text"):
            valid_context(
                nested_signature_bundle_tsa_root_certificate_der=root_der,
                nested_signature_bundle_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
                nested_signature_bundle_tsa_policy_oid="1.02.3",
            )

    def test_nested_bundle_tsa_pin_is_bound_into_provider_context_digest(self):
        base = valid_context()
        root_der = b"nested-tsa-root"
        nested = valid_context(
            nested_signature_bundle_tsa_root_certificate_der=root_der,
            nested_signature_bundle_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
            nested_signature_bundle_tsa_policy_oid="1.2.3.4.5",
        )
        self.assertNotEqual(
            physical_trust_context_sha256(base),
            physical_trust_context_sha256(nested),
        )

    def test_provider_context_copy_preserves_nested_bundle_tsa_pin(self):
        root_der = b"nested-tsa-root"
        context = valid_context(
            nested_signature_bundle_tsa_root_certificate_der=root_der,
            nested_signature_bundle_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
            nested_signature_bundle_tsa_policy_oid="1.2.3.4.5",
            context_generation=1,
        )

        class Provider:
            def read_physical_trust_context(self, *, policy_domain):
                self.asserted_policy_domain = policy_domain
                return context

        provider = Provider()
        snapshot = SimpleNamespace(
            physical_trust_context_generation=context.context_generation,
            physical_trust_context_sha256=physical_trust_context_sha256(context),
            root_public_key_bytes=context.policy_root_public_key_bytes,
            root_key_id=context.policy_root_key_id,
            minimum_policy_sequence=context.minimum_policy_sequence,
        )
        copied, digest = _read_physical_trust_context(provider, snapshot)

        self.assertEqual(provider.asserted_policy_domain, "origen.chispazo.classic.physical")
        self.assertIsNot(copied, context)
        self.assertEqual(
            copied.nested_signature_bundle_tsa_root_certificate_der,
            root_der,
        )
        self.assertEqual(
            copied.nested_signature_bundle_tsa_root_sha256,
            hashlib.sha256(root_der).hexdigest(),
        )
        self.assertEqual(copied.nested_signature_bundle_tsa_policy_oid, "1.2.3.4.5")
        self.assertEqual(digest, physical_trust_context_sha256(context))

    def test_nested_bundle_tsa_root_der_size_is_bounded(self):
        root_der = b"x" * (1_048_576 + 1)
        with self.assertRaisesRegex(ValueError, "within the size limit"):
            valid_context(
                nested_signature_bundle_tsa_root_certificate_der=root_der,
                nested_signature_bundle_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
                nested_signature_bundle_tsa_policy_oid="1.2.3.4.5",
            )


if __name__ == "__main__":
    unittest.main()
