"""Adversarial tests for the research-only policy/receipt trust chain."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from origen.trust_chain_v1 import (
    VerifiedReceiptTrustChain,
    verify_receipt_trust_chain,
)
from origen.trust_policy_envelope_v1 import SCHEMA_VERSION
from test_trust_receipt_v1 import encode, valid_document


NOW = datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc)
ROOT_KEY_ID = "offline-root-2026"
POLICY_SEQUENCE = 9


def canonical(document: dict) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def raw_public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def signed_fixture(*, policy_version: str = "policy-2026-11"):
    root_private = Ed25519PrivateKey.generate()
    issuer_private = Ed25519PrivateKey.generate()
    issuer_public = raw_public_key(issuer_private)

    policy_document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": policy_version,
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-23T00:00:00Z",
        "not_before_utc": "2026-11-23T00:00:00Z",
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
    unsigned_policy = copy.deepcopy(policy_document)
    unsigned_policy.pop("signature")
    policy_document["signature"]["signature_b64"] = base64.b64encode(
        root_private.sign(canonical(unsigned_policy))
    ).decode("ascii")
    raw_policy = canonical(policy_document)

    receipt_document = valid_document()
    receipt_document["receipt_attestation"]["issuer_id"] = "independent-verifier"
    receipt_document["receipt_attestation"]["key_id"] = "verifier-key-1"
    receipt_document["receipt_attestation"]["algorithm"] = "ed25519"
    receipt_document["receipt_attestation"]["signed_at_utc"] = "2026-11-23T03:05:00Z"
    receipt_document["receipt_attestation"]["signature_b64"] = ""
    unsigned_receipt = copy.deepcopy(receipt_document)
    unsigned_receipt["receipt_attestation"].pop("signature_b64")
    receipt_document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        issuer_private.sign(canonical(unsigned_receipt))
    ).decode("ascii")
    raw_receipt = encode(receipt_document)

    return raw_policy, raw_receipt, raw_public_key(root_private)


class ChangingOffset(tzinfo):
    """Adversarial tzinfo whose offset changes after the first observation."""

    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=0 if self.calls == 1 else 8)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "changing-offset"


class TestTrustChainV1(unittest.TestCase):
    def verify(self, raw_policy, raw_receipt, root_public, **overrides):
        args = {
            "pinned_root_public_key_bytes": root_public,
            "expected_root_key_id": ROOT_KEY_ID,
            "minimum_policy_sequence": POLICY_SEQUENCE,
            "verification_time": NOW,
        }
        args.update(overrides)
        return verify_receipt_trust_chain(
            raw_policy, raw_receipt, **args
        )

    def test_valid_chain_binds_policy_and_receipt_bytes(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        result = self.verify(raw_policy, raw_receipt, root_public)

        self.assertIsInstance(result, VerifiedReceiptTrustChain)
        self.assertEqual(
            result.policy_envelope_sha256,
            hashlib.sha256(raw_policy).hexdigest(),
        )
        self.assertEqual(
            result.receipt_bytes_sha256,
            hashlib.sha256(raw_receipt).hexdigest(),
        )
        self.assertEqual(result.verified_policy.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.verified_policy.root_key_id, ROOT_KEY_ID)
        self.assertEqual(
            result.verified_receipt.verified_issuer_id,
            "independent-verifier",
        )
        self.assertEqual(
            result.verified_receipt.verified_key_id,
            "verifier-key-1",
        )
        self.assertEqual(result.verified_at_utc, NOW)

    def test_policy_tampering_fails_before_receipt_verification(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        document = json.loads(raw_policy)
        document["issuer_keys"][0]["revoked"] = True
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(canonical(document), raw_receipt, root_public)

    def test_wrong_root_anchor_rejects_policy(self):
        raw_policy, raw_receipt, _ = signed_fixture()
        attacker_root = Ed25519PrivateKey.generate()
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.verify(raw_policy, raw_receipt, raw_public_key(attacker_root))

    def test_external_minimum_sequence_rejects_rollback(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.verify(
                raw_policy,
                raw_receipt,
                root_public,
                minimum_policy_sequence=POLICY_SEQUENCE + 1,
            )

    def test_receipt_tampering_fails_root_attestation(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        document = json.loads(raw_receipt)
        document["artifacts"][0]["sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(raw_policy, encode(document), root_public)

    def test_receipt_policy_version_must_match_signed_envelope(self):
        raw_policy, raw_receipt, root_public = signed_fixture(
            policy_version="policy-2026-12"
        )
        with self.assertRaisesRegex(ValueError, "policy_version does not match"):
            self.verify(raw_policy, raw_receipt, root_public)

    def test_verification_time_offset_is_snapshotted_once_across_both_verifiers(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        changing_zone = ChangingOffset()
        supplied_time = datetime(2026, 11, 23, 4, 0, tzinfo=changing_zone)

        result = self.verify(
            raw_policy,
            raw_receipt,
            root_public,
            verification_time=supplied_time,
        )

        self.assertEqual(changing_zone.calls, 1)
        self.assertEqual(
            result.verified_at_utc,
            datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc),
        )

    def test_verified_chain_does_not_unblock_independent_provenance_adapter(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        self.verify(raw_policy, raw_receipt, root_public)

        status = verify_independent_provenance(raw_receipt)
        self.assertIs(status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)

    def test_result_cannot_be_constructed_through_public_initializer(self):
        with self.assertRaisesRegex(
            TypeError, "created only by verify_receipt_trust_chain"
        ):
            VerifiedReceiptTrustChain(None, None, None, None, None)

    def test_raw_inputs_require_exact_immutable_bytes(self):
        raw_policy, raw_receipt, root_public = signed_fixture()
        with self.assertRaisesRegex(TypeError, "raw_policy_envelope must be exact bytes"):
            verify_receipt_trust_chain(
                bytearray(raw_policy),
                raw_receipt,
                pinned_root_public_key_bytes=root_public,
                expected_root_key_id=ROOT_KEY_ID,
                minimum_policy_sequence=POLICY_SEQUENCE,
                verification_time=NOW,
            )
        with self.assertRaisesRegex(TypeError, "raw_receipt must be exact bytes"):
            verify_receipt_trust_chain(
                raw_policy,
                bytearray(raw_receipt),
                pinned_root_public_key_bytes=root_public,
                expected_root_key_id=ROOT_KEY_ID,
                minimum_policy_sequence=POLICY_SEQUENCE,
                verification_time=NOW,
            )


if __name__ == "__main__":
    unittest.main()
