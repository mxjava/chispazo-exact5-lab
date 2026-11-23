"""Tests for detached envelope verification; trust anchors are synthetic fixtures."""
from __future__ import annotations

import base64
import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.signed_envelope import verify_detached_ed25519_envelope


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class TestDetachedEnvelope(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        self.store = canonical({
            "schema": "origen.trust-store.v1",
            "keys": [{
                "key_id": "test-authority-01",
                "public_key_b64": base64.b64encode(public).decode(),
                "roles": ["evidence_attestor", "custodian"],
                "not_before_utc": "2026-01-01T00:00:00Z",
                "not_after_utc": "2027-01-01T00:00:00Z",
                "revoked": False,
            }],
        })
        self.pin = hashlib.sha256(self.store).hexdigest()
        self.payload = b'{"artifact_sha256":"' + b"a" * 64 + b'"}'
        signed_input = b"ORIGEN-DETACHED-ED25519-ENVELOPE-V1\x00" + canonical({
            "domain": "ORIGEN-DETACHED-ED25519-ENVELOPE-V1",
            "issued_at_utc": "2026-11-23T14:00:00Z",
            "key_id": "test-authority-01",
            "payload_sha256": hashlib.sha256(self.payload).hexdigest(),
            "role": "evidence_attestor",
        })
        self.signature = self.private.sign(signed_input)
        self.envelope = canonical({
            "schema": "origen.detached-ed25519-envelope.v1",
            "key_id": "test-authority-01",
            "role": "evidence_attestor",
            "issued_at_utc": "2026-11-23T14:00:00Z",
            "payload_b64": base64.b64encode(self.payload).decode(),
            "signature_b64": base64.b64encode(self.signature).decode(),
        })

    def verify(self, envelope=None, store=None, pin=None, role="evidence_attestor", at="2026-11-23T15:00:00Z"):
        return verify_detached_ed25519_envelope(
            self.envelope if envelope is None else envelope,
            self.store if store is None else store,
            self.pin if pin is None else pin,
            role,
            at,
        )

    def test_valid_signature_and_authorized_role_returns_exact_payload(self):
        self.assertEqual(self.verify(), self.payload)

    def test_tampered_payload_is_rejected(self):
        env = json.loads(self.envelope)
        env["payload_b64"] = base64.b64encode(self.payload + b"!").decode()
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(envelope=canonical(env))

    def test_role_metadata_is_cryptographically_bound(self):
        env = json.loads(self.envelope)
        env["role"] = "custodian"
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(envelope=canonical(env), role="custodian")

    def test_issued_at_metadata_is_cryptographically_bound(self):
        env = json.loads(self.envelope)
        env["issued_at_utc"] = "2026-11-23T14:30:00Z"
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(envelope=canonical(env))

    def test_wrong_deployment_pin_rejects_trust_store(self):
        with self.assertRaisesRegex(ValueError, "does not match deployment pin"):
            self.verify(pin="0" * 64)

    def test_wrong_role_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "role or key_id"):
            self.verify(role="custodian")

    def test_revoked_key_is_rejected(self):
        store = json.loads(self.store)
        store["keys"][0]["revoked"] = True
        raw = canonical(store)
        with self.assertRaisesRegex(ValueError, "unknown, revoked"):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_inverted_key_validity_window_is_rejected(self):
        store = json.loads(self.store)
        store["keys"][0]["not_before_utc"] = "2027-01-01T00:00:00Z"
        store["keys"][0]["not_after_utc"] = "2026-01-01T00:00:00Z"
        raw = canonical(store)
        with self.assertRaisesRegex(ValueError, "validity window is inverted"):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_malformed_unused_trust_store_key_is_rejected(self):
        store = json.loads(self.store)
        unused = dict(store["keys"][0])
        unused["key_id"] = "unused-authority-02"
        unused["public_key_b64"] = "not-base64!"
        store["keys"].append(unused)
        raw = canonical(store)
        with self.assertRaisesRegex(ValueError, "invalid public-key base64"):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_key_outside_validity_window_is_rejected(self):
        env = json.loads(self.envelope)
        env["issued_at_utc"] = "2025-12-31T23:59:59Z"
        with self.assertRaisesRegex(ValueError, "not valid at envelope issuance"):
            self.verify(envelope=canonical(env))

    def test_future_envelope_is_rejected(self):
        env = json.loads(self.envelope)
        env["issued_at_utc"] = "2026-12-01T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "from the future"):
            self.verify(envelope=canonical(env))

    def test_noncanonical_envelope_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "canonical JSON"):
            self.verify(envelope=b'{ "schema": "wrong" }')

    def test_duplicate_trust_store_key_ids_are_rejected(self):
        store = json.loads(self.store)
        store["keys"].append(dict(store["keys"][0]))
        raw = canonical(store)
        with self.assertRaisesRegex(ValueError, "duplicated"):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_same_public_key_cannot_be_registered_under_distinct_key_ids(self):
        store = json.loads(self.store)
        alias = dict(store["keys"][0])
        alias["key_id"] = "test-authority-alias-02"
        store["keys"].append(alias)
        raw = canonical(store)
        with self.assertRaisesRegex(
            ValueError,
            "public key bytes must not be aliased across key IDs",
        ):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_duplicate_json_object_keys_are_rejected(self):
        raw = b'{"keys":[],"schema":"origen.trust-store.v1","schema":"origen.trust-store.v1"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_oversized_envelope_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1 MiB limit"):
            self.verify(envelope=b" " * 1048577)

    def test_oversized_trust_store_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "1 MiB limit"):
            self.verify(store=b" " * 1048577)

    def test_nonstandard_json_nan_constant_is_rejected(self):
        raw = b'{"keys":[],"schema":"origen.trust-store.v1","unused":NaN}'
        with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
            self.verify(store=raw, pin=hashlib.sha256(raw).hexdigest())

    def test_timestamp_with_more_than_six_fractional_digits_is_rejected(self):
        env = json.loads(self.envelope)
        env["issued_at_utc"] = "2026-11-23T14:00:00.1234567Z"
        with self.assertRaisesRegex(ValueError, "canonical RFC3339"):
            self.verify(envelope=canonical(env))

    def test_noncanonical_base64_is_rejected(self):
        env = json.loads(self.envelope)
        env["payload_b64"] = env["payload_b64"].rstrip("=")
        with self.assertRaisesRegex(ValueError, "invalid base64"):
            self.verify(envelope=canonical(env))

    def test_excessive_json_nesting_is_rejected_before_recursive_decode(self):
        nested = b"[" * 17 + b"0" + b"]" * 17
        with self.assertRaisesRegex(ValueError, "maximum JSON nesting depth 16"):
            self.verify(envelope=nested)

    def test_signature_from_untrusted_key_is_rejected(self):
        other = Ed25519PrivateKey.generate().sign(self.payload)
        env = json.loads(self.envelope)
        env["signature_b64"] = base64.b64encode(other).decode()
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(envelope=canonical(env))


if __name__ == "__main__":
    unittest.main()
