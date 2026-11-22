"""Tests for root Ed25519 attestation verification (synthetic keys only)."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.trust_receipt_v1 import parse_unverified_receipt
from origen.trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    TrustPolicy,
    TrustedIssuerKey,
    canonical_attestation_payload,
    verify_receipt_attestation,
)
from test_trust_receipt_v1 import encode, valid_document


NOW = datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc)
VALID_FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)
VALID_UNTIL = datetime(2027, 1, 1, tzinfo=timezone.utc)


def signed_receipt():
    private_key = Ed25519PrivateKey.generate()
    document = valid_document()
    unsigned = copy.deepcopy(document)
    unsigned.pop("receipt_attestation")
    payload = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        private_key.sign(payload)
    ).decode("ascii")
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return encode(document), public_bytes


def policy(public_bytes, *, revoked=False, key_id="verifier-key-1"):
    return TrustPolicy(
        policy_version="policy-2026-11",
        issuer_keys=(
            TrustedIssuerKey(
                issuer_id="independent-verifier",
                key_id=key_id,
                public_key_bytes=public_bytes,
                valid_from_utc=VALID_FROM,
                valid_until_utc=VALID_UNTIL,
                revoked=revoked,
            ),
        ),
    )


class TestTrustVerifierV1(unittest.TestCase):
    def test_valid_root_attestation_returns_scoped_verified_type(self):
        raw, public_bytes = signed_receipt()
        result = verify_receipt_attestation(
            raw, policy(public_bytes), verification_time=NOW
        )
        self.assertIsInstance(result, CryptographicallyVerifiedReceipt)
        self.assertEqual(result.verified_issuer_id, "independent-verifier")
        self.assertEqual(result.verified_key_id, "verifier-key-1")
        self.assertEqual(result.receipt.target.contest_id, "12389")
        self.assertEqual(len(result.signed_payload_sha256), 64)

    def test_tampered_claim_is_rejected(self):
        raw, public_bytes = signed_receipt()
        document = json.loads(raw)
        document["artifacts"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            verify_receipt_attestation(
                encode(document), policy(public_bytes), verification_time=NOW
            )

    def test_unknown_key_is_rejected(self):
        raw, public_bytes = signed_receipt()
        with self.assertRaisesRegex(ValueError, "unknown or ambiguous"):
            verify_receipt_attestation(
                raw, policy(public_bytes, key_id="other-key"), verification_time=NOW
            )

    def test_revoked_key_is_rejected(self):
        raw, public_bytes = signed_receipt()
        with self.assertRaisesRegex(ValueError, "revoked"):
            verify_receipt_attestation(
                raw, policy(public_bytes, revoked=True), verification_time=NOW
            )

    def test_key_outside_validity_interval_is_rejected(self):
        raw, public_bytes = signed_receipt()
        too_early = datetime(2025, 12, 31, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "outside its policy validity"):
            verify_receipt_attestation(
                raw, policy(public_bytes), verification_time=too_early
            )

    def test_inverted_key_validity_interval_is_rejected(self):
        raw, public_bytes = signed_receipt()
        malformed = TrustPolicy(
            policy_version="policy-2026-11",
            issuer_keys=(
                TrustedIssuerKey(
                    issuer_id="independent-verifier",
                    key_id="verifier-key-1",
                    public_key_bytes=public_bytes,
                    valid_from_utc=VALID_UNTIL,
                    valid_until_utc=VALID_FROM,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "validity interval is inverted"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_signed_at_outside_key_validity_is_rejected(self):
        raw, public_bytes = signed_receipt()
        trust = TrustPolicy(
            policy_version="policy-2026-11",
            issuer_keys=(
                TrustedIssuerKey(
                    issuer_id="independent-verifier",
                    key_id="verifier-key-1",
                    public_key_bytes=public_bytes,
                    valid_from_utc=datetime(2026, 11, 23, 3, 30, tzinfo=timezone.utc),
                    valid_until_utc=VALID_UNTIL,
                ),
            ),
        )
        with self.assertRaisesRegex(ValueError, "signing time is outside"):
            verify_receipt_attestation(raw, trust, verification_time=NOW)

    def test_signed_at_after_verification_time_is_rejected(self):
        raw, public_bytes = signed_receipt()
        earlier = datetime(2026, 11, 23, 3, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "after verification time"):
            verify_receipt_attestation(
                raw, policy(public_bytes), verification_time=earlier
            )

    def test_policy_rejects_list_instead_of_exact_tuple(self):
        raw, public_bytes = signed_receipt()
        valid = policy(public_bytes)
        malformed = TrustPolicy(
            policy_version=valid.policy_version,
            issuer_keys=list(valid.issuer_keys),
        )
        with self.assertRaisesRegex(ValueError, "exact tuple"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_rejects_mutable_public_key_bytes(self):
        raw, public_bytes = signed_receipt()
        malformed_key = TrustedIssuerKey(
            issuer_id="independent-verifier",
            key_id="verifier-key-1",
            public_key_bytes=bytearray(public_bytes),
            valid_from_utc=VALID_FROM,
            valid_until_utc=VALID_UNTIL,
        )
        malformed = TrustPolicy("policy-2026-11", (malformed_key,))
        with self.assertRaisesRegex(ValueError, "32 immutable bytes"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_rejects_non_boolean_revocation_flag(self):
        raw, public_bytes = signed_receipt()
        malformed_key = TrustedIssuerKey(
            issuer_id="independent-verifier",
            key_id="verifier-key-1",
            public_key_bytes=public_bytes,
            valid_from_utc=VALID_FROM,
            valid_until_utc=VALID_UNTIL,
            revoked=1,
        )
        malformed = TrustPolicy("policy-2026-11", (malformed_key,))
        with self.assertRaisesRegex(ValueError, "exact boolean"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_rejects_duplicate_issuer_key_pairs(self):
        raw, public_bytes = signed_receipt()
        key = policy(public_bytes).issuer_keys[0]
        malformed = TrustPolicy("policy-2026-11", (key, key))
        with self.assertRaisesRegex(ValueError, "duplicate issuer/key"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_rejects_noncanonical_issuer_identifier(self):
        raw, public_bytes = signed_receipt()
        malformed_key = TrustedIssuerKey(
            issuer_id=" independent-verifier",
            key_id="verifier-key-1",
            public_key_bytes=public_bytes,
            valid_from_utc=VALID_FROM,
            valid_until_utc=VALID_UNTIL,
        )
        malformed = TrustPolicy("policy-2026-11", (malformed_key,))
        with self.assertRaisesRegex(ValueError, "canonical policy identifier"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_rejects_naive_validity_bound(self):
        raw, public_bytes = signed_receipt()
        malformed_key = TrustedIssuerKey(
            issuer_id="independent-verifier",
            key_id="verifier-key-1",
            public_key_bytes=public_bytes,
            valid_from_utc=datetime(2026, 1, 1),
            valid_until_utc=VALID_UNTIL,
        )
        malformed = TrustPolicy("policy-2026-11", (malformed_key,))
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_issuer_key_collection_is_bounded(self):
        raw, public_bytes = signed_receipt()
        malformed = TrustPolicy(
            "policy-2026-11",
            tuple(
                TrustedIssuerKey(
                    issuer_id=f"issuer-{index}",
                    key_id=f"key-{index}",
                    public_key_bytes=public_bytes,
                    valid_from_utc=VALID_FROM,
                    valid_until_utc=VALID_UNTIL,
                )
                for index in range(257)
            ),
        )
        with self.assertRaisesRegex(ValueError, r"1..256 entries"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_policy_subclass_is_rejected(self):
        raw, public_bytes = signed_receipt()

        class PolicySubclass(TrustPolicy):
            pass

        valid = policy(public_bytes)
        malformed = PolicySubclass(valid.policy_version, valid.issuer_keys)
        with self.assertRaisesRegex(ValueError, "exact TrustPolicy"):
            verify_receipt_attestation(raw, malformed, verification_time=NOW)

    def test_bytes_subclass_receipt_is_rejected(self):
        raw, public_bytes = signed_receipt()

        class ReceiptBytes(bytes):
            pass

        with self.assertRaisesRegex(TypeError, "exact bytes"):
            verify_receipt_attestation(
                ReceiptBytes(raw), policy(public_bytes), verification_time=NOW
            )

    def test_datetime_subclass_verification_clock_is_rejected(self):
        raw, public_bytes = signed_receipt()

        class ClockSubclass(datetime):
            pass

        clock = ClockSubclass(2026, 11, 23, 4, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "exact datetime"):
            verify_receipt_attestation(raw, policy(public_bytes), verification_time=clock)

    def test_policy_version_mismatch_is_rejected(self):
        raw, public_bytes = signed_receipt()
        trust = TrustPolicy(policy_version="wrong-policy", issuer_keys=policy(public_bytes).issuer_keys)
        with self.assertRaisesRegex(ValueError, "does not match"):
            verify_receipt_attestation(raw, trust, verification_time=NOW)

    def test_naive_verification_clock_is_rejected(self):
        raw, public_bytes = signed_receipt()
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            verify_receipt_attestation(
                raw, policy(public_bytes), verification_time=datetime(2026, 11, 23)
            )

    def test_unverified_parser_never_upgrades_receipt_by_itself(self):
        raw, _ = signed_receipt()
        parsed = parse_unverified_receipt(raw)
        self.assertEqual(parsed.declared_status, "AUTHENTICATED")
        self.assertNotIsInstance(parsed, CryptographicallyVerifiedReceipt)

    def test_declared_rejected_receipt_is_not_verified(self):
        raw, public_bytes = signed_receipt()
        document = json.loads(raw)
        document["status"] = "REJECTED"
        document["failure_codes"] = ["TEST_REJECTED"]
        unsigned = copy.deepcopy(document)
        unsigned.pop("receipt_attestation")
        payload = json.dumps(
            unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        private_key = Ed25519PrivateKey.generate()
        # A rejected declaration must fail before signature verification; its
        # signature is intentionally not made valid for the supplied key.
        with self.assertRaisesRegex(ValueError, "declaration is REJECTED"):
            verify_receipt_attestation(
                encode(document), policy(public_bytes), verification_time=NOW
            )


if __name__ == "__main__":
    unittest.main()
