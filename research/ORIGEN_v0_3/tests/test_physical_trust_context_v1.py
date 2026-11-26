"""Synthetic validation of provider-owned physical trust context."""
from __future__ import annotations

import hashlib
import unittest

from origen.physical_trust_context_v1 import PhysicalTrustContextV1


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


if __name__ == "__main__":
    unittest.main()
