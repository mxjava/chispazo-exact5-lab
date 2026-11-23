"""Adversarial tests for V2 proof-to-signature and proof-to-time binding."""
from __future__ import annotations

import base64
import copy
import hashlib
import unittest

from origen.trust_receipt_v1 import parse_unverified_receipt
from origen.trust_receipt_v2 import (
    MAX_TRUST_RECEIPT_JSON_DEPTH_V2,
    SCHEMA_VERSION_V2,
    UnverifiedTrustReceiptV2,
    parse_unverified_receipt_v2,
)
from test_trust_receipt_v1 import encode, valid_document


def valid_v2_document():
    document = valid_document()
    document["schema_version"] = SCHEMA_VERSION_V2
    attestation_signature = base64.b64decode(
        document["receipt_attestation"]["signature_b64"], validate=True
    )
    document["trusted_time_proofs"][0]["subject_sha256"] = hashlib.sha256(
        attestation_signature
    ).hexdigest()

    for index, seal in enumerate(document["output_seals"]):
        proof_digest = hashlib.sha256(f"output-seal-proof-{index}".encode("ascii")).hexdigest()
        seal["timestamp_proof_sha256"] = proof_digest
        document["trusted_time_proofs"].append(
            {
                "authority_id": "tsa-test",
                "event_id": f"output-seal-{index}",
                "event_at_utc": seal["created_at_utc"],
                "proof_sha256": proof_digest,
                "subject_sha256": seal["signature_sha256"],
            }
        )
    return document


class TestTrustReceiptV2(unittest.TestCase):
    def test_valid_v2_binds_both_output_seals_and_attestation(self):
        raw = encode(valid_v2_document())
        parsed = parse_unverified_receipt_v2(raw)

        self.assertIsInstance(parsed, UnverifiedTrustReceiptV2)
        self.assertEqual(parsed.receipt.target.modality, "CLASSIC")
        self.assertEqual(len(parsed.output_seal_time_bindings), 2)
        self.assertEqual(parsed.raw_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(parsed.receipt.raw_sha256, parsed.raw_sha256)
        for seal, binding in zip(parsed.receipt.output_seals, parsed.output_seal_time_bindings):
            self.assertEqual(binding.signature_sha256, seal.signature_sha256)
            self.assertEqual(binding.created_at_utc, seal.created_at_utc)

    def test_output_seal_timestamp_proof_must_be_declared(self):
        document = valid_v2_document()
        document["output_seals"][0]["timestamp_proof_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "must reference a declared V2 proof"):
            parse_unverified_receipt_v2(encode(document))

    def test_output_seal_timestamp_proof_must_bind_exact_signature_digest(self):
        document = valid_v2_document()
        proof_ref = document["output_seals"][0]["timestamp_proof_sha256"]
        proof = next(
            item for item in document["trusted_time_proofs"]
            if item["proof_sha256"] == proof_ref
        )
        proof["subject_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "subject must match signature_sha256"):
            parse_unverified_receipt_v2(encode(document))

    def test_output_seal_timestamp_proof_time_must_match_created_at(self):
        document = valid_v2_document()
        proof_ref = document["output_seals"][0]["timestamp_proof_sha256"]
        proof = next(
            item for item in document["trusted_time_proofs"]
            if item["proof_sha256"] == proof_ref
        )
        proof["event_at_utc"] = "2026-11-23T02:49:59Z"
        with self.assertRaisesRegex(ValueError, "time must match created_at_utc"):
            parse_unverified_receipt_v2(encode(document))

    def test_attestation_timestamp_proof_must_bind_exact_signature_bytes(self):
        document = valid_v2_document()
        document["trusted_time_proofs"][0]["subject_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "must bind to its signature bytes"):
            parse_unverified_receipt_v2(encode(document))

    def test_attestation_and_output_seals_cannot_reuse_timestamp_proof(self):
        document = valid_v2_document()
        document["output_seals"][0]["timestamp_proof_sha256"] = (
            document["receipt_attestation"]["timestamp_proof_sha256"]
        )
        with self.assertRaisesRegex(ValueError, "references must be distinct"):
            parse_unverified_receipt_v2(encode(document))

    def test_v2_rejects_excessive_json_nesting_before_decode(self):
        nested = (
            b'{"untrusted":'
            + b"[" * MAX_TRUST_RECEIPT_JSON_DEPTH_V2
            + b"0"
            + b"]" * MAX_TRUST_RECEIPT_JSON_DEPTH_V2
            + b"}"
        )
        with self.assertRaisesRegex(
            ValueError,
            f"maximum JSON nesting depth {MAX_TRUST_RECEIPT_JSON_DEPTH_V2}",
        ):
            parse_unverified_receipt_v2(nested)

    def test_v2_brackets_inside_json_strings_do_not_count_as_nesting(self):
        document = valid_v2_document()
        document["status"] = "AUTHENTICATED[]{}"
        with self.assertRaisesRegex(ValueError, "status must be"):
            parse_unverified_receipt_v2(encode(document))

    def test_v1_parser_does_not_silently_accept_v2_schema(self):
        with self.assertRaisesRegex(ValueError, "unsupported trust receipt schema_version"):
            parse_unverified_receipt(encode(valid_v2_document()))


if __name__ == "__main__":
    unittest.main()
