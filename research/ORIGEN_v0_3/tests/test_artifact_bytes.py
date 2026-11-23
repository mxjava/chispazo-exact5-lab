"""Tests for byte-level integrity checks; no provenance is inferred."""
from __future__ import annotations

import hashlib
import unittest

from origen.artifact_bytes import verify_declared_artifact_bytes
from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from test_physical_evidence_manifest_v1 import encode, valid_document


class TestArtifactByteIntegrity(unittest.TestCase):
    def make_case(self):
        document = valid_document()
        payloads = {}
        replacements = {}
        for index, artifact in enumerate(document["artifacts"]):
            payload = f"original-artifact-{index}".encode("ascii")
            digest = hashlib.sha256(payload).hexdigest()
            replacements[artifact["sha256"]] = digest
            artifact["sha256"] = digest
            artifact["byte_length"] = len(payload)
            payloads[digest] = payload
        for signature in document["signatures"]:
            signature["artifact_sha256"] = replacements[signature["artifact_sha256"]]
        for event in document["custody_events"]:
            event["artifact_sha256"] = replacements[event["artifact_sha256"]]
        manifest = parse_unverified_physical_manifest(encode(document))
        return manifest, payloads

    def test_exact_original_byte_set_passes_digest_and_length_checks(self):
        manifest, payloads = self.make_case()
        result = verify_declared_artifact_bytes(manifest, payloads)
        self.assertEqual(len(result), len(manifest.artifacts))
        self.assertEqual({item.sha256 for item in result}, set(payloads))

    def test_modified_bytes_fail_sha256_check(self):
        manifest, payloads = self.make_case()
        digest = next(iter(payloads))
        payloads[digest] += b"tampered"
        with self.assertRaisesRegex(ValueError, "byte length mismatch|SHA-256 mismatch"):
            verify_declared_artifact_bytes(manifest, payloads)

    def test_same_length_modified_bytes_fail_sha256_check(self):
        manifest, payloads = self.make_case()
        digest, payload = next(iter(payloads.items()))
        payloads[digest] = bytes([payload[0] ^ 1]) + payload[1:]
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_declared_artifact_bytes(manifest, payloads)

    def test_missing_artifact_fails_closed(self):
        manifest, payloads = self.make_case()
        payloads.pop(next(iter(payloads)))
        with self.assertRaisesRegex(ValueError, "byte set mismatch"):
            verify_declared_artifact_bytes(manifest, payloads)

    def test_unexpected_artifact_fails_closed(self):
        manifest, payloads = self.make_case()
        payloads["0" * 64] = b"unexpected"
        with self.assertRaisesRegex(ValueError, "byte set mismatch"):
            verify_declared_artifact_bytes(manifest, payloads)

    def test_mutable_artifact_buffer_is_rejected(self):
        manifest, payloads = self.make_case()
        digest = next(iter(payloads))
        payloads[digest] = bytearray(payloads[digest])
        with self.assertRaisesRegex(TypeError, "exact immutable bytes"):
            verify_declared_artifact_bytes(manifest, payloads)

    def test_non_exact_manifest_type_is_rejected(self):
        with self.assertRaisesRegex(TypeError, "exact UnverifiedPhysicalEvidenceManifest"):
            verify_declared_artifact_bytes(object(), {})

    def test_non_dict_mapping_is_rejected(self):
        manifest, payloads = self.make_case()
        with self.assertRaisesRegex(TypeError, "exact dict"):
            verify_declared_artifact_bytes(manifest, payloads.items())


if __name__ == "__main__":
    unittest.main()
