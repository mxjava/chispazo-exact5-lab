"""Adversarial tests for mapping artifact claim/byte binding."""
import hashlib
import unittest

from origen.mapping_artifact_binding import verify_mapping_artifact_byte_binding
from origen.physical_evidence_manifest_v1 import PhysicalArtifactClaim


class MappingArtifactByteBindingTests(unittest.TestCase):
    def setUp(self):
        self.original = b"opaque original mapping register bytes"
        self.claim = PhysicalArtifactClaim(
            artifact_type="SPHERE-NUMBER-MAPPING-REGISTER",
            sha256=hashlib.sha256(self.original).hexdigest(),
            byte_length=len(self.original),
            contest_id="12300",
            source_id="OFFICIAL-SOURCE",
            source_object_id="MAPPING-REGISTER-12300",
            media_type="application/pdf",
        )
        self.rows = [
            {
                "target_contest_id": "12300",
                "mapping_artifact_ref": "MAPPING-REGISTER-12300",
                "mapping_artifact_sha256": self.claim.sha256,
                "sphere_id": f"SPHERE-{number:02d}",
                "printed_number": str(number),
            }
            for number in range(1, 29)
        ]

    def test_exact_28_rows_bind_to_manifest_claim_and_original_bytes(self):
        result = verify_mapping_artifact_byte_binding(
            self.rows, self.claim, self.original
        )
        self.assertEqual(result.status, "MAPPING_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED")
        self.assertEqual(result.row_count, 28)

    def test_wrong_original_bytes_fail_digest_check(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verify_mapping_artifact_byte_binding(
                self.rows, self.claim, b"X" * len(self.original)
            )

    def test_wrong_claim_type_fails(self):
        wrong = PhysicalArtifactClaim(
            artifact_type="WEIGHING-STRIP",
            sha256=self.claim.sha256,
            byte_length=self.claim.byte_length,
            contest_id="12300",
            source_id="OFFICIAL-SOURCE",
            source_object_id="MAPPING-REGISTER-12300",
            media_type="application/pdf",
        )
        with self.assertRaisesRegex(ValueError, "SPHERE-NUMBER-MAPPING-REGISTER"):
            verify_mapping_artifact_byte_binding(self.rows, wrong, self.original)

    def test_manifest_reference_mismatch_fails(self):
        rows = [dict(row) for row in self.rows]
        rows[0]["mapping_artifact_ref"] = "GENERIC-SOURCE-DOC"
        with self.assertRaisesRegex(ValueError, "reference does not match"):
            verify_mapping_artifact_byte_binding(rows, self.claim, self.original)

    def test_manifest_digest_mismatch_fails(self):
        rows = [dict(row) for row in self.rows]
        rows[-1]["mapping_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest does not match"):
            verify_mapping_artifact_byte_binding(rows, self.claim, self.original)

    def test_bijective_reassignment_is_not_claimed_to_be_detected_by_opaque_byte_binding(self):
        # The helper binds bytes and references; it deliberately cannot parse
        # institutionally authoritative mapping content or authenticate pairs.
        rows = [dict(row) for row in self.rows]
        rows[0]["printed_number"], rows[1]["printed_number"] = (
            rows[1]["printed_number"], rows[0]["printed_number"]
        )
        result = verify_mapping_artifact_byte_binding(
            rows, self.claim, self.original
        )
        self.assertEqual(result.status, "MAPPING_ARTIFACT_BYTES_MATCHED_NOT_AUTHENTICATED")

    def test_incomplete_or_duplicate_rows_fail(self):
        with self.assertRaisesRegex(ValueError, "exactly 28"):
            verify_mapping_artifact_byte_binding(
                self.rows[:-1], self.claim, self.original
            )
        rows = [dict(row) for row in self.rows]
        rows[-1]["sphere_id"] = rows[0]["sphere_id"]
        with self.assertRaisesRegex(ValueError, "28 unique"):
            verify_mapping_artifact_byte_binding(rows, self.claim, self.original)


if __name__ == "__main__":
    unittest.main()
