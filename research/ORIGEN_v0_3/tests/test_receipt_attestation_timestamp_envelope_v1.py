"""Synthetic adversarial tests for detached, non-circular receipt timestamp proofs."""
from __future__ import annotations

import base64
import hashlib
import json
import unittest
from datetime import timedelta

from origen.independent_trust_adapter import ProvenanceStatus
from origen.receipt_attestation_timestamp_envelope_v1 import (
    SCHEMA_VERSION,
    inspect_signed_root_attestation_chain_with_detached_receipt_timestamp,
)
from test_trust_policy_integration_v1 import ROOT_KEY_ID
from test_trust_policy_rfc3161_integration_v1 import (
    ALLOWED_TSA_OID,
    _fixture,
    _stamp,
    _timestamp_token,
)


def _canonical(document) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _make_envelope(
    fixture,
    *,
    authority_id="tsa-test",
    nonce=778899,
    token_data=None,
    token_gen_time=None,
    accuracy=None,
    policy_oid=ALLOWED_TSA_OID,
):
    receipt = json.loads(fixture["receipt_bytes"].decode("utf-8"))
    signature_bytes = base64.b64decode(
        receipt["receipt_attestation"]["signature_b64"], validate=True
    )
    signed_at = __import__("datetime").datetime.fromisoformat(
        receipt["receipt_attestation"]["signed_at_utc"].replace("Z", "+00:00")
    )
    token = _timestamp_token(
        signature_bytes if token_data is None else token_data,
        fixture["tsa_root_certificate"],
        fixture["tsa_signer_certificate"],
        fixture["tsa_signer_private_key"],
        nonce=nonce,
        gen_time=signed_at if token_gen_time is None else token_gen_time,
        accuracy=accuracy,
        policy_oid=policy_oid,
    )
    document = {
        "schema_version": SCHEMA_VERSION,
        "receipt_sha256": hashlib.sha256(fixture["receipt_bytes"]).hexdigest(),
        "signature_sha256": hashlib.sha256(signature_bytes).hexdigest(),
        "token_sha256": hashlib.sha256(token).hexdigest(),
        "authority_id": authority_id,
        "expected_nonce": nonce,
        "token_der_b64": base64.b64encode(token).decode("ascii"),
    }
    return _canonical(document)


def _inspect(fixture, envelope, **overrides):
    values = {
        "pinned_root_public_key_bytes": fixture["policy_root_public"],
        "expected_root_key_id": ROOT_KEY_ID,
        "minimum_policy_sequence": 7,
        "verification_time": fixture["verification_time"],
        "signed_timestamp_authority_policy_bytes": fixture["tsa_policy_bytes"],
        "output_seal_timestamp_evidence": fixture["evidence"],
        "pinned_tsa_root_certificate_der": fixture["tsa_root_der"],
        "detached_receipt_timestamp_envelope_bytes": envelope,
    }
    values.update(overrides)
    return inspect_signed_root_attestation_chain_with_detached_receipt_timestamp(
        fixture["receipt_bytes"], fixture["policy_bytes"], **values
    )


def _document(raw):
    return json.loads(raw.decode("ascii"))


class TestDetachedReceiptAttestationTimestampEnvelopeV1(unittest.TestCase):
    def test_valid_detached_token_binds_exact_receipt_signature_without_circular_claim(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(fixture, accuracy={"seconds": 1})
        result = _inspect(fixture, envelope)
        proof = result.receipt_attestation_timestamp
        self.assertEqual(proof.receipt_sha256, hashlib.sha256(fixture["receipt_bytes"]).hexdigest())
        self.assertEqual(proof.signature_sha256, _document(envelope)["signature_sha256"])
        self.assertEqual(proof.token_sha256, _document(envelope)["token_sha256"])
        self.assertEqual(proof.authority_id, "tsa-test")
        self.assertEqual(proof.tsa_policy_oid, ALLOWED_TSA_OID)
        self.assertEqual(proof.gen_time_utc.isoformat(), "2026-11-25T05:55:00+00:00")
        self.assertEqual(proof.accuracy_microseconds, 1_000_000)
        self.assertEqual(
            proof.binding_status,
            "RFC3161_IMPRINT_MATCHES_EXACT_RECEIPT_SIGNATURE_BYTES",
        )
        self.assertEqual(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn(
            "RECEIPT_V1_EMBEDDED_TIMESTAMP_REFERENCE_NOT_USED_AS_PROOF_BINDING",
            result.remaining_blockers,
        )
        self.assertNotIn(
            "RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED",
            result.remaining_blockers,
        )

    def test_receipt_digest_must_bind_exact_original_bytes(self):
        fixture = _fixture(accuracy={"seconds": 1})
        document = _document(_make_envelope(fixture, accuracy={"seconds": 1}))
        document["receipt_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "receipt_sha256"):
            _inspect(fixture, _canonical(document))

    def test_signature_digest_must_bind_exact_embedded_signature_bytes(self):
        fixture = _fixture(accuracy={"seconds": 1})
        document = _document(_make_envelope(fixture, accuracy={"seconds": 1}))
        document["signature_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "signature_sha256"):
            _inspect(fixture, _canonical(document))

    def test_token_digest_must_bind_exact_detached_token_bytes(self):
        fixture = _fixture(accuracy={"seconds": 1})
        document = _document(_make_envelope(fixture, accuracy={"seconds": 1}))
        document["token_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "token_sha256"):
            _inspect(fixture, _canonical(document))

    def test_token_imprint_must_cover_exact_receipt_signature_not_other_data(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(
            fixture,
            accuracy={"seconds": 1},
            token_data=b"not-the-receipt-attestation-signature",
        )
        with self.assertRaisesRegex(ValueError, "message imprint"):
            _inspect(fixture, envelope)

    def test_nonce_must_match_signed_tsa_token(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(fixture, accuracy={"seconds": 1}, nonce=778899)
        document = _document(envelope)
        document["expected_nonce"] = 778900
        with self.assertRaisesRegex(ValueError, "nonce"):
            _inspect(fixture, _canonical(document))

    def test_authority_must_be_in_root_signed_tsa_policy(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(
            fixture, accuracy={"seconds": 1}, authority_id="unlisted-authority"
        )
        with self.assertRaisesRegex(ValueError, "not authorized"):
            _inspect(fixture, envelope)

    def test_policy_oid_must_be_authorized_for_detached_receipt_token(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(
            fixture, accuracy={"seconds": 1}, policy_oid="1.2.3.4.99"
        )
        with self.assertRaisesRegex(ValueError, "policy OID is not authorized"):
            _inspect(fixture, envelope)

    def test_gen_time_must_equal_signed_attestation_time(self):
        fixture = _fixture(accuracy={"seconds": 1})
        receipt = json.loads(fixture["receipt_bytes"].decode("utf-8"))
        signed_at = __import__("datetime").datetime.fromisoformat(
            receipt["receipt_attestation"]["signed_at_utc"].replace("Z", "+00:00")
        )
        envelope = _make_envelope(
            fixture,
            accuracy={"seconds": 1},
            token_gen_time=signed_at + timedelta(seconds=1),
        )
        with self.assertRaisesRegex(ValueError, "does not match signed_at_utc"):
            _inspect(fixture, envelope)

    def test_missing_accuracy_fails_closed(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(fixture, accuracy=None)
        with self.assertRaisesRegex(ValueError, "accuracy is absent"):
            _inspect(fixture, envelope)

    def test_whitespace_variant_is_rejected_as_noncanonical(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(fixture, accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "canonical ASCII JSON"):
            _inspect(fixture, b" " + envelope)

    def test_duplicate_json_key_is_rejected_before_semantic_use(self):
        fixture = _fixture(accuracy={"seconds": 1})
        envelope = _make_envelope(fixture, accuracy={"seconds": 1})
        duplicate = envelope.replace(
            b'"schema_version":',
            b'"schema_version":"attacker","schema_version":',
            1,
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            _inspect(fixture, duplicate)

    def test_unknown_envelope_field_is_rejected(self):
        fixture = _fixture(accuracy={"seconds": 1})
        document = _document(_make_envelope(fixture, accuracy={"seconds": 1}))
        document["authenticated"] = True
        with self.assertRaisesRegex(ValueError, "exact V1 schema"):
            _inspect(fixture, _canonical(document))

    def test_invalid_nonce_type_is_rejected(self):
        fixture = _fixture(accuracy={"seconds": 1})
        document = _document(_make_envelope(fixture, accuracy={"seconds": 1}))
        document["expected_nonce"] = True
        with self.assertRaisesRegex(ValueError, "exact positive"):
            _inspect(fixture, _canonical(document))


if __name__ == "__main__":
    unittest.main()
