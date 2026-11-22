from __future__ import annotations

import base64
import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.trust_adapter import (canonical_payload, parse_attestation_json, verify_attestation, verify_attestation_json, verify_artifact_bytes)


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
                "enabled": True,
                "revoked": False,
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

    def test_noncanonical_public_key_base64_pad_bits_are_rejected(self):
        encoded = self.roots["custody-key-01"]["public_key_b64"]
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        index = alphabet.index(encoded[-2])
        alternate = encoded[:-2] + alphabet[index + 1] + "="
        self.assertNotEqual(alternate, encoded)
        self.assertEqual(
            base64.b64decode(alternate, validate=True),
            base64.b64decode(encoded, validate=True),
        )
        roots = {
            "custody-key-01": dict(
                self.roots["custody-key-01"], public_key_b64=alternate
            )
        }
        result = self.verify(roots=roots)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("non-canonical base64", result["reason"])

    def test_noncanonical_signature_base64_pad_bits_are_rejected(self):
        encoded = self.envelope["signature_b64"]
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        # A 64-byte Ed25519 signature ends with two '=' padding bytes;
        # the final data symbol is therefore at -3 (not -2).
        index = alphabet.index(encoded[-3])
        alternate = encoded[:-3] + alphabet[index + 1] + "=="
        self.assertNotEqual(alternate, encoded)
        self.assertEqual(
            base64.b64decode(alternate, validate=True),
            base64.b64decode(encoded, validate=True),
        )
        altered = dict(self.envelope, signature_b64=alternate)
        result = self.verify(envelope=altered)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("non-canonical base64", result["reason"])

    def test_canonical_json_envelope_is_parsed_and_verified(self):
        raw = json.dumps(
            self.envelope, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(parse_attestation_json(raw), self.envelope)
        result = verify_attestation_json(
            raw, trust_roots=self.roots, expected_role="CUSTODIAN",
            expected_subject_sha256=self.subject,
            verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "SIGNATURE_VALID")

    def test_duplicate_json_member_is_rejected_before_last_value_wins(self):
        canonical = json.dumps(
            self.envelope, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        )
        needle = '"schema_version":"exact5.attestation.ed25519.v1"'
        self.assertIn(needle, canonical)
        duplicated = canonical.replace(
            needle,
            '"schema_version":"attacker","schema_version":"exact5.attestation.ed25519.v1"',
            1,
        ).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_attestation_json(duplicated)
        result = verify_attestation_json(
            duplicated, trust_roots=self.roots, expected_role="CUSTODIAN",
            expected_subject_sha256=self.subject,
            verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("duplicate JSON object key", result["reason"])

    def test_noncanonical_json_whitespace_and_trailing_lf_are_rejected(self):
        spaced = json.dumps(self.envelope).encode("utf-8")
        canonical = json.dumps(
            self.envelope, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        for raw in (spaced, canonical + b"\n"):
            with self.subTest(raw=raw[-8:]):
                with self.assertRaisesRegex(ValueError, "canonical UTF-8 JSON"):
                    parse_attestation_json(raw)

    def test_attestation_json_bytes_subclass_is_rejected(self):
        class SpoofedBytes(bytes):
            pass

        with self.assertRaisesRegex(ValueError, "exact built-in bytes"):
            parse_attestation_json(SpoofedBytes(b"{}"))

    def test_attestation_json_must_be_an_object(self):
        with self.assertRaisesRegex(ValueError, "exact built-in object"):
            parse_attestation_json(b"[]")

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


    def test_noncanonical_utc_forms_are_rejected_even_when_signed(self):
        invalid_values = (
            "2026-11-21 10:00:00Z",
            "2026-11-21T10:00Z",
            "2026-11-21T10:00:00+0000",
            "2026-11-21T10:00:00Z ",
        )
        for value in invalid_values:
            with self.subTest(value=value):
                altered = dict(self.envelope, issued_at_utc=value)
                altered["signature_b64"] = base64.b64encode(
                    self.private.sign(canonical_payload(altered))
                ).decode("ascii")
                result = self.verify(envelope=altered)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("canonical extended ISO-8601 UTC", result["reason"])

    def test_canonical_explicit_utc_offset_is_accepted(self):
        altered = dict(
            self.envelope,
            issued_at_utc="2026-11-21T10:00:00+00:00",
            expires_at_utc="2026-11-21T12:00:00+00:00",
        )
        altered["signature_b64"] = base64.b64encode(
            self.private.sign(canonical_payload(altered))
        ).decode("ascii")
        self.assertEqual(self.verify(envelope=altered)["status"], "SIGNATURE_VALID")

    def test_artifact_bytes_subclass_is_rejected(self):
        class SpoofedBytes(bytes):
            def __len__(self):
                return 1

        result = verify_artifact_bytes(
            self.envelope, SpoofedBytes(b"exact sealed portfolio bytes"),
            trust_roots=self.roots, expected_role="CUSTODIAN",
            verification_time_utc="2026-11-21T11:00:00Z",
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("exact built-in raw bytes", result["reason"])

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

    def test_trust_root_requires_explicit_enabled_and_revoked_state(self):
        for field in ("enabled", "revoked"):
            with self.subTest(field=field):
                roots = {"custody-key-01": dict(self.roots["custody-key-01"])}
                roots["custody-key-01"].pop(field)
                self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_trust_root_flags_must_be_booleans(self):
        roots = {"custody-key-01": dict(self.roots["custody-key-01"], revoked="false")}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_trust_root_identifier_string_subclass_is_rejected(self):
        class SpoofedKeyId(str):
            def __hash__(self):
                return hash("custody-key-01")

            def __eq__(self, other):
                return other == "custody-key-01"

        roots = {SpoofedKeyId("attacker-key"): self.roots["custody-key-01"]}
        self.assertEqual(self.verify(roots=roots)["status"], "BLOCKED")

    def test_trust_root_field_name_string_subclass_is_rejected(self):
        class SpoofedField(str):
            def __hash__(self):
                return hash("enabled")

            def __eq__(self, other):
                return other == "enabled"

        root = dict(self.roots["custody-key-01"])
        root[SpoofedField("attacker-field")] = root.pop("enabled")
        roots = {"custody-key-01": root}
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

    def test_nonce_rejects_whitespace_control_unicode_and_oversized_values(self):
        invalid_nonces = (
            "                ",
            "nonce with spaces",
            "nonce\nvalue_123456",
            "nonce-é-value-123",
            "n" * 129,
        )
        for nonce in invalid_nonces:
            with self.subTest(nonce=repr(nonce)):
                altered = dict(self.envelope, nonce=nonce)
                altered["signature_b64"] = base64.b64encode(
                    self.private.sign(canonical_payload(altered))
                ).decode("ascii")
                result = self.verify(envelope=altered)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn("nonce must be 16-128 ASCII URL-safe characters", result["reason"])

    def test_nonce_accepts_url_safe_ascii(self):
        altered = dict(self.envelope, nonce="nonce_value-1234567890")
        altered["signature_b64"] = base64.b64encode(
            self.private.sign(canonical_payload(altered))
        ).decode("ascii")
        self.assertEqual(self.verify(envelope=altered)["status"], "SIGNATURE_VALID")


if __name__ == "__main__":
    unittest.main()
