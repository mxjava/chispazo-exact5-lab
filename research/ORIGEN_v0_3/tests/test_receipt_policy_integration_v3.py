"""Adversarial tests for V3 receipt-policy composition (synthetic keys only)."""
from __future__ import annotations

import base64
import copy
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import (
    ProvenanceStatus,
    _verify_independent_provenance_with_explicit_context,
    verify_independent_provenance,
)
from origen.physical_evidence_verifier_v2 import CLASSIC_PHYSICAL_POLICY_DOMAIN
from origen.receipt_policy_integration_v3 import (
    RECEIPT_ATTESTATION_ARTIFACT_TYPE,
    RECEIPT_ATTESTER_ROLE,
    RECEIPT_ROLE_STATUS,
    verify_receipt_attestation_with_policy_v3,
)
from test_physical_evidence_verifier_v2 import fixture as signed_v2_physical_fixture
from test_trust_receipt_v1 import encode
from test_trust_verifier_v1 import NOW, signed_receipt


ROOT_KEY_ID = "synthetic-classic-policy-root"
POLICY_SEQUENCE = 17
POLICY_VERSION = "policy-2026-11"
ISSUER_ID = "independent-verifier"
ISSUER_KEY_ID = "verifier-key-1"


def raw_public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def signed_v3_policy(
    receipt_public_key_bytes,
    *,
    role=RECEIPT_ATTESTER_ROLE,
    artifact_types=(RECEIPT_ATTESTATION_ARTIFACT_TYPE,),
    policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
    root_private=None,
    issuer_key_id=ISSUER_KEY_ID,
    issued_at_utc="2026-11-22T00:00:00Z",
    not_before_utc="2026-11-22T00:00:00Z",
    expires_at_utc="2026-12-01T00:00:00Z",
    additional_issuer_keys=(),
):
    if root_private is None:
        root_private = Ed25519PrivateKey.generate()
    document = {
        "schema_version": "origen.trust-policy-envelope.v3",
        "policy_domain": policy_domain,
        "policy_version": POLICY_VERSION,
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": issued_at_utc,
        "not_before_utc": not_before_utc,
        "expires_at_utc": expires_at_utc,
        "issuer_keys": [
            {
                "issuer_id": ISSUER_ID,
                "key_id": issuer_key_id,
                "public_key_b64": base64.b64encode(receipt_public_key_bytes).decode("ascii"),
                "valid_from_utc": "2026-01-01T00:00:00Z",
                "valid_until_utc": "2027-01-01T00:00:00Z",
                "revoked": False,
                "authorizations": [
                    {
                        "role": role,
                        "artifact_types": sorted(set(artifact_types)),
                    }
                ],
            },
            *list(additional_issuer_keys),
        ],
    }
    unsigned = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["signature"] = {
        "algorithm": "ed25519",
        "signature_b64": base64.b64encode(root_private.sign(unsigned)).decode("ascii"),
    }
    envelope = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return envelope, raw_public_key(root_private)


class _StatefulOffsetTimezone(tzinfo):
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=-2 if self.calls == 1 else 2)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "stateful-integration-test"


class TestReceiptPolicyIntegrationV3(unittest.TestCase):
    def setUp(self):
        self.receipt_bytes, self.receipt_public_key, _ = signed_receipt()
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key
        )

    def inspect(self, **overrides):
        args = {
            "original_receipt_bytes": self.receipt_bytes,
            "signed_policy_envelope_bytes": self.policy_bytes,
            "pinned_root_public_key_bytes": self.root_public_key,
            "expected_root_key_id": ROOT_KEY_ID,
            "minimum_policy_sequence": POLICY_SEQUENCE,
            "verification_time": NOW,
        }
        args.update(overrides)
        return verify_receipt_attestation_with_policy_v3(**args)

    def test_valid_signed_policy_and_receipt_signature_still_remain_blocked(self):
        result = self.inspect()
        self.assertTrue(result.root_attestation_signature_verified)
        self.assertEqual(result.policy_domain, CLASSIC_PHYSICAL_POLICY_DOMAIN)
        self.assertEqual(result.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.verified_issuer_id, ISSUER_ID)
        self.assertEqual(result.verified_key_id, ISSUER_KEY_ID)
        self.assertEqual(result.role_authorization_status, RECEIPT_ROLE_STATUS)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn("RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED", result.remaining_blockers)
        self.assertIn("SIGNED_POLICY_ENVELOPE_EXISTENCE_TIME_NOT_INDEPENDENTLY_AUTHENTICATED", result.remaining_blockers)
        self.assertIn("CUSTODY_RECEIPT_SIGNATURES_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED", result.remaining_blockers)

    def test_receipt_signature_cannot_precede_policy_effective_time(self):
        policy_bytes, root_public = signed_v3_policy(
            self.receipt_public_key,
            issued_at_utc="2026-11-23T03:06:00Z",
            not_before_utc="2026-11-23T03:06:00Z",
        )
        with self.assertRaisesRegex(
            ValueError,
            "receipt root attestation signing time is outside the signed V3 policy validity interval",
        ):
            self.inspect(
                signed_policy_envelope_bytes=policy_bytes,
                pinned_root_public_key_bytes=root_public,
                verification_time=NOW + timedelta(hours=1),
            )

    def test_delegated_key_id_cannot_alias_pinned_policy_root_key_id(self):
        policy_bytes, root_public = signed_v3_policy(
            self.receipt_public_key, issuer_key_id=ROOT_KEY_ID
        )
        with self.assertRaisesRegex(ValueError, "delegated issuer key ID must not reuse pinned root key ID"):
            self.inspect(
                signed_policy_envelope_bytes=policy_bytes,
                pinned_root_public_key_bytes=root_public,
            )

    def test_policy_root_key_cannot_be_reused_as_receipt_issuer_key(self):
        receipt_bytes, receipt_public, shared_private = signed_receipt()
        policy_bytes, root_public = signed_v3_policy(
            receipt_public, root_private=shared_private
        )
        self.assertEqual(root_public, receipt_public)
        with self.assertRaisesRegex(ValueError, "must not be reused as a delegated issuer key"):
            verify_receipt_attestation_with_policy_v3(
                receipt_bytes,
                policy_bytes,
                pinned_root_public_key_bytes=root_public,
                expected_root_key_id=ROOT_KEY_ID,
                minimum_policy_sequence=POLICY_SEQUENCE,
                verification_time=NOW,
            )

    def test_valid_root_signature_without_receipt_role_authorization_is_rejected(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key, role="PHYSICAL-RECORDS-SIGNER"
        )
        with self.assertRaisesRegex(ValueError, "not authorized by the signed V3 policy"):
            self.inspect()

    def test_valid_root_signature_without_receipt_artifact_type_authorization_is_rejected(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            artifact_types=("PHYSICAL-ACTA",),
        )
        with self.assertRaisesRegex(ValueError, "not authorized by the signed V3 policy"):
            self.inspect()

    def test_policy_from_non_classic_domain_is_rejected_even_when_root_signature_is_valid(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            policy_domain="origen.chispazo.de-las-tres.provenance",
        )
        with self.assertRaisesRegex(ValueError, "does not match externally expected deployment domain"):
            self.inspect()

    def test_policy_sequence_below_external_floor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.inspect(minimum_policy_sequence=POLICY_SEQUENCE + 1)

    def test_wrong_root_pin_is_rejected(self):
        wrong_root = raw_public_key(Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self.inspect(pinned_root_public_key_bytes=wrong_root)

    def test_receipt_tampering_is_rejected_before_provenance_gate(self):
        import json
        from test_trust_receipt_v1 import encode

        document = json.loads(self.receipt_bytes)
        document["artifacts"][0]["sha256"] = "f" * 64
        tampered = encode(document)
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.inspect(original_receipt_bytes=tampered)

    def test_stateful_timezone_offset_is_sampled_once_across_policy_and_receipt(self):
        tz = _StatefulOffsetTimezone()
        supplied = datetime(2026, 11, 23, 4, 0, tzinfo=tz)
        result = self.inspect(verification_time=supplied)
        self.assertEqual(tz.calls, 1)
        self.assertEqual(
            result.verification_time_utc,
            datetime(2026, 11, 23, 6, 0, tzinfo=timezone.utc),
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_validly_signed_v2_envelope_is_not_implicitly_accepted(self):
        v2 = signed_v2_physical_fixture()
        with self.assertRaisesRegex(ValueError, "fields mismatch|unsupported trust-policy envelope schema"):
            self.inspect(
                signed_policy_envelope_bytes=v2["signed_policy_envelope_bytes"],
                pinned_root_public_key_bytes=v2["pinned_root_public_key_bytes"],
            )



    def test_independent_provenance_gate_receives_exact_bytes_and_reverification_inputs(self):
        from unittest.mock import patch

        observed = []

        def gate(raw, **context):
            observed.append((raw, context))
            return ProvenanceStatus.BLOCKED_PROVENANCE

        with patch(
            "origen.receipt_policy_integration_v3._verify_independent_provenance_with_explicit_context",
            side_effect=gate,
        ):
            result = self.inspect()

        self.assertEqual(len(observed), 1)
        raw, context = observed[0]
        self.assertEqual(raw, self.receipt_bytes)
        self.assertEqual(context["signed_policy_envelope_bytes"], self.policy_bytes)
        self.assertEqual(context["pinned_root_public_key_bytes"], self.root_public_key)
        self.assertEqual(context["expected_root_key_id"], ROOT_KEY_ID)
        self.assertEqual(context["minimum_policy_sequence"], POLICY_SEQUENCE)
        self.assertEqual(context["verification_time"], NOW)
        self.assertNotIn("verified_policy", context)
        self.assertNotIn("verified_receipt", context)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def _verify_at_boundary(self, **overrides):
        args = {
            "original_receipt_bytes": self.receipt_bytes,
            "signed_policy_envelope_bytes": self.policy_bytes,
            "pinned_root_public_key_bytes": self.root_public_key,
            "expected_root_key_id": ROOT_KEY_ID,
            "minimum_policy_sequence": POLICY_SEQUENCE,
            "verification_time": NOW,
        }
        args.update(overrides)
        return _verify_independent_provenance_with_explicit_context(**args)

    def test_independent_provenance_reverifies_exact_v3_bytes_and_still_blocks(self):
        result = self._verify_at_boundary()
        self.assertIs(result, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_independent_provenance_rejects_tampered_receipt_at_boundary(self):
        document = json.loads(self.receipt_bytes)
        document["artifacts"][0]["sha256"] = "f" * 64
        tampered = encode(document)
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self._verify_at_boundary(original_receipt_bytes=tampered)

    def test_independent_provenance_rejects_noncanonical_or_tampered_policy_bytes_at_boundary(self):
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            self._verify_at_boundary(signed_policy_envelope_bytes=self.policy_bytes + b" ")

    def test_independent_provenance_rejects_tampered_signed_policy_at_boundary(self):
        document = json.loads(self.policy_bytes)
        document["policy_sequence"] = POLICY_SEQUENCE + 1
        tampered = encode(document)
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self._verify_at_boundary(signed_policy_envelope_bytes=tampered)

    def test_independent_provenance_rejects_wrong_root_pin_at_boundary(self):
        wrong_root = raw_public_key(Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            self._verify_at_boundary(pinned_root_public_key_bytes=wrong_root)

    def test_independent_provenance_rejects_policy_rollback_floor_at_boundary(self):
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self._verify_at_boundary(minimum_policy_sequence=POLICY_SEQUENCE + 1)

    def test_public_independent_provenance_rejects_caller_context(self):
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            verify_independent_provenance(
                self.receipt_bytes,
                signed_policy_envelope_bytes=self.policy_bytes,
            )

    def test_independent_provenance_rejects_policy_without_receipt_role_authorization(self):
        policy_bytes, root_public_key = signed_v3_policy(
            self.receipt_public_key,
            role="PHYSICAL-RECORDS-SIGNER",
        )
        with self.assertRaisesRegex(ValueError, "receipt-attester role/artifact authorization"):
            self._verify_at_boundary(
                signed_policy_envelope_bytes=policy_bytes,
                pinned_root_public_key_bytes=root_public_key,
            )

    def test_independent_provenance_requires_normalized_exact_utc_instant(self):
        tz = _StatefulOffsetTimezone()
        supplied = datetime(2026, 11, 23, 4, 0, tzinfo=tz)
        with self.assertRaisesRegex(ValueError, "exact normalized UTC datetime"):
            self._verify_at_boundary(verification_time=supplied)
        self.assertEqual(tz.calls, 0)

    def test_future_authenticated_provenance_status_is_rejected(self):
        from enum import Enum
        from unittest.mock import patch

        class FutureProvenanceStatus(Enum):
            BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"
            AUTHENTICATED = "AUTHENTICATED"

        with (
            patch(
                "origen.receipt_policy_integration_v3.ProvenanceStatus",
                FutureProvenanceStatus,
            ),
            patch(
                "origen.receipt_policy_integration_v3._verify_independent_provenance_with_explicit_context",
                return_value=FutureProvenanceStatus.AUTHENTICATED,
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "unsupported non-blocked status",
            ):
                self.inspect()


if __name__ == "__main__":
    unittest.main()
