"""Canonical-byte binding tests for signed trust-policy envelopes (synthetic keys only)."""
from __future__ import annotations

import json
import unittest

from origen.trust_policy_envelope_v1 import verify_signed_trust_policy
from test_trust_policy_envelope_v1 import NOW, fixture


class TestSignedTrustPolicyCanonicalBytesV1(unittest.TestCase):
    def verify(self, raw: bytes, root_public: bytes):
        return verify_signed_trust_policy(
            raw,
            pinned_root_public_key_bytes=root_public,
            expected_root_key_id="offline-root-2026",
            minimum_policy_sequence=7,
            verification_time=NOW,
        )

    def test_original_canonical_envelope_is_accepted(self):
        raw, root_public, _ = fixture()
        result = self.verify(raw, root_public)
        self.assertEqual(result.policy_sequence, 7)

    def test_whitespace_variants_are_rejected_even_when_signature_is_unchanged(self):
        raw, root_public, _ = fixture()
        variants = (b" " + raw, raw + bytes((10,)), bytes((10,)) + raw)
        for variant in variants:
            with self.subTest(prefix=variant[:8], suffix=variant[-8:]):
                with self.assertRaisesRegex(
                    ValueError, "canonical UTF-8 encoding"
                ):
                    self.verify(variant, root_public)

    def test_reordered_object_members_are_rejected(self):
        raw, root_public, document = fixture()
        reordered = json.dumps(
            document, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        self.assertNotEqual(reordered, raw)
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            self.verify(reordered, root_public)

    def test_equivalent_unicode_escape_is_rejected(self):
        raw, root_public, _ = fixture()
        alternate = raw.replace(
            b"policy_version", b"policy_versi\\u006fn", 1
        )
        self.assertNotEqual(alternate, raw)
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            self.verify(alternate, root_public)


if __name__ == "__main__":
    unittest.main()
