"""Adversarial tests for the fail-closed independent trust boundary."""
from __future__ import annotations

import unittest

from origen.independent_trust_adapter import verify_independent_provenance


class TestIndependentTrustAdapter(unittest.TestCase):
    def test_unprovisioned_backend_always_blocks_even_well_formed_looking_bytes(self):
        result = verify_independent_provenance(b'{"status":"AUTHENTICATED"}')
        self.assertEqual(result.status, "BLOCKED_PROVENANCE")
        self.assertFalse(result.authenticated)
        self.assertEqual(
            result.failure_codes,
            ("INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED",),
        )

    def test_caller_cannot_inject_trust_roots_or_verifier_callbacks(self):
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                b"receipt",
                trust_roots={"self-signed-test-key": b"fake"},
            )
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                b"receipt",
                verifier=lambda *_: True,
            )

    def test_bytes_subclasses_are_not_accepted_at_boundary(self):
        class SpoofedBytes(bytes):
            pass

        with self.assertRaisesRegex(TypeError, "exact bytes"):
            verify_independent_provenance(SpoofedBytes(b"receipt"))

    def test_empty_original_bytes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            verify_independent_provenance(b"")


if __name__ == "__main__":
    unittest.main()
