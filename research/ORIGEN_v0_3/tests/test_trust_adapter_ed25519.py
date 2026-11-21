from __future__ import annotations

import base64
import hashlib
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.trust_adapter import canonical_payload, verify_attestation, verify_artifact_bytes


class Ed25519TrustAdapterTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.roots = {
            "custody-key-01": {
                "public_key_b64": base64.b64encode(public).decode("ascii"),
                "roles": ["CUSTODIAN"],
            }
        }
        self.subject = hashlib.sha256(b"exact sealed portfolio bytes").hexdigest()
        self.envelope = {
            "schema_version": "exact5.attestation.ed25519.v1",
            "key_id": "custody-key-01",
            "role": "CUSTODIAN",
            "subject_sha256": self.subject,
            "issued_at_utc": "2026-11-21T10:00:00Z",
            "expires_at_utc": "2026-11-21T12:00:00Z",
            "nonce": "nonce-value-1234567890",
        }
        self.envelope["signature_b64"] = base64.b64encode(
            self.private.sign(canonical_payload(self.envelope))
        ).decode("ascii")

    def verify(self, envelope=None, roots=None, role="CUSTODIAN", subject=None,
               now="2026-11-21T11:00:00Z"):
        return verify_attestation(
            self.envelope if envelope is None else envelope,
            trust_roots=self.roots if roots is None else roots,
            expected_role=role,
            expected_subject_sha256=subject or self.subject,
            verification_time_utc=now,
        )

    def test_valid_signature_reports_only_pinned_key_assurance(self):
        result = self.verify()
        self.assertEqual(result["status"], "SIGNATURE_VALID")
        self.assertEqual(result["identity_status"], "PINNED_KEY_ONLY")
        self.assertEqual(result["trusted_time_status"], "NOT_ESTABLISHED_BY_THIS_MODULE")
        self.assertEqual(result["custody_status"], "NOT_ESTABLISHED_BY_THIS_MODULE")
        self.assertEqual(result["replay_status"], "NOT_CHECKED_NO_DURABLE_NONCE_LEDGER")


    def test_timestamp_string_subclass_cannot_spoof_valid_utc_time(self):
        class SpoofedTimestamp(str):
            def strip(self, *args, **kwargs):
                return "2026-11-21T10:00:00Z"

            def replace(self, old, new, *args, **kwargs):
                return "2026-11-21T10:00:00+00:00"

        altered = dict(self.envelope)
        altered["issued_at_utc"] = SpoofedTimestamp("attacker-controlled")
        altered["signature_b64"] = base64.b64encode(
            self.private.sign(canonical_payload(altered))
        ).decode("ascii")
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")

    def test_mapping_subclass_cannot_present_different_signed_and_read_values(self):
        class SpoofedEnvelope(dict):
            def __init__(self, stored, presented):
                super().__init__(stored)
                self.presented = presented

            def __getitem__(self, key):
                return self.presented[key]

            def items(self):
                return self.presented.items()

        stored = dict(self.envelope, issued_at_utc="not-a-time")
        presented = dict(self.envelope)
        spoofed = SpoofedEnvelope(stored, presented)
        self.assertEqual(self.verify(envelope=spoofed)["status"], "BLOCKED")

    def test_signature_is_bound_to_exact_original_bytes(self):
        raw = b"exact sealed portfolio bytes"
        result = verify_artifact_bytes(
            self.envelope, raw, trust_roots=self.roots,
            expected_role="CUSTODIAN", verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "SIGNATURE_VALID")
        self.assertEqual(result["byte_integrity_status"], "MATCHED")
        self.assertEqual(result["artifact_byte_length"], len(raw))

    def test_one_byte_change_in_original_artifact_is_rejected(self):
        result = verify_artifact_bytes(
            self.envelope, b"exact sealed portfolio byteS", trust_roots=self.roots,
            expected_role="CUSTODIAN", verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_artifact_must_be_raw_bytes(self):
        result = verify_artifact_bytes(
            self.envelope, "exact sealed portfolio bytes", trust_roots=self.roots,
            expected_role="CUSTODIAN", verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_tampered_payload_is_rejected(self):
        altered = dict(self.envelope, subject_sha256="f" * 64)
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")

    def test_unknown_key_is_rejected(self):
        self.assertEqual(self.verify(roots={})["status"], "BLOCKED")

    def test_wrong_role_is_rejected(self):
        self.assertEqual(self.verify(role="TIMESTAMP_AUTHORITY")["status"], "BLOCKED")

    def test_key_without_role_authorization_is_rejected(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], roles=["SOURCE_SIGNER"])}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_roles_must_be_an_explicit_list(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], roles="CUSTODIAN")}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_revoked_or_disabled_key_is_rejected(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], revoked=True)}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], enabled=False)}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")


    def test_trust_root_rejects_unknown_fields(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], operator_override=True)}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_trust_root_flags_must_be_booleans(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], revoked="false")}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_trust_roots_must_be_mapping(self):
        result = verify_attestation(
            self.envelope, trust_roots=None, expected_role="CUSTODIAN",
            expected_subject_sha256=self.subject, verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_malformed_signature_base64_is_rejected(self):
        altered = dict(self.envelope, signature_b64="not base64!")
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")

    def test_wrong_signature_length_is_rejected(self):
        altered = dict(self.envelope, signature_b64=base64.b64encode(b"short").decode("ascii"))
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")

    def test_malformed_public_key_is_rejected(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], public_key_b64=base64.b64encode(b"short").decode("ascii"))}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_reversed_validity_interval_is_rejected(self):
        altered = dict(self.envelope, issued_at_utc="2026-11-21T12:00:00Z",
                       expires_at_utc="2026-11-21T10:00:00Z")
        altered["signature_b64"] = base64.b64encode(
            self.private.sign(canonical_payload(altered))
        ).decode("ascii")
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")

    def test_wrong_subject_is_rejected(self):
        self.assertEqual(self.verify(subject="e" * 64)["status"], "BLOCKED")

    def test_expired_attestation_is_rejected(self):
        self.assertEqual(self.verify(now="2026-11-22T00:00:00Z")["status"], "BLOCKED")

    def test_naive_verification_time_is_rejected(self):
        self.assertEqual(self.verify(now="2026-11-21T11:00:00")["status"], "BLOCKED")

    def test_signature_is_required_and_exact_schema_is_enforced(self):
        altered = dict(self.envelope)
        altered.pop("signature_b64")
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")

    def test_nonce_is_required(self):
        altered = dict(self.envelope, nonce="short")
        altered["signature_b64"] = base64.b64encode(
            self.private.sign(canonical_payload(altered))
        ).decode("ascii")
        self.assertEqual(self.verify(envelope=altered)["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
