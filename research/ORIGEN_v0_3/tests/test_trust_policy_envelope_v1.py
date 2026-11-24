"""Adversarial tests for externally anchored signed trust-policy envelopes."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.trust_policy_envelope_v1 import (
    SCHEMA_VERSION,
    verify_signed_trust_policy,
)

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def fixture():
    root = Ed25519PrivateKey.generate()
    issuer = Ed25519PrivateKey.generate()
    issuer_public = issuer.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "policy-2026-11",
        "policy_sequence": 7,
        "issuer_id": "policy-authority",
        "root_key_id": "offline-root-2026",
        "issued_at_utc": "2026-11-24T10:00:00Z",
        "not_before_utc": "2026-11-24T11:00:00Z",
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
    payload = dict(document)
    payload.pop("signature")
    document["signature"]["signature_b64"] = base64.b64encode(
        root.sign(canonical(payload))
    ).decode("ascii")
    root_public = root.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return canonical(document), root_public, document


class TestSignedTrustPolicyEnvelopeV1(unittest.TestCase):
    def verify(self, raw, root_public, **kwargs):
        defaults = {
            "pinned_root_public_key_bytes": root_public,
            "expected_root_key_id": "offline-root-2026",
            "minimum_policy_sequence": 7,
            "verification_time": NOW,
        }
        defaults.update(kwargs)
        return verify_signed_trust_policy(raw, **defaults)

    def test_valid_policy_verifies_against_pinned_root(self):
        raw, root_public, _ = fixture()
        result = self.verify(raw, root_public)
        self.assertEqual(result.policy.policy_version, "policy-2026-11")
        self.assertEqual(result.policy_sequence, 7)
        self.assertEqual(result.root_key_id, "offline-root-2026")
        self.assertEqual(result.policy.issuer_keys[0].issuer_id, "independent-verifier")
        self.assertFalse(result.policy.issuer_keys[0].revoked)
        self.assertEqual(len(result.envelope_sha256), 64)

    def test_tampered_policy_claim_fails_signature(self):
        raw, root_public, document = fixture()
        document["issuer_keys"][0]["revoked"] = True
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(canonical(document), root_public)

    def test_wrong_pinned_root_fails_signature(self):
        raw, _, _ = fixture()
        attacker = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(raw, attacker)

    def test_root_key_identifier_must_match_deployment_pin(self):
        raw, root_public, _ = fixture()
        with self.assertRaisesRegex(ValueError, "does not match pinned"):
            self.verify(raw, root_public, expected_root_key_id="other-root")

    def test_policy_sequence_rollback_is_rejected(self):
        raw, root_public, _ = fixture()
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.verify(raw, root_public, minimum_policy_sequence=8)

    def test_policy_not_yet_valid_is_rejected(self):
        raw, root_public, _ = fixture()
        before = datetime(2026, 11, 24, 10, 30, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "not currently valid"):
            self.verify(raw, root_public, verification_time=before)

    def test_expired_policy_is_rejected(self):
        raw, root_public, _ = fixture()
        after = datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "not currently valid"):
            self.verify(raw, root_public, verification_time=after)

    def test_duplicate_json_keys_are_rejected(self):
        raw, root_public, _ = fixture()
        duplicate = raw[:-1] + b',"policy_sequence":7}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            self.verify(duplicate, root_public)

    def test_noncanonical_base64_is_rejected(self):
        raw, root_public, document = fixture()
        document["issuer_keys"][0]["public_key_b64"] += "="
        with self.assertRaisesRegex(ValueError, "valid base64|canonical base64"):
            self.verify(canonical(document), root_public)

    def test_duplicate_issuer_key_identity_is_rejected_before_signature(self):
        raw, root_public, document = fixture()
        document["issuer_keys"].append(copy.deepcopy(document["issuer_keys"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate issuer/key"):
            self.verify(canonical(document), root_public)

    def test_public_key_reuse_is_rejected(self):
        raw, root_public, document = fixture()
        alias = copy.deepcopy(document["issuer_keys"][0])
        alias["issuer_id"] = "second-verifier"
        alias["key_id"] = "different-key"
        document["issuer_keys"].append(alias)
        with self.assertRaisesRegex(ValueError, "public key reused"):
            self.verify(canonical(document), root_public)

    def test_revocation_flag_must_be_exact_boolean(self):
        raw, root_public, document = fixture()
        document["issuer_keys"][0]["revoked"] = 1
        with self.assertRaisesRegex(ValueError, "exact boolean"):
            self.verify(canonical(document), root_public)

    def test_unknown_fields_are_rejected(self):
        raw, root_public, document = fixture()
        document["trust_me"] = True
        with self.assertRaisesRegex(ValueError, "fields mismatch"):
            self.verify(canonical(document), root_public)

    def test_oversized_envelope_is_rejected(self):
        raw, root_public, _ = fixture()
        with self.assertRaisesRegex(ValueError, "size limit"):
            self.verify(b"x" * 131073, root_public)

    def test_root_key_must_be_immutable_exact_bytes(self):
        raw, root_public, _ = fixture()
        with self.assertRaisesRegex(ValueError, "32 immutable bytes"):
            self.verify(raw, bytearray(root_public))


    def test_excessive_json_nesting_is_rejected_before_decode(self):
        raw, root_public, _ = fixture()
        deeply_nested = b"[" * 33 + b"]" * 33
        with self.assertRaisesRegex(ValueError, "maximum JSON nesting depth"):
            self.verify(deeply_nested, root_public)

    def test_policy_sequence_outside_signed_64_bit_range_is_rejected(self):
        raw, root_public, document = fixture()
        document["policy_sequence"] = 9223372036854775808
        with self.assertRaisesRegex(ValueError, "signed 64-bit range"):
            self.verify(canonical(document), root_public)

    def test_issue_time_after_not_before_is_rejected(self):
        raw, root_public, document = fixture()
        document["issued_at_utc"] = "2026-11-24T11:30:00Z"
        document["not_before_utc"] = "2026-11-24T11:00:00Z"
        with self.assertRaisesRegex(ValueError, "validity chronology is inverted"):
            self.verify(canonical(document), root_public)

    def test_non_utc_timestamp_form_is_rejected(self):
        raw, root_public, document = fixture()
        document["expires_at_utc"] = "2026-12-01T00:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "canonical UTC timestamp"):
            self.verify(canonical(document), root_public)


if __name__ == "__main__":
    unittest.main()
