from __future__ import annotations

import unittest

from origen.physical_intake_v2 import (
    V2_REQUIRED_COLUMNS, evaluate_temporal_eligibility,
)


def rows_for_target(available="2026-11-20T21:15:00-06:00",
                    received="2026-11-20T21:16:00-06:00"):
    rows = []
    for number in range(1, 29):
        rows.append({
            "source_contest_id": "12300", "target_contest_id": "12301",
            "contest_id": "12300", "draw_date": "2026-11-20",
            "modality": "CLASSIC",
            "draw_close_at": "2026-11-20T20:45:00-06:00",
            "target_draw_close_at": "2026-11-21T19:00:00-06:00",
            "sphere_set_id": "SET-A", "set_assigned_at": "2026-11-20T17:00:00-06:00",
            "sphere_type": "Smartballs", "machine_id": "M-01",
            "machine_model": "Model-X", "sphere_id": f"SPH-{number:02d}",
            "printed_number": str(number), "mass_value": "4.700",
            "mass_unit": "g", "measurement_at": "2026-11-20T20:55:00-06:00",
            "measurement_resolution": "0.001", "scale_id": "SCALE-1",
            "calibration_valid_from": "2026-01-01T00:00:00-06:00",
            "calibration_valid_to": "2026-12-31T23:59:59-06:00",
            "calibration_certificate_sha256": "a" * 64,
            "mapping_valid_from": "2026-11-20T16:00:00-06:00",
            "mapping_valid_to": "2026-11-22T21:30:00-06:00",
            "source_draw_at": "2026-11-20T21:00:00-06:00",
            "target_draw_at": "2026-11-21T21:00:00-06:00",
            "source_document_sha256": "b" * 64,
            "source_document_ref": "DOC-12300",
            "source_signed_at": "2026-11-20T20:58:00-06:00",
            "source_signer_id": "SIGNER-1", "source_signature_ref": "SIG-1",
            "evidence_available_at": available, "custody_received_at": received,
            "custodian_id": "CUST-1", "custodian_role": "independent-archive",
            "custody_receipt_ref": "RECEIPT-1",
            "custody_receipt_sha256": "c" * 64,
            "trusted_timestamp_ref": "TSA-1",
        })
    return rows


VERIFIED = dict(
    verified_custody_refs={"RECEIPT-1"},
    verified_timestamp_refs={"TSA-1"},
    verified_source_refs={"DOC-12300"},
    verified_continuity_targets={"12301"},
)


class PhysicalIntakeV2Tests(unittest.TestCase):
    def test_structural_preclose_does_not_claim_independent_authentication(self):
        result = evaluate_temporal_eligibility(rows_for_target(), **VERIFIED)
        target = result["targets"]["12301"]
        self.assertEqual(result["status"], "STRUCTURAL_REVIEW_ONLY")
        self.assertEqual(
            result["authentication_status"],
            "NOT_AUTHENTICATED_BY_THIS_MODULE",
        )
        self.assertEqual(target["predictive_eligibility"], "STRUCTURAL_PRE_CLOSE_ONLY")
        self.assertEqual(target["reasons"], [])

    def test_measurement_before_close_but_receipt_after_target_close_is_ineligible(self):
        rows = rows_for_target(received="2026-11-21T19:00:00-06:00")
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "INELIGIBLE_POST_CLOSE",
        )

    def test_measurement_after_source_close_can_be_eligible_for_later_target(self):
        rows = rows_for_target()
        for row in rows:
            row["measurement_at"] = "2026-11-20T20:55:00-06:00"
            row["evidence_available_at"] = "2026-11-20T21:15:00-06:00"
            row["custody_received_at"] = "2026-11-20T21:16:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_missing_external_custody_and_clock_attestations_fail_closed(self):
        result = evaluate_temporal_eligibility(rows_for_target())
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("CUSTODY_NOT_INDEPENDENTLY_VERIFIED", reasons)
        self.assertIn("TIMESTAMP_NOT_INDEPENDENTLY_VERIFIED", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_PROVENANCE",
        )

    def test_missing_continuity_is_separate_block(self):
        result = evaluate_temporal_eligibility(
            rows_for_target(),
            verified_custody_refs={"RECEIPT-1"},
            verified_timestamp_refs={"TSA-1"},
            verified_source_refs={"DOC-12300"},
        )
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_naive_timestamp_blocks_provenance(self):
        rows = rows_for_target()
        rows[0]["evidence_available_at"] = "2026-11-20T18:00:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_PROVENANCE",
        )

    def test_inconsistent_target_close_is_blocked(self):
        rows = rows_for_target()
        rows[-1]["target_draw_close_at"] = "2026-11-21T20:00:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_PROVENANCE",
        )
        self.assertIn("TARGET_CLOSE_CONFLICT", result["targets"]["12301"]["reasons"])

    def test_template_contract_has_all_required_fields(self):
        self.assertEqual(len(V2_REQUIRED_COLUMNS), len(set(V2_REQUIRED_COLUMNS)))
        rows = rows_for_target()
        self.assertEqual(set(V2_REQUIRED_COLUMNS) - set(rows[0]), set())

    def test_incomplete_or_duplicate_sphere_set_is_blocked(self):
        rows = rows_for_target()
        rows[-1]["printed_number"] = "27"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET", result["targets"]["12301"]["reasons"])
        self.assertEqual(result["targets"]["12301"]["predictive_eligibility"], "BLOCKED_CONTINUITY")

    def test_non_classic_modality_is_not_eligible(self):
        rows = rows_for_target()
        rows[0]["modality"] = "DE LAS TRES"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("MODALITY_NOT_VERIFIED_CLASSIC", result["targets"]["12301"]["reasons"])

    def test_mapping_must_cover_target_draw(self):
        rows = rows_for_target()
        for row in rows:
            row["mapping_valid_to"] = "2026-11-21T20:59:59-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("MAPPING_NOT_VALID_AT_TARGET_DRAW", result["targets"]["12301"]["reasons"])
        self.assertEqual(result["targets"]["12301"]["predictive_eligibility"], "BLOCKED_CONTINUITY")
    def test_measurement_cannot_follow_source_draw(self):
        rows = rows_for_target()
        for row in rows:
            row["measurement_at"] = "2026-11-20T21:01:00-06:00"
            row["evidence_available_at"] = "2026-11-20T21:15:00-06:00"
            row["custody_received_at"] = "2026-11-20T21:16:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("MEASUREMENT_AFTER_SOURCE_DRAW", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_measurement_cannot_precede_source_close(self):
        rows = rows_for_target()
        for row in rows:
            row["measurement_at"] = "2026-11-20T20:40:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("MEASUREMENT_PRECEDES_SOURCE_CLOSE", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_source_draw_cannot_precede_source_close(self):
        rows = rows_for_target()
        for row in rows:
            row["source_draw_at"] = "2026-11-20T20:40:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("SOURCE_DRAW_PRECEDES_SOURCE_CLOSE", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_source_and_target_draw_timestamps_are_distinct(self):
        result = evaluate_temporal_eligibility(rows_for_target(), **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertNotIn("TARGET_DRAW_TIME_CONFLICT", reasons)
        self.assertNotIn("MAPPING_NOT_VALID_AT_TARGET_DRAW", reasons)

    def test_evidence_available_before_source_draw_is_allowed_after_signature(self):
        rows = rows_for_target(
            available="2026-11-20T20:59:00-06:00",
            received="2026-11-20T20:59:30-06:00",
        )
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_source_signature_must_follow_measurement_and_precede_source_draw(self):
        rows = rows_for_target()
        for row in rows:
            row["source_signed_at"] = "2026-11-20T21:01:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("SOURCE_SIGNED_AFTER_SOURCE_DRAW", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_source_signature_cannot_precede_measurement(self):
        rows = rows_for_target()
        for row in rows:
            row["source_signed_at"] = "2026-11-20T20:54:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("SOURCE_SIGNED_PRECEDES_MEASUREMENT", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_measurement_cannot_precede_set_assignment(self):
        rows = rows_for_target()
        for row in rows:
            row["set_assigned_at"] = "2026-11-20T17:20:00-06:00"
            row["measurement_at"] = "2026-11-20T17:10:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("BROKEN_EVIDENCE_TEMPORAL_ORDER", result["targets"]["12301"]["reasons"])

    def test_custody_cannot_precede_evidence_availability(self):
        rows = rows_for_target(available="2026-11-20T18:05:00-06:00",
                               received="2026-11-20T21:16:00-06:00")
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("BROKEN_EVIDENCE_AVAILABILITY_ORDER", result["targets"]["12301"]["reasons"])

    def test_source_must_be_signed_before_evidence_is_declared_available(self):
        rows = rows_for_target()
        for row in rows:
            row["source_signed_at"] = "2026-11-20T21:18:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("SOURCE_SIGNED_AFTER_EVIDENCE_AVAILABLE", result["targets"]["12301"]["reasons"])

    def test_invalid_mass_and_calibration_digest_are_blocked(self):
        rows = rows_for_target()
        rows[0]["mass_value"] = "nan"
        rows[1]["calibration_certificate_sha256"] = "not-a-digest"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("INVALID_MASS_OR_RESOLUTION", reasons)
        self.assertIn("INVALID_CALIBRATION_SHA256", reasons)

    def test_target_draw_cannot_precede_target_close(self):
        rows = rows_for_target()
        for row in rows:
            row["target_draw_at"] = "2026-11-21T18:59:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("TARGET_DRAW_TIME_CONFLICT", result["targets"]["12301"]["reasons"])

    def test_mixed_primary_document_hashes_are_blocked(self):
        rows = rows_for_target()
        rows[0]["source_document_sha256"] = "d" * 64
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("EVIDENCE_DOCUMENT_SET_CONFLICT", result["targets"]["12301"]["reasons"])
        self.assertEqual(result["targets"]["12301"]["predictive_eligibility"], "BLOCKED_CONTINUITY")

    def test_mapping_must_cover_set_assignment_as_well_as_draw(self):
        rows = rows_for_target()
        for row in rows:
            row["mapping_valid_from"] = "2026-11-20T17:05:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("MAPPING_NOT_VALID_AT_TARGET_DRAW", result["targets"]["12301"]["reasons"])

    def test_empty_input_is_not_success(self):
        self.assertEqual(evaluate_temporal_eligibility([])["status"], "EMPTY")


if __name__ == "__main__":
    unittest.main()
