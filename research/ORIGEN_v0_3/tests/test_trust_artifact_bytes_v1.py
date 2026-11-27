"""Adversarial tests for receipt-to-original-artifact byte binding.

All keys, receipts, and payloads in this module are synthetic fixtures. They do
not represent Lotería Nacional records or institutional trust anchors.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.trust_artifact_bytes_v1 import (
    ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED,
    SIGNATURE_AND_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED,
    verify_independent_provenance_with_artifacts,
    verify_receipt_artifact_bytes,
)
from test_independent_trust_adapter import NOW, raw_public_key, verified_policy
from test_trust_receipt_v1 import encode, valid_document


def signed_receipt(document: dict, issuer: Ed25519PrivateKey) -> bytes:
    unsigned = copy.deepcopy(document)
    unsigned["receipt_attestation"].pop("signature_b64")
    payload = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        issuer.sign(payload)
    ).decode("ascii")
    return encode(document)


def make_case(required_artifact_types=("sphere-measurement-register",)):
    payload = b"synthetic-original-evidence-bytes"
    document = valid_document()
    digest = hashlib.sha256(payload).hexdigest()
    document["artifacts"][0]["sha256"] = digest
    document["artifacts"][0]["byte_length"] = len(payload)
    issuer = Ed25519PrivateKey.generate()
    raw = signed_receipt(document, issuer)
    policy = verified_policy(
        raw_public_key(issuer), required_artifact_types=required_artifact_types
    )
    return raw, policy, digest, payload


class TestReceiptArtifactBytesV1(unittest.TestCase):
    def check(self, raw, policy, payloads):
        return verify_independent_provenance_with_artifacts(
            raw,
            verified_trust_policy=policy,
            verification_time=NOW,
            artifact_bytes_by_sha256=payloads,
        )

    def test_signed_receipt_and_exact_original_bytes_match_but_provenance_stays_blocked(self):
        raw, policy, digest, payload = make_case()
        result = self.check(raw, policy, {digest: payload})
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(
            result.status,
            SIGNATURE_AND_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED,
        )
        self.assertEqual(result.receipt_sha256, hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(result.artifact_matches), 1)
        self.assertEqual(result.artifact_matches[0].sha256, digest)

    def test_receipt_missing_signed_policy_required_artifact_type_fails(self):
        raw, policy, digest, payload = make_case(
            required_artifact_types=(
                "sphere-measurement-register",
                "draw-acta",
            )
        )
        with self.assertRaisesRegex(
            ValueError,
            "receipt omits trust-policy-required artifact types: \\['draw-acta'\\]",
        ):
            self.check(raw, policy, {digest: payload})

    def test_same_length_modified_artifact_bytes_fail(self):
        raw, policy, digest, payload = make_case()
        changed = bytes([payload[0] ^ 1]) + payload[1:]
        self.assertEqual(len(changed), len(payload))
        with self.assertRaisesRegex(ValueError, "artifact SHA-256 mismatch"):
            self.check(raw, policy, {digest: changed})

    def test_wrong_artifact_length_fails_before_digest_comparison(self):
        raw, policy, digest, payload = make_case()
        with self.assertRaisesRegex(ValueError, "byte length mismatch"):
            self.check(raw, policy, {digest: payload + b"x"})

    def test_missing_artifact_fails_closed(self):
        raw, policy, _, _ = make_case()
        with self.assertRaisesRegex(ValueError, "byte set mismatch"):
            self.check(raw, policy, {})

    def test_extra_artifact_fails_closed(self):
        raw, policy, digest, payload = make_case()
        with self.assertRaisesRegex(ValueError, "byte set mismatch"):
            self.check(raw, policy, {digest: payload, "0" * 64: b"extra"})

    def test_mutable_artifact_buffer_is_rejected(self):
        raw, policy, digest, payload = make_case()
        with self.assertRaisesRegex(TypeError, "exact immutable bytes"):
            self.check(raw, policy, {digest: bytearray(payload)})

    def test_memoryview_artifact_buffer_is_rejected(self):
        raw, policy, digest, payload = make_case()
        with self.assertRaisesRegex(TypeError, "exact immutable bytes"):
            self.check(raw, policy, {digest: memoryview(payload)})

    def test_bytes_subclass_is_rejected(self):
        raw, policy, digest, payload = make_case()

        class ArtifactBytes(bytes):
            pass

        with self.assertRaisesRegex(TypeError, "exact immutable bytes"):
            self.check(raw, policy, {digest: ArtifactBytes(payload)})

    def test_dict_subclass_is_rejected(self):
        raw, policy, digest, payload = make_case()

        class ArtifactMap(dict):
            pass

        with self.assertRaisesRegex(TypeError, "exact dict"):
            self.check(raw, policy, ArtifactMap({digest: payload}))

    def test_string_subclass_digest_key_is_rejected(self):
        raw, policy, digest, payload = make_case()

        class DigestKey(str):
            pass

        with self.assertRaisesRegex(TypeError, "exact built-in strings"):
            self.check(raw, policy, {DigestKey(digest): payload})

    def test_same_digest_with_conflicting_declared_lengths_is_rejected(self):
        raw, policy, digest, payload = make_case()
        document = json.loads(raw)
        duplicate = copy.deepcopy(document["artifacts"][0])
        duplicate["artifact_type"] = "second-evidence-type"
        duplicate["byte_length"] += 1
        document["artifacts"].append(duplicate)
        issuer = Ed25519PrivateKey.generate()
        # Rebuild a matching policy/receipt signer so the failure is specifically
        # the contradictory digest-length claim, not a signature mismatch.
        document["receipt_attestation"]["signature_b64"] = base64.b64encode(
            b"x" * 64
        ).decode("ascii")
        raw = signed_receipt(document, issuer)
        policy = verified_policy(raw_public_key(issuer))
        with self.assertRaisesRegex(ValueError, "one artifact digest cannot satisfy multiple distinct artifact types"):
            self.check(raw, policy, {digest: payload})

    def test_same_digest_cannot_satisfy_two_distinct_artifact_labels(self):
        raw, policy, digest, payload = make_case()
        document = json.loads(raw)
        duplicate = copy.deepcopy(document["artifacts"][0])
        duplicate["artifact_type"] = "second-evidence-type"
        document["artifacts"].append(duplicate)
        issuer = Ed25519PrivateKey.generate()
        raw = signed_receipt(document, issuer)
        policy = verified_policy(raw_public_key(issuer))
        with self.assertRaisesRegex(
            ValueError,
            "one artifact digest cannot satisfy multiple distinct artifact types",
        ):
            self.check(raw, policy, {digest: payload})

    def test_tampered_receipt_is_rejected_before_artifact_binding(self):
        raw, policy, digest, payload = make_case()
        document = json.loads(raw)
        document["artifacts"][0]["artifact_type"] = "substituted-evidence-type"
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.check(encode(document), policy, {digest: payload})

    def test_standalone_byte_check_explicitly_does_not_claim_authentication(self):
        payload = b"synthetic bytes only"
        document = valid_document()
        digest = hashlib.sha256(payload).hexdigest()
        document["artifacts"][0]["sha256"] = digest
        document["artifacts"][0]["byte_length"] = len(payload)
        result = verify_receipt_artifact_bytes(encode(document), {digest: payload})
        self.assertEqual(result.status, ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED)
        self.assertEqual(result.receipt_sha256, hashlib.sha256(encode(document)).hexdigest())

    def test_no_receipt_artifact_bytes_are_retained_in_result(self):
        raw, policy, digest, payload = make_case()
        result = self.check(raw, policy, {digest: payload})
        self.assertFalse(hasattr(result, "artifact_bytes_by_sha256"))
        self.assertFalse(hasattr(result.artifact_matches[0], "payload"))


if __name__ == "__main__":
    unittest.main()
