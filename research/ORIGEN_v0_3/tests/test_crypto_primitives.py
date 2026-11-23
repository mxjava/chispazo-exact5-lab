"""Adversarial tests for the low-level Ed25519 primitive (synthetic keys only)."""
from __future__ import annotations

import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.crypto_primitives import verify_ed25519_signature_bytes


class TestEd25519Primitive(unittest.TestCase):
    def setUp(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.message = b"ORIGEN synthetic verifier primitive test"
        self.signature = self.private_key.sign(self.message)

    def test_valid_signature_over_exact_message_is_accepted(self):
        self.assertTrue(
            verify_ed25519_signature_bytes(
                self.public_key, self.message, self.signature
            )
        )

    def test_one_byte_message_change_is_rejected(self):
        self.assertFalse(
            verify_ed25519_signature_bytes(
                self.public_key, self.message + b"!", self.signature
            )
        )

    def test_signature_from_another_key_is_rejected(self):
        other = Ed25519PrivateKey.generate().sign(self.message)
        self.assertFalse(
            verify_ed25519_signature_bytes(self.public_key, self.message, other)
        )

    def test_tampered_signature_is_rejected(self):
        tampered = bytes([self.signature[0] ^ 1]) + self.signature[1:]
        self.assertFalse(
            verify_ed25519_signature_bytes(
                self.public_key, self.message, tampered
            )
        )

    def test_malformed_key_and_signature_lengths_fail_closed(self):
        self.assertFalse(
            verify_ed25519_signature_bytes(b"\x00" * 31, self.message, self.signature)
        )
        self.assertFalse(
            verify_ed25519_signature_bytes(self.public_key, self.message, b"\x00" * 63)
        )

    def test_mutable_and_non_bytes_inputs_are_rejected(self):
        for args in (
            (bytearray(self.public_key), self.message, self.signature),
            (self.public_key, bytearray(self.message), self.signature),
            (self.public_key, self.message, bytearray(self.signature)),
        ):
            with self.subTest(types=tuple(type(item).__name__ for item in args)):
                with self.assertRaisesRegex(TypeError, "exact bytes"):
                    verify_ed25519_signature_bytes(*args)


if __name__ == "__main__":
    unittest.main()
