from __future__ import annotations

import csv
import io
import tempfile
import unittest
from pathlib import Path

from origen.physical_intake_v2 import (
    MAX_V2_INTAKE_ROWS, V2_REQUIRED_COLUMNS, evaluate_temporal_csv, evaluate_temporal_eligibility,
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
    declared_custody_refs={"RECEIPT-1"},
    declared_timestamp_refs={"TSA-1"},
    declared_source_refs={"DOC-12300"},
    declared_continuity_targets={"12301"},
)


class PhysicalIntakeV2Tests(unittest.TestCase):
    def test_rows_are_snapshotted_when_consumed_from_mutating_iterable(self):
        rows = rows_for_target()
        first_row = rows[0]

        def mutating_rows():
            yield first_row
            # Mutate the caller-owned row only after the evaluator has consumed it.
            first_row["printed_number"] = "999"
            yield from rows[1:]

        result = evaluate_temporal_eligibility(mutating_rows(), **VERIFIED)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )
        self.assertNotIn("INVALID_PRINTED_NUMBER", result["targets"]["12301"]["reasons"])

    def test_iterator_failure_after_partial_intake_is_controlled_rejection(self):
        rows = rows_for_target()

        def interrupted_rows():
            yield rows[0]
            raise RuntimeError("synthetic source stream interruption")

        with self.assertRaisesRegex(
            ValueError,
            r"intake iterable failed after row 1",
        ):
            evaluate_temporal_eligibility(interrupted_rows(), **VERIFIED)

    def test_iterable_initialization_failure_is_controlled_rejection(self):
        class UnreadableRows:
            def __iter__(self):
                raise RuntimeError("synthetic iterator initialization failure")

        with self.assertRaisesRegex(
            ValueError,
            r"intake rows are not a readable iterable",
        ):
            evaluate_temporal_eligibility(UnreadableRows(), **VERIFIED)

    def test_every_row_must_include_all_required_columns(self):
        rows = rows_for_target()
        del rows[1]["source_document_sha256"]
        with self.assertRaisesRegex(
            ValueError,
            r"row 2 missing required columns: source_document_sha256",
        ):
            evaluate_temporal_eligibility(rows, **VERIFIED)

    def test_intake_row_limit_stops_unbounded_iterable_before_exhaustion(self):
        row = rows_for_target()[0]

        def unbounded_rows():
            for _ in range(MAX_V2_INTAKE_ROWS + 1):
                yield row
            raise AssertionError("intake consumed beyond its configured row limit")

        with self.assertRaisesRegex(
            ValueError,
            rf"intake exceeds maximum {MAX_V2_INTAKE_ROWS} rows",
        ):
            evaluate_temporal_eligibility(unbounded_rows(), **VERIFIED)

    def test_custom_mapping_row_cannot_spoof_scalar_lookup(self):
        class SpoofedRow(dict):
            def __getitem__(self, key):
                if key == "mass_value":
                    return "4.700"
                return super().__getitem__(key)

        rows = rows_for_target()
        rows[0]["mass_value"] = object()
        rows[0] = SpoofedRow(rows[0])
        with self.assertRaises(ValueError):
            evaluate_temporal_eligibility(rows, **VERIFIED)

    def test_mass_object_cannot_spoof_numeric_text_through_str(self):
        class SpoofedNumeric:
            def __str__(self):
                return "4.700"

        rows = rows_for_target()
        rows[0]["mass_value"] = SpoofedNumeric()
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn(
            "INVALID_MASS_OR_RESOLUTION",
            result["targets"]["12301"]["reasons"],
        )
        self.assertNotEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_printed_number_object_cannot_spoof_integer_through_str(self):
        class SpoofedScalar:
            def __str__(self):
                return "1"

        rows = rows_for_target()
        rows[0]["printed_number"] = SpoofedScalar()
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("INVALID_PRINTED_NUMBER", reasons)
        self.assertIn("INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET", reasons)
        self.assertNotEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_hash_object_cannot_spoof_sha256_through_str(self):
        class SpoofedDigest:
            def __str__(self):
                return "b" * 64

        rows = rows_for_target()
        rows[0]["source_document_sha256"] = SpoofedDigest()
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("INVALID_SOURCE_SHA256", reasons)
        self.assertIn("EVIDENCE_DOCUMENT_SET_CONFLICT", reasons)
        self.assertNotEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_all_digest_fields_reject_objects_that_stringify_to_sha256(self):
        class SpoofedDigest:
            def __init__(self, rendered):
                self.rendered = rendered

            def __str__(self):
                return self.rendered

        cases = (
            ("custody_receipt_sha256", "c" * 64, "INVALID_CUSTODY_RECEIPT_SHA256"),
            ("calibration_certificate_sha256", "a" * 64, "INVALID_CALIBRATION_SHA256"),
        )
        for field, rendered, expected_reason in cases:
            with self.subTest(field=field):
                rows = rows_for_target()
                rows[0][field] = SpoofedDigest(rendered)
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                reasons = result["targets"]["12301"]["reasons"]
                self.assertIn(expected_reason, reasons)
                self.assertIn("EVIDENCE_DOCUMENT_SET_CONFLICT", reasons)
                self.assertNotEqual(
                    result["targets"]["12301"]["predictive_eligibility"],
                    "STRUCTURAL_PRE_CLOSE_ONLY",
                )

    def test_mass_unit_object_cannot_spoof_gram_unit_through_str(self):
        class SpoofedUnit:
            def __str__(self):
                return "g"

        rows = rows_for_target()
        rows[0]["mass_unit"] = SpoofedUnit()
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn(
            "UNSUPPORTED_MASS_UNIT",
            result["targets"]["12301"]["reasons"],
        )
        self.assertNotEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_timestamp_string_subclass_cannot_spoof_valid_time(self):
        class SpoofedTimestamp(str):
            def strip(self, *args, **kwargs):
                return "2026-11-20T21:15:00-06:00"

            def replace(self, old, new, *args, **kwargs):
                return "2026-11-20T21:15:00-06:00"

        rows = rows_for_target()
        rows[0]["evidence_available_at"] = SpoofedTimestamp("attacker-controlled")
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn(
            "INVALID_OR_MISSING_TIMESTAMP_OR_PROVENANCE",
            result["targets"]["12301"]["reasons"],
        )
        self.assertNotEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_malformed_declared_reference_containers_fail_closed(self):
        class SpoofedReference(str):
            def __hash__(self):
                return hash("RECEIPT-1")

            def __eq__(self, other):
                return other == "RECEIPT-1"

        invalid_values = (
            "prefixRECEIPT-1suffix",  # would pass substring membership in the old code
            ["RECEIPT-1"],
            {"RECEIPT-1", 7},
            {""},
            {" RECEIPT-1 "},
            {SpoofedReference("ATTACKER-CONTROLLED")},
        )
        for invalid in invalid_values:
            with self.subTest(invalid=repr(invalid)):
                with self.assertRaises(ValueError):
                    evaluate_temporal_eligibility(
                        rows_for_target(),
                        declared_custody_refs=invalid,
                        declared_timestamp_refs=VERIFIED["declared_timestamp_refs"],
                        declared_source_refs=VERIFIED["declared_source_refs"],
                        declared_continuity_targets=VERIFIED["declared_continuity_targets"],
                    )

    def test_frozenset_declarations_remain_structural_only(self):
        result = evaluate_temporal_eligibility(
            rows_for_target(),
            declared_custody_refs=frozenset({"RECEIPT-1"}),
            declared_timestamp_refs=frozenset({"TSA-1"}),
            declared_source_refs=frozenset({"DOC-12300"}),
            declared_continuity_targets=frozenset({"12301"}),
        )
        self.assertEqual(result["status"], "STRUCTURAL_REVIEW_ONLY")
        self.assertEqual(
            result["authentication_status"],
            "NOT_AUTHENTICATED_BY_THIS_MODULE",
        )
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

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

    def test_source_contest_id_must_be_canonical_and_prior_to_target(self):
        # Timestamps alone must not allow a future, equal, padded, or nonnumeric
        # contest identifier to masquerade as the prior source draw.
        cases = (
            ("12302", "12301"),
            ("12301", "12301"),
            ("not-numeric", "12301"),
            ("012300", "12301"),
            ("12300", "not-numeric"),
        )
        for source_id, target_id in cases:
            with self.subTest(source_id=source_id, target_id=target_id):
                rows = rows_for_target()
                for row in rows:
                    row["source_contest_id"] = source_id
                    row["contest_id"] = source_id
                    row["target_contest_id"] = target_id
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                target = result["targets"][target_id]
                self.assertIn("CONTEST_ID_ORDER_INVALID", target["reasons"])
                self.assertEqual(target["predictive_eligibility"], "BLOCKED_CONTINUITY")

    def test_caller_supplied_reference_strings_are_declarations_not_authentication(self):
        # These deliberately fabricated identifiers satisfy only structural membership.
        result = evaluate_temporal_eligibility(
            rows_for_target(),
            declared_custody_refs={"RECEIPT-1"},
            declared_timestamp_refs={"TSA-1"},
            declared_source_refs={"DOC-12300"},
            declared_continuity_targets={"12301"},
        )
        self.assertEqual(result["status"], "STRUCTURAL_REVIEW_ONLY")
        self.assertEqual(
            result["authentication_status"],
            "NOT_AUTHENTICATED_BY_THIS_MODULE",
        )
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )
        self.assertNotIn("authenticated", result)
        self.assertNotIn("authenticated", result["targets"]["12301"])

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
            declared_custody_refs={"RECEIPT-1"},
            declared_timestamp_refs={"TSA-1"},
            declared_source_refs={"DOC-12300"},
        )
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_utc_normalization_overflow_fails_closed(self):
        # A syntactically valid offset can normalize outside datetime's year range.
        # This must become a provenance block, not escape as OverflowError.
        cases = (
            "0001-01-01T00:00:00+23:59",
            "9999-12-31T23:59:59-23:59",
        )
        for timestamp in cases:
            with self.subTest(timestamp=timestamp):
                rows = rows_for_target()
                rows[0]["target_draw_close_at"] = timestamp
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                target = result["targets"]["12301"]
                self.assertIn(
                    "INVALID_OR_MISSING_TIMESTAMP_OR_PROVENANCE",
                    target["reasons"],
                )
                self.assertEqual(
                    target["predictive_eligibility"],
                    "BLOCKED_PROVENANCE",
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

    def test_blank_sphere_id_is_rejected_even_when_unique_count_is_28(self):
        rows = rows_for_target()
        rows[0]["sphere_id"] = "   "
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn(
            "INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET",
            result["targets"]["12301"]["reasons"],
        )
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_blank_source_contest_id_is_rejected(self):
        rows = rows_for_target()
        for row in rows:
            row["source_contest_id"] = " "
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("SOURCE_CONTEST_CONFLICT", result["targets"]["12301"]["reasons"])
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_contest_id_alias_must_match_source_contest_id(self):
        rows = rows_for_target()
        rows[0]["contest_id"] = "12302"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("CONTEST_ID_ALIAS_MISMATCH", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_draw_date_must_match_source_close_and_draw_dates(self):
        rows = rows_for_target()
        rows[0]["draw_date"] = "2026-11-21"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("DRAW_DATE_SOURCE_DRAW_MISMATCH", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_draw_date_accepts_utc_draw_timestamp_for_same_source_local_date(self):
        rows = rows_for_target()
        for row in rows:
            row["source_draw_at"] = "2026-11-21T03:00:00Z"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertNotIn("DRAW_DATE_SOURCE_DRAW_MISMATCH", reasons)
        self.assertNotIn("CLASSIC_SCHEDULE_TIME_MISMATCH", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )

    def test_draw_date_requires_canonical_valid_iso_calendar_date(self):
        for invalid_date in ("2026-1-20", "2026-02-30", "2026-11-20 ", "", None):
            with self.subTest(invalid_date=invalid_date):
                rows = rows_for_target()
                rows[0]["draw_date"] = invalid_date
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                reasons = result["targets"]["12301"]["reasons"]
                self.assertIn("INVALID_DRAW_DATE", reasons)
                self.assertEqual(
                    result["targets"]["12301"]["predictive_eligibility"],
                    "BLOCKED_CONTINUITY",
                )


    def test_classic_modality_rejects_de_las_tres_1500_source_and_target_slots(self):
        rows = rows_for_target()
        for row in rows:
            row.update({
                "set_assigned_at": "2026-11-20T14:00:00-06:00",
                "draw_close_at": "2026-11-20T14:45:00-06:00",
                "measurement_at": "2026-11-20T14:55:00-06:00",
                "source_signed_at": "2026-11-20T14:58:00-06:00",
                "source_draw_at": "2026-11-20T15:00:00-06:00",
                "evidence_available_at": "2026-11-20T15:01:00-06:00",
                "custody_received_at": "2026-11-20T15:02:00-06:00",
                "target_draw_close_at": "2026-11-21T14:00:00-06:00",
                "target_draw_at": "2026-11-21T15:00:00-06:00",
                "mapping_valid_from": "2026-11-20T13:00:00-06:00",
                "mapping_valid_to": "2026-11-21T15:30:00-06:00",
            })
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("CLASSIC_SCHEDULE_TIME_MISMATCH", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )


    def test_utc_2100_is_not_misread_as_classic_local_2100(self):
        rows = rows_for_target()
        for row in rows:
            row["target_draw_close_at"] = "2026-11-21T14:00:00-06:00"
            # 21:00 UTC is 15:00 in America/Mexico_City, i.e. De las Tres.
            row["target_draw_at"] = "2026-11-21T21:00:00Z"
            row["mapping_valid_to"] = "2026-11-21T15:30:00-06:00"
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("CLASSIC_SCHEDULE_TIME_MISMATCH", reasons)
        self.assertEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "BLOCKED_CONTINUITY",
        )

    def test_none_values_are_not_stringified_into_valid_provenance_refs(self):
        cases = (
            ("source_document_ref", "declared_source_refs", "PRIMARY_SOURCE_MISSING"),
            ("custody_receipt_ref", "declared_custody_refs", "CUSTODY_RECEIPT_MISSING"),
            ("trusted_timestamp_ref", "declared_timestamp_refs", "TRUSTED_TIMESTAMP_MISSING"),
        )
        for field, declaration, expected_reason in cases:
            with self.subTest(field=field):
                rows = rows_for_target()
                for row in rows:
                    row[field] = None
                declarations = dict(VERIFIED)
                declarations[declaration] = {"None"}
                result = evaluate_temporal_eligibility(rows, **declarations)
                reasons = result["targets"]["12301"]["reasons"]
                self.assertIn(expected_reason, reasons)
                self.assertNotEqual(
                    result["targets"]["12301"]["predictive_eligibility"],
                    "STRUCTURAL_PRE_CLOSE_ONLY",
                )

    def test_none_sphere_and_source_contest_ids_are_rejected(self):
        rows = rows_for_target()
        rows[0]["sphere_id"] = None
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn(
            "INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET",
            result["targets"]["12301"]["reasons"],
        )

        rows = rows_for_target()
        for row in rows:
            row["source_contest_id"] = None
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        self.assertIn("SOURCE_CONTEST_CONFLICT", result["targets"]["12301"]["reasons"])

    def test_none_target_contest_id_is_rejected(self):
        rows = rows_for_target()
        for row in rows:
            row["target_contest_id"] = None
        with self.assertRaises(ValueError):
            evaluate_temporal_eligibility(rows, **VERIFIED)

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



    def test_csv_duplicate_headers_are_rejected_before_dictreader_overwrite(self):
        rows = rows_for_target()
        for row in rows:
            row["modality"] = "DE LAS TRES"
        headers = list(V2_REQUIRED_COLUMNS) + ["modality"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate-header.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow(
                        [row[column] for column in V2_REQUIRED_COLUMNS] + ["CLASSIC"]
                    )
            with self.assertRaisesRegex(ValueError, "CSV headers must be unique"):
                evaluate_temporal_csv(path, **VERIFIED)


    def test_mapping_rows_reject_unrecognized_v2_columns(self):
        rows = rows_for_target()
        rows[0]["authenticated_provenance"] = "true"
        with self.assertRaisesRegex(
            ValueError,
            "row 1 has unexpected columns: authenticated_provenance",
        ):
            evaluate_temporal_eligibility(rows, **VERIFIED)

    def test_csv_rejects_unrecognized_v2_header_before_row_processing(self):
        rows = rows_for_target()
        headers = list(V2_REQUIRED_COLUMNS) + ["authenticated_provenance"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unknown-header.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                for row in rows:
                    writer.writerow(
                        [row[column] for column in V2_REQUIRED_COLUMNS] + ["true"]
                    )
            with self.assertRaisesRegex(
                ValueError,
                "unexpected columns: authenticated_provenance",
            ):
                evaluate_temporal_csv(path, **VERIFIED)


    def test_printed_sphere_number_requires_canonical_decimal_1_through_28(self):
        invalid_values = ("01", "+1", " 1", "1 ", "0", "29", "1.0", "")
        for value in invalid_values:
            with self.subTest(value=value):
                rows = rows_for_target()
                rows[0]["printed_number"] = value
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                reasons = result["targets"]["12301"]["reasons"]
                self.assertIn("INVALID_PRINTED_NUMBER", reasons)
                self.assertIn("INCOMPLETE_OR_DUPLICATE_28_SPHERE_SET", reasons)
                self.assertNotEqual(
                    result["targets"]["12301"]["predictive_eligibility"],
                    "STRUCTURAL_PRE_CLOSE_ONLY",
                )


    def test_timestamps_require_canonical_extended_iso8601_and_offset(self):
        invalid_values = (
            "2026-11-20 21:00:00-06:00",
            "2026-11-20T21:00-06:00",
            "2026-11-20T21:00:00-0600",
            "2026-11-20T21:00:00",
            "2026-11-20T21:00:00-06:00 ",
        )
        for value in invalid_values:
            with self.subTest(value=value):
                rows = rows_for_target()
                for row in rows:
                    row["source_signed_at"] = value
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                reasons = result["targets"]["12301"]["reasons"]
                self.assertIn("INVALID_OR_MISSING_TIMESTAMP_OR_PROVENANCE", reasons)
                self.assertNotEqual(
                    result["targets"]["12301"]["predictive_eligibility"],
                    "STRUCTURAL_PRE_CLOSE_ONLY",
                )

    def test_unknown_negative_zero_timezone_offset_is_rejected(self):
        timestamp_fields = (
            "draw_close_at", "target_draw_close_at", "target_draw_at",
            "set_assigned_at", "measurement_at", "calibration_valid_from",
            "calibration_valid_to", "mapping_valid_from", "mapping_valid_to",
            "source_draw_at", "source_signed_at", "evidence_available_at",
            "custody_received_at",
        )
        for field in timestamp_fields:
            with self.subTest(field=field):
                rows = rows_for_target()
                for row in rows:
                    row[field] = row[field][:-6] + "-00:00"
                result = evaluate_temporal_eligibility(rows, **VERIFIED)
                reasons = result["targets"]["12301"]["reasons"]
                self.assertIn(
                    "INVALID_OR_MISSING_TIMESTAMP_OR_PROVENANCE",
                    reasons,
                )
                self.assertNotEqual(
                    result["targets"]["12301"]["predictive_eligibility"],
                    "STRUCTURAL_PRE_CLOSE_ONLY",
                )

    def test_sha256_fields_reject_surrounding_whitespace(self):
        rows = rows_for_target()
        rows[0]["source_document_sha256"] = " " + ("b" * 64) + " "
        rows[0]["custody_receipt_sha256"] = " " + ("c" * 64) + " "
        rows[0]["calibration_certificate_sha256"] = " " + ("a" * 64) + " "
        result = evaluate_temporal_eligibility(rows, **VERIFIED)
        reasons = result["targets"]["12301"]["reasons"]
        self.assertIn("INVALID_SOURCE_SHA256", reasons)
        self.assertIn("INVALID_CUSTODY_RECEIPT_SHA256", reasons)
        self.assertIn("INVALID_CALIBRATION_SHA256", reasons)
        self.assertNotEqual(
            result["targets"]["12301"]["predictive_eligibility"],
            "STRUCTURAL_PRE_CLOSE_ONLY",
        )


    def test_csv_unterminated_quote_is_rejected_instead_of_silently_accepted(self):
        rows = rows_for_target()
        headers = list(V2_REQUIRED_COLUMNS) + ["optional_notes"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unterminated-quote.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                for row in rows:
                    buffer = io.StringIO(newline="")
                    csv.writer(buffer).writerow(
                        [row[column] for column in V2_REQUIRED_COLUMNS]
                    )
                    stream.write(
                        buffer.getvalue().rstrip("\r\n") + ',"unterminated\r\n'
                    )
            with self.assertRaisesRegex(
                ValueError,
                r"intake iterable failed after row 0",
            ) as raised:
                evaluate_temporal_csv(path, **VERIFIED)
            self.assertIsInstance(raised.exception.__cause__, csv.Error)

if __name__ == "__main__":
    unittest.main()
