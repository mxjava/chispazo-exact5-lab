"""Adversarial tests for the untrusted ORIGEN trust-receipt parser."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest

from origen.trust_receipt_v1 import (
    MAX_TRUST_RECEIPT_BYTES,
    UnverifiedTrustReceipt,
    parse_unverified_receipt,
)


def digest(char: str) -> str:
    return char * 64


def valid_document() -> dict:
    contest_id = "12389"
    target_list = json.dumps([contest_id], separators=(",", ":"), ensure_ascii=True).encode("ascii")
    close_at = "2026-11-23T03:00:00Z"
    return {
        "schema_version": "origen.trust-receipt.v1",
        "status": "AUTHENTICATED",
        "policy_version": "policy-2026-11",
        "verifier_build_sha256": digest("0"),
        "artifacts": [
            {
                "artifact_type": "sphere-measurement-register",
                "sha256": digest("1"),
                "byte_length": 1024,
                "contest_id": contest_id,
            }
        ],
        "signers": [
            {
                "subject_id": "institution-signer-1",
                "role": "records-officer",
                "key_id": "institution-key-1",
                "algorithm": "ed25519",
                "signature_sha256": digest("2"),
            },
            {
                "subject_id": "institution-signer-2",
                "role": "records-officer",
                "key_id": "institution-key-2",
                "algorithm": "ed25519",
                "signature_sha256": digest("e"),
            },
        ],
        "custodians": [
            {
                "subject_id": "independent-custodian-1",
                "role": "external-custodian",
                "receipt_sha256": digest("3"),
            }
        ],
        "trusted_time_proofs": [
            {
                "authority_id": "tsa-test",
                "event_id": "event-1",
                "event_at_utc": "2026-11-23T03:05:00Z",
                "proof_sha256": digest("4"),
            }
        ],
        "ledger_anchor": {
            "ledger_id": "ledger-test",
            "entry_id": "entry-1",
            "previous_head_sha256": digest("5"),
            "head_sha256": digest("6"),
            "inclusion_proof_sha256": digest("7"),
        },
        "target": {
            "modality": "CLASSIC",
            "contest_id": contest_id,
            "draw_close_at_utc": close_at,
            "target_list_sha256": hashlib.sha256(target_list).hexdigest(),
        },
        "commitments": {
            "preregistration_sha256": digest("8"),
            "candidate_sha256": digest("9"),
            "code_sha256": digest("a"),
            "environment_sha256": digest("b"),
        },
        "output_seals": [
            {
                "target_contest_id": contest_id,
                "generator_id": "generator-a",
                "created_at_utc": "2026-11-23T02:50:00Z",
                "portfolio_sha256": digest("c"),
                "seal_sha256": digest("d"),
                "signature_sha256": digest("e"),
            },
            {
                "target_contest_id": contest_id,
                "generator_id": "generator-b",
                "created_at_utc": "2026-11-23T02:51:00Z",
                "portfolio_sha256": digest("f"),
                "seal_sha256": digest("1"),
                "signature_sha256": digest("2"),
            },
        ],
        "failure_codes": [],
        "receipt_attestation": {
            "issuer_id": "independent-verifier",
            "key_id": "verifier-key-1",
            "algorithm": "ed25519",
            "signature_b64": base64.b64encode(b"x" * 64).decode("ascii"),
            "signed_at_utc": "2026-11-23T03:05:00Z",
            "timestamp_proof_sha256": digest("4"),
        },
    }


def encode(document: dict) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class TestTrustReceiptV1(unittest.TestCase):
    def test_valid_document_parses_to_explicitly_unverified_type(self):
        parsed = parse_unverified_receipt(encode(valid_document()))
        self.assertIsInstance(parsed, UnverifiedTrustReceipt)
        self.assertEqual(parsed.declared_status, "AUTHENTICATED")
        self.assertEqual(parsed.target.modality, "CLASSIC")
        self.assertEqual(parsed.target.contest_id, "12389")
        self.assertEqual(len(parsed.output_seals), 2)
        self.assertEqual(parsed.raw_sha256, hashlib.sha256(encode(valid_document())).hexdigest())
        self.assertFalse(hasattr(parsed, "authenticated"))

    def test_attestation_timestamp_proof_must_reference_declared_trusted_time_proof(self):
        document = valid_document()
        document["receipt_attestation"]["timestamp_proof_sha256"] = digest("3")
        with self.assertRaisesRegex(
            ValueError,
            "receipt attestation timestamp proof must reference a declared trusted time proof",
        ):
            parse_unverified_receipt(encode(document))

    def test_attestation_signed_at_must_match_referenced_trusted_time_proof(self):
        document = valid_document()
        document["trusted_time_proofs"][0]["event_at_utc"] = "2026-11-23T03:04:59Z"
        with self.assertRaisesRegex(
            ValueError,
            "signed_at_utc must match its referenced trusted time proof",
        ):
            parse_unverified_receipt(encode(document))

    def test_rejected_document_requires_failure_code(self):
        document = valid_document()
        document["status"] = "REJECTED"
        with self.assertRaisesRegex(ValueError, "must contain at least one failure code"):
            parse_unverified_receipt(encode(document))

    def test_authenticated_declaration_cannot_hide_failure_codes(self):
        document = valid_document()
        document["failure_codes"] = ["SIGNATURE_INVALID"]
        with self.assertRaisesRegex(ValueError, "cannot contain failure codes"):
            parse_unverified_receipt(encode(document))

    def test_noncanonical_whitespace_is_rejected(self):
        raw = json.dumps(
            valid_document(), sort_keys=True, ensure_ascii=True
        ).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            parse_unverified_receipt(raw)

    def test_noncanonical_key_order_is_rejected(self):
        raw = json.dumps(
            valid_document(), sort_keys=False, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            parse_unverified_receipt(raw)

    def test_noncanonical_string_escape_is_rejected(self):
        raw = encode(valid_document()).replace(
            b'"policy_version":"policy-2026-11"',
            b'"policy_version":"policy\\u002d2026-11"',
        )
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 encoding"):
            parse_unverified_receipt(raw)

    def test_duplicate_root_json_key_is_rejected(self):
        raw = b'{"schema_version":"origen.trust-receipt.v1","schema_version":"origen.trust-receipt.v1"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_unverified_receipt(raw)

    def test_duplicate_nested_json_key_is_rejected(self):
        raw = encode(valid_document()).replace(
            b'"modality":"CLASSIC"',
            b'"modality":"CLASSIC","modality":"CLASSIC"',
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            parse_unverified_receipt(raw)

    def test_unknown_root_field_is_rejected(self):
        document = valid_document()
        document["authenticated_provenance"] = True
        with self.assertRaisesRegex(ValueError, "unexpected"):
            parse_unverified_receipt(encode(document))

    def test_boolean_is_not_accepted_as_byte_length(self):
        document = valid_document()
        document["artifacts"][0]["byte_length"] = True
        with self.assertRaisesRegex(ValueError, "positive integer"):
            parse_unverified_receipt(encode(document))

    def test_uppercase_digest_is_rejected_not_normalized(self):
        document = valid_document()
        document["verifier_build_sha256"] = "A" * 64
        with self.assertRaisesRegex(ValueError, "lowercase hexadecimal"):
            parse_unverified_receipt(encode(document))

    def test_noncanonical_contest_id_is_rejected(self):
        document = valid_document()
        document["target"]["contest_id"] = "012389"
        with self.assertRaisesRegex(ValueError, "canonical positive decimal"):
            parse_unverified_receipt(encode(document))

    def test_de_las_tres_target_is_rejected(self):
        document = valid_document()
        document["target"]["modality"] = "DE LAS TRES"
        with self.assertRaisesRegex(ValueError, "restricted to CLASSIC"):
            parse_unverified_receipt(encode(document))

    def test_target_list_digest_must_bind_exact_target(self):
        document = valid_document()
        document["target"]["target_list_sha256"] = digest("a")
        with self.assertRaisesRegex(ValueError, "does not match"):
            parse_unverified_receipt(encode(document))

    def test_output_seal_at_or_after_close_is_rejected(self):
        document = valid_document()
        document["output_seals"][1]["created_at_utc"] = "2026-11-23T03:00:00Z"
        with self.assertRaisesRegex(ValueError, "strictly before"):
            parse_unverified_receipt(encode(document))

    def test_identical_portfolio_bytes_are_not_two_independent_outputs(self):
        document = valid_document()
        document["output_seals"][1]["portfolio_sha256"] = document["output_seals"][0]["portfolio_sha256"]
        with self.assertRaisesRegex(ValueError, "distinct portfolio bytes"):
            parse_unverified_receipt(encode(document))

    def test_same_generator_cannot_claim_two_independent_seals(self):
        document = valid_document()
        document["output_seals"][1]["generator_id"] = document["output_seals"][0]["generator_id"]
        with self.assertRaisesRegex(ValueError, "distinct generators"):
            parse_unverified_receipt(encode(document))

    def test_output_seal_signature_must_reference_a_declared_signer_signature(self):
        document = valid_document()
        document["output_seals"][0]["signature_sha256"] = digest("9")
        with self.assertRaisesRegex(
            ValueError,
            "every output seal signature must reference a declared signer signature digest",
        ):
            parse_unverified_receipt(encode(document))

    def test_signer_signature_digests_must_be_unique(self):
        document = valid_document()
        document["signers"][1]["signature_sha256"] = document["signers"][0]["signature_sha256"]
        with self.assertRaisesRegex(ValueError, "signers contain duplicate signature digests"):
            parse_unverified_receipt(encode(document))

    def test_signer_cannot_also_be_a_generator(self):
        document = valid_document()
        document["signers"][0]["subject_id"] = document["output_seals"][0]["generator_id"]
        with self.assertRaisesRegex(ValueError, "signer and generator claims must be separate"):
            parse_unverified_receipt(encode(document))

    def test_custodian_cannot_be_one_of_the_generators(self):
        document = valid_document()
        document["custodians"][0]["subject_id"] = "generator-a"
        with self.assertRaisesRegex(ValueError, "generator and custodian"):
            parse_unverified_receipt(encode(document))

    def test_signer_subject_cannot_claim_multiple_signer_roles(self):
        document = valid_document()
        second = copy.deepcopy(document["signers"][0])
        second["role"] = "independent-reviewer"
        second["key_id"] = "institution-key-2"
        second["signature_sha256"] = digest("a")
        document["signers"].append(second)
        with self.assertRaisesRegex(ValueError, "signers contain duplicate subject IDs"):
            parse_unverified_receipt(encode(document))

    def test_custodian_cannot_also_be_a_signer(self):
        document = valid_document()
        document["custodians"][0]["subject_id"] = document["signers"][0]["subject_id"]
        with self.assertRaisesRegex(ValueError, "signer and custodian claims must be separate"):
            parse_unverified_receipt(encode(document))

    def test_receipt_issuer_cannot_also_be_a_signer(self):
        document = valid_document()
        document["receipt_attestation"]["issuer_id"] = document["signers"][0]["subject_id"]
        with self.assertRaisesRegex(
            ValueError,
            "issuer must be separate from signers, custodians, and generators",
        ):
            parse_unverified_receipt(encode(document))

    def test_receipt_attestation_cannot_reuse_a_signer_key(self):
        document = valid_document()
        document["receipt_attestation"]["key_id"] = document["signers"][0]["key_id"]
        with self.assertRaisesRegex(
            ValueError,
            "attestation key must be separate from signer keys",
        ):
            parse_unverified_receipt(encode(document))

    def test_receipt_issuer_cannot_also_be_a_generator(self):
        document = valid_document()
        document["receipt_attestation"]["issuer_id"] = document["output_seals"][0]["generator_id"]
        with self.assertRaisesRegex(
            ValueError,
            "issuer must be separate from signers, custodians, and generators",
        ):
            parse_unverified_receipt(encode(document))

    def test_receipt_issuer_cannot_also_be_a_custodian(self):
        document = valid_document()
        document["receipt_attestation"]["issuer_id"] = document["custodians"][0]["subject_id"]
        with self.assertRaisesRegex(
            ValueError,
            "issuer must be separate from signers, custodians, and generators",
        ):
            parse_unverified_receipt(encode(document))

    def test_artifact_cannot_claim_another_contest(self):
        document = valid_document()
        document["artifacts"][0]["contest_id"] = "12390"
        with self.assertRaisesRegex(ValueError, "bind to the receipt target"):
            parse_unverified_receipt(encode(document))

    def test_timestamp_must_be_canonical_utc(self):
        document = valid_document()
        document["target"]["draw_close_at_utc"] = "2026-11-22T21:00:00-06:00"
        with self.assertRaisesRegex(ValueError, "ending in Z"):
            parse_unverified_receipt(encode(document))

    def test_invalid_calendar_timestamp_is_rejected(self):
        document = valid_document()
        document["target"]["draw_close_at_utc"] = "2026-02-30T03:00:00Z"
        with self.assertRaisesRegex(ValueError, "valid calendar"):
            parse_unverified_receipt(encode(document))

    def test_noncanonical_base64_attestation_is_rejected(self):
        document = valid_document()
        document["receipt_attestation"]["signature_b64"] = "not-base64!"
        with self.assertRaisesRegex(ValueError, "invalid base64"):
            parse_unverified_receipt(encode(document))

    def test_wrong_ed25519_signature_length_is_rejected(self):
        document = valid_document()
        document["receipt_attestation"]["signature_b64"] = base64.b64encode(b"short").decode("ascii")
        with self.assertRaisesRegex(ValueError, "exactly 64"):
            parse_unverified_receipt(encode(document))

    def test_json_nan_is_rejected(self):
        raw = encode(valid_document()).replace(b'"byte_length":1024', b'"byte_length":NaN')
        with self.assertRaisesRegex(ValueError, "non-standard JSON constant"):
            parse_unverified_receipt(raw)

    def test_finite_and_overflowing_json_floats_are_rejected_at_decode_boundary(self):
        for token in (b"1024.0", b"1e999999"):
            with self.subTest(token=token):
                raw = encode(valid_document()).replace(b'"byte_length":1024', b'"byte_length":' + token)
                with self.assertRaisesRegex(
                    ValueError,
                    "floating-point JSON numbers are not accepted",
                ):
                    parse_unverified_receipt(raw)

    def test_signed_64_bit_json_integer_boundary_is_enforced_at_decode(self):
        maximum = (1 << 63) - 1
        document = valid_document()
        document["artifacts"][0]["byte_length"] = maximum
        parsed = parse_unverified_receipt(encode(document))
        self.assertEqual(parsed.artifacts[0].byte_length, maximum)

        for token in (b"9223372036854775808", b"-9223372036854775809", b"9" * 5000):
            with self.subTest(token_length=len(token)):
                raw = encode(valid_document()).replace(
                    b'"byte_length":1024', b'"byte_length":' + token
                )
                with self.assertRaisesRegex(ValueError, "signed 64-bit range"):
                    parse_unverified_receipt(raw)

    def test_non_utf8_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "valid UTF-8"):
            parse_unverified_receipt(b"\xff")

    def test_bytearray_input_is_not_silently_coerced(self):
        with self.assertRaisesRegex(TypeError, "exact bytes"):
            parse_unverified_receipt(bytearray(encode(valid_document())))

    def test_oversized_receipt_is_rejected_before_json_parse(self):
        raw = b" " * (MAX_TRUST_RECEIPT_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "must contain 1"):
            parse_unverified_receipt(raw)

    def test_duplicate_trusted_time_authority_event_identity_is_rejected(self):
        document = valid_document()
        duplicate = copy.deepcopy(document["trusted_time_proofs"][0])
        duplicate["event_at_utc"] = "2026-11-23T02:51:00Z"
        duplicate["proof_sha256"] = digest("5")
        document["trusted_time_proofs"].append(duplicate)
        with self.assertRaisesRegex(
            ValueError,
            "duplicate authority/event identities",
        ):
            parse_unverified_receipt(encode(document))

    def test_same_event_id_from_distinct_time_authorities_is_not_collapsed(self):
        document = valid_document()
        other_authority = copy.deepcopy(document["trusted_time_proofs"][0])
        other_authority["authority_id"] = "tsa-independent-test"
        other_authority["proof_sha256"] = digest("5")
        document["trusted_time_proofs"].append(other_authority)
        parsed = parse_unverified_receipt(encode(document))
        self.assertEqual(len(parsed.trusted_time_proofs), 2)

    def test_receipt_arrays_cannot_be_empty_or_unbounded(self):
        document = valid_document()
        document["trusted_time_proofs"] = []
        with self.assertRaisesRegex(ValueError, "1..4096"):
            parse_unverified_receipt(encode(document))


if __name__ == "__main__":
    unittest.main()
