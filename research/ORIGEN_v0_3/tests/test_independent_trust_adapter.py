"""Adversarial tests for the fail-closed signed-policy trust boundary."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import (
    INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED,
    ProvenanceStatus,
    verify_independent_provenance,
)
from origen.trust_policy_envelope_v1 import (
    SCHEMA_VERSION,
    VerifiedTrustPolicy,
    verify_signed_trust_policy,
)
from origen.trust_receipt_v1 import (
    MAX_TRUST_RECEIPT_BYTES,
    parse_unverified_receipt,
)
from origen.trust_verifier_v1 import TrustPolicy
from test_trust_receipt_v1 import encode, valid_document


NOW = datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc)


def raw_public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def signed_receipt(issuer_private_key):
    document = valid_document()
    unsigned = copy.deepcopy(document)
    unsigned["receipt_attestation"].pop("signature_b64")
    payload = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        issuer_private_key.sign(payload)
    ).decode("ascii")
    return encode(document)


def signed_policy_envelope(issuer_public_bytes, *, not_before="2026-11-23T03:00:00Z",
                           expires="2026-12-01T00:00:00Z",
                           required_artifact_types=("sphere-measurement-register",)):
    root_private_key = Ed25519PrivateKey.generate()
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "policy-2026-11",
        "policy_sequence": 7,
        "issuer_id": "policy-authority",
        "root_key_id": "offline-root-2026",
        "issued_at_utc": "2026-11-22T00:00:00Z",
        "not_before_utc": not_before,
        "expires_at_utc": expires,
        "required_artifact_types": list(required_artifact_types),
        "issuer_keys": [{
            "issuer_id": "independent-verifier",
            "key_id": "verifier-key-1",
            "public_key_b64": base64.b64encode(issuer_public_bytes).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
        }],
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = dict(document)
    unsigned.pop("signature")
    payload = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["signature"]["signature_b64"] = base64.b64encode(
        root_private_key.sign(payload)
    ).decode("ascii")
    return encode(document), raw_public_key(root_private_key)


def verified_policy(issuer_public_bytes, *, not_before="2026-11-23T03:00:00Z",
                    expires="2026-12-01T00:00:00Z", verification_time=NOW,
                    required_artifact_types=("sphere-measurement-register",)):
    raw, root_public = signed_policy_envelope(
        issuer_public_bytes, not_before=not_before, expires=expires,
        required_artifact_types=required_artifact_types,
    )
    return verify_signed_trust_policy(
        raw,
        pinned_root_public_key_bytes=root_public,
        expected_root_key_id="offline-root-2026",
        minimum_policy_sequence=7,
        verification_time=verification_time,
    )


class TestIndependentTrustAdapter(unittest.TestCase):
    def test_unprovisioned_backend_always_blocks_authentication_looking_bytes(self):
        result = verify_independent_provenance(b'{"status":"AUTHENTICATED"}')
        self.assertIs(result, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(
            INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED,
            "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED",
        )
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)

    def test_structurally_valid_receipt_still_cannot_authenticate_without_policy(self):
        raw = encode(valid_document())
        self.assertIs(
            verify_independent_provenance(raw),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_malformed_bytes_remain_unparsed_without_policy(self):
        self.assertIs(
            verify_independent_provenance(b'{"status":'),
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )

    def test_verified_policy_composes_with_receipt_signature_but_still_blocks(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        policy = verified_policy(raw_public_key(issuer))
        result = verify_independent_provenance(
            raw, verified_trust_policy=policy, verification_time=NOW
        )
        self.assertIs(result, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)

    def test_tampered_receipt_is_rejected_during_composed_verification(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        policy = verified_policy(raw_public_key(issuer))
        document = json.loads(raw)
        document["artifacts"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            verify_independent_provenance(
                encode(document), verified_trust_policy=policy,
                verification_time=NOW
            )

    def test_expired_policy_is_rejected_at_receipt_verification_time(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        policy_time = datetime(2026, 11, 23, 3, 20, tzinfo=timezone.utc)
        policy = verified_policy(
            raw_public_key(issuer), expires="2026-11-23T03:30:00Z",
            verification_time=policy_time
        )
        later = datetime(2026, 11, 23, 3, 40, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "not valid at receipt verification time"):
            verify_independent_provenance(
                raw, verified_trust_policy=policy, verification_time=later
            )

    def test_policy_not_before_is_rechecked_at_receipt_verification_time(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        policy = verified_policy(
            raw_public_key(issuer), not_before="2026-11-23T03:30:00Z"
        )
        before = datetime(2026, 11, 23, 3, 15, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "not valid at receipt verification time"):
            verify_independent_provenance(
                raw, verified_trust_policy=policy, verification_time=before
            )

    def test_policy_and_verification_time_must_be_supplied_together(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        policy = verified_policy(raw_public_key(issuer))
        with self.assertRaisesRegex(ValueError, "must be supplied together"):
            verify_independent_provenance(
                raw, verified_trust_policy=policy
            )
        with self.assertRaisesRegex(ValueError, "must be supplied together"):
            verify_independent_provenance(raw, verification_time=NOW)

    def test_unverified_trust_policy_is_not_accepted_as_verified_policy(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        with self.assertRaisesRegex(TypeError, "exact VerifiedTrustPolicy"):
            verify_independent_provenance(
                raw, verified_trust_policy=TrustPolicy("policy-2026-11", ()),
                verification_time=NOW
            )

    def test_verified_policy_public_constructor_is_disabled(self):
        with self.assertRaisesRegex(
            TypeError, "created only by verify_signed_trust_policy"
        ):
            VerifiedTrustPolicy(
                TrustPolicy("policy-2026-11", ()), 7, "root", "a" * 64,
                NOW, NOW, NOW
            )

    def test_caller_cannot_inject_trust_roots_or_verifier_callbacks(self):
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                b"receipt", trust_roots={"self-signed-test-key": b"fake"}
            )
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                b"receipt", verifier=lambda *_: True
            )

    def test_bytes_subclasses_are_not_accepted_at_boundary(self):
        class SpoofedBytes(bytes):
            pass
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            verify_independent_provenance(SpoofedBytes(b"receipt"))

    def test_mutable_and_view_backed_buffers_are_rejected_at_boundary(self):
        mutable = bytearray(b"receipt")
        for candidate in (mutable, memoryview(mutable)):
            with self.subTest(input_type=type(candidate).__name__):
                with self.assertRaisesRegex(TypeError, "exact bytes"):
                    verify_independent_provenance(candidate)

    def test_empty_original_bytes_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            verify_independent_provenance(b"")

    def test_input_at_shared_receipt_size_limit_remains_fail_closed(self):
        result = verify_independent_provenance(b"x" * MAX_TRUST_RECEIPT_BYTES)
        self.assertIs(result, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_input_one_byte_over_shared_receipt_size_limit_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError, f"must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        ):
            verify_independent_provenance(b"x" * (MAX_TRUST_RECEIPT_BYTES + 1))

    def test_policy_not_before_must_cover_receipt_signing_time(self):
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(issuer)
        # The policy is valid at NOW (04:00), but the receipt was signed at
        # 03:05 and the policy does not become effective until 03:06.
        policy = verified_policy(
            raw_public_key(issuer),
            not_before="2026-11-23T03:06:00Z",
        )
        with self.assertRaisesRegex(
            ValueError, "not effective at receipt signing time"
        ):
            verify_independent_provenance(
                raw, verified_trust_policy=policy, verification_time=NOW
            )


if __name__ == "__main__":
    unittest.main()
