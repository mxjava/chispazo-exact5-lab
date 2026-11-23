"""Adversarial tests for the fail-closed independent trust boundary."""
from __future__ import annotations

import unittest

from origen.independent_trust_adapter import (
    INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED,
    ProvenanceStatus,
    verify_independent_provenance,
)
from origen.trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES


class TestIndependentTrustAdapter(unittest.TestCase):
    def test_unprovisioned_backend_always_blocks_authentication_looking_bytes(self):
        result = verify_independent_provenance(b'{"status":"AUTHENTICATED"}')
        self.assertIs(result, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(
            INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED,
            "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED",
        )
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)

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

    def test_input_at_shared_receipt_size_limit_remains_fail_closed(self):
        result = verify_independent_provenance(b"x" * MAX_TRUST_RECEIPT_BYTES)
        self.assertIs(result, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_input_one_byte_over_shared_receipt_size_limit_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            f"must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes",
        ):
            verify_independent_provenance(b"x" * (MAX_TRUST_RECEIPT_BYTES + 1))


if __name__ == "__main__":
    unittest.main()
