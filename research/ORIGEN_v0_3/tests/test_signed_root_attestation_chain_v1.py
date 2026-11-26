"""Synthetic adversarial tests for the V1 fail-closed trust-chain composition."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from origen.signed_root_attestation_chain_v1 import (
    inspect_signed_root_attestation_chain_v1,
)
from origen.trust_policy_envelope_v1 import (
    SCHEMA_VERSION,
    VerifiedTrustPolicy,
    verify_signed_trust_policy,
)
from test_trust_receipt_v1 import encode
from test_trust_verifier_v1 import NOW, signed_receipt


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _signed_policy(issuer_public_key_bytes):
    root = Ed25519PrivateKey.generate()
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "policy-2026-11",
        "policy_sequence": 7,
        "issuer_id": "policy-authority",
        "root_key_id": "offline-root-2026",
        "issued_at_utc": "2026-11-23T02:00:00Z",
        "not_before_utc": "2026-11-23T03:00:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": [{
            "issuer_id": "independent-verifier",
            "key_id": "verifier-key-1",
            "public_key_b64": base64.b64encode(
                issuer_public_key_bytes
            ).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
        }],
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = copy.deepcopy(document)
    unsigned.pop("signature")
    document["signature"]["signature_b64"] = base64.b64encode(
        root.sign(_canonical(unsigned))
    ).decode("ascii")
    root_public = root.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _canonical(document), root_public


class _OneShotUTC(tzinfo):
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("timezone callback invoked more than once")
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)


class TestSignedRootAttestationChainV1(unittest.TestCase):
    def setUp(self):
        self.receipt_bytes, self.issuer_public_key, _ = signed_receipt()
        self.policy_bytes, self.root_public_key = _signed_policy(
            self.issuer_public_key
        )

    def inspect(self, **overrides):
        args = {
            "original_receipt_bytes": self.receipt_bytes,
            "signed_policy_envelope_bytes": self.policy_bytes,
            "pinned_root_public_key_bytes": self.root_public_key,
            "expected_root_key_id": "offline-root-2026",
            "minimum_policy_sequence": 7,
            "verification_time": NOW,
        }
        args.update(overrides)
        return inspect_signed_root_attestation_chain_v1(**args)

    def test_signed_policy_and_receipt_are_composed_but_provenance_stays_blocked(self):
        result = self.inspect()
        self.assertEqual(result.policy_sequence, 7)
        self.assertEqual(result.root_key_id, "offline-root-2026")
        self.assertEqual(result.receipt_issuer_id, "independent-verifier")
        self.assertEqual(result.receipt_key_id, "verifier-key-1")
        self.assertEqual(len(result.policy_envelope_sha256), 64)
        self.assertEqual(len(result.receipt_sha256), 64)
        self.assertEqual(len(result.receipt_attestation_payload_sha256), 64)
        self.assertEqual(result.policy_domain_binding, "ABSENT_IN_V1")
        self.assertIs(
            result.provenance_status,
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_receipt_signature_failure_occurs_before_independent_gate(self):
        document = json.loads(self.receipt_bytes)
        document["artifacts"][0]["sha256"] = "f" * 64
        tampered = encode(document)
        with patch(
            "origen.signed_root_attestation_chain_v1.verify_independent_provenance"
        ) as independent_gate:
            with self.assertRaisesRegex(ValueError, "signature verification failed"):
                self.inspect(original_receipt_bytes=tampered)
            independent_gate.assert_not_called()

    def test_wrong_external_root_pin_rejects_before_receipt_verification(self):
        wrong_root = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        with patch(
            "origen.signed_root_attestation_chain_v1.verify_receipt_attestation"
        ) as receipt_verifier:
            with self.assertRaisesRegex(ValueError, "root signature verification failed"):
                self.inspect(pinned_root_public_key_bytes=wrong_root)
            receipt_verifier.assert_not_called()

    def test_preconstructed_verified_policy_is_not_accepted_as_input(self):
        verified = verify_signed_trust_policy(
            self.policy_bytes,
            pinned_root_public_key_bytes=self.root_public_key,
            expected_root_key_id="offline-root-2026",
            minimum_policy_sequence=7,
            verification_time=NOW,
        )
        self.assertIs(type(verified), VerifiedTrustPolicy)
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            self.inspect(signed_policy_envelope_bytes=verified)

    def test_non_blocked_or_unknown_independent_status_fails_closed(self):
        with patch(
            "origen.signed_root_attestation_chain_v1.verify_independent_provenance",
            return_value="AUTHENTICATED",
        ):
            with self.assertRaisesRegex(RuntimeError, "non-blocked status"):
                self.inspect()

    def test_verification_time_timezone_is_snapshotted_once(self):
        one_shot = _OneShotUTC()
        local_time = datetime(2026, 11, 23, 4, 0, tzinfo=one_shot)
        result = self.inspect(verification_time=local_time)
        self.assertEqual(one_shot.calls, 1)
        self.assertIs(
            result.provenance_status,
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_mutable_byte_buffers_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            self.inspect(original_receipt_bytes=bytearray(self.receipt_bytes))
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            self.inspect(signed_policy_envelope_bytes=bytearray(self.policy_bytes))



    def test_independent_gate_reverifies_exact_v1_raw_inputs(self):
        with patch(
            "origen.signed_root_attestation_chain_v1.verify_independent_provenance",
            wraps=verify_independent_provenance,
        ) as independent_gate:
            result = self.inspect()
        independent_gate.assert_called_once_with(
            self.receipt_bytes,
            signed_policy_envelope_bytes=self.policy_bytes,
            pinned_root_public_key_bytes=self.root_public_key,
            expected_root_key_id="offline-root-2026",
            minimum_policy_sequence=7,
            verification_time=NOW,
        )
        self.assertIs(
            result.provenance_status,
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_independent_gate_rejects_partial_v1_context_instead_of_downgrading(self):
        with self.assertRaisesRegex(ValueError, "requires exact policy bytes"):
            verify_independent_provenance(
                self.receipt_bytes,
                signed_policy_envelope_bytes=self.policy_bytes,
            )

if __name__ == "__main__":
    unittest.main()
