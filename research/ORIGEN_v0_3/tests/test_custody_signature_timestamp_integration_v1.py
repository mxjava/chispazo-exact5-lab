"""Adversarial tests for non-circular V3 detached-signature timestamping.

All keys, certificates, receipts, records, signatures and timestamp tokens
are synthetic. These tests prove byte binding, not institutional provenance.
"""
from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from origen.custody_signature_timestamp_integration_v1 import (
    custody_signature_timestamp_event_id,
    verify_receipt_custody_signature_timestamp_v1,
)
from origen.independent_trust_adapter import ProvenanceStatus
from test_custody_receipt_verifier_v3 import (
    StatefulOffsetTimezone,
    bundle,
)
from test_rfc3161_tsa_verifier_v1 import _token
from test_trust_verifier_v1 import NOW


GEN_TIME = datetime(2026, 11, 23, 2, 50, tzinfo=timezone.utc)


def timestamped_bundle(
    *, gen_time=GEN_TIME, accuracy=None, timestamp_data=None, **bundle_options
):
    data = bundle(**bundle_options)
    target = (
        data["custody_signature_bytes"]
        if timestamp_data is None
        else timestamp_data
    )
    token, tsa_root = _token(
        data=target,
        accuracy=accuracy,
        gen_time=gen_time,
    )
    data.update({
        "timestamp_token_der": token,
        "pinned_tsa_root_certificate_der": tsa_root,
        "expected_tsa_root_sha256": hashlib.sha256(tsa_root).hexdigest(),
        "expected_nonce": 12345,
    })
    return data


def inspect_timestamp(data, **overrides):
    args = dict(data)
    args.pop("receipt_private", None)
    args.pop("custodian_private", None)
    args.update(overrides)
    return verify_receipt_custody_signature_timestamp_v1(**args)


class CustodySignatureTimestampIntegrationV1Tests(unittest.TestCase):
    def test_exact_detached_signature_is_timestamped_without_receipt_cycle(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        result = inspect_timestamp(data)
        self.assertTrue(result.detached_signature_timestamped)
        self.assertTrue(result.signature_existence_interval_preclose_verified)
        self.assertTrue(result.timestamp_proof_is_detached_sidecar)
        self.assertEqual(
            result.signature_sha256,
            hashlib.sha256(data["custody_signature_bytes"]).hexdigest(),
        )
        self.assertEqual(
            result.timestamp_event_id,
            custody_signature_timestamp_event_id(result.signature_sha256),
        )
        self.assertEqual(result.timestamp.accuracy_microseconds, 1_000_000)
        self.assertLess(result.accuracy_lower_bound_utc, result.timestamp.gen_time_utc)
        self.assertGreater(result.accuracy_upper_bound_utc, result.timestamp.gen_time_utc)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_timestamp_accuracy_interval_must_fit_signed_policy_validity(self):
        data = timestamped_bundle(
            accuracy={"seconds": 1},
            policy_not_before_utc="2026-11-23T02:51:00Z",
        )
        with self.assertRaisesRegex(
            ValueError,
            "RFC 3161 signature accuracy interval falls outside signed V3 policy validity interval",
        ):
            inspect_timestamp(data)

    def test_timestamp_accuracy_interval_must_fit_custodian_key_validity(self):
        data = timestamped_bundle(
            accuracy={"seconds": 1},
            custodian_key_valid_from_utc="2026-11-23T02:51:00Z",
        )
        with self.assertRaisesRegex(
            ValueError,
            "RFC 3161 signature accuracy interval falls outside custodian key validity interval",
        ):
            inspect_timestamp(data)

    def test_timestamp_token_must_imprint_exact_signature_not_record_bytes(self):
        data = timestamped_bundle(
            accuracy={"seconds": 1},
            timestamp_data=b"not the detached signature",
        )
        with self.assertRaisesRegex(ValueError, "message imprint"):
            inspect_timestamp(data)

    def test_mutated_signature_is_rejected_by_v3_before_timestamp_acceptance(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        changed = bytearray(data["custody_signature_bytes"])
        changed[0] ^= 1
        with self.assertRaisesRegex(ValueError, "detached custody Ed25519 signature"):
            inspect_timestamp(data, custody_signature_bytes=bytes(changed))

    def test_accuracy_lower_boundary_exactly_at_received_time_is_accepted(self):
        result = inspect_timestamp(timestamped_bundle(
            gen_time=datetime(2026, 11, 23, 2, 46, tzinfo=timezone.utc),
            accuracy={"seconds": 60},
        ))
        self.assertEqual(
            result.accuracy_lower_bound_utc,
            datetime(2026, 11, 23, 2, 45, tzinfo=timezone.utc),
        )

    def test_accuracy_upper_boundary_at_classic_close_is_rejected(self):
        data = timestamped_bundle(
            gen_time=datetime(2026, 11, 23, 2, 59, 59, tzinfo=timezone.utc),
            accuracy={"seconds": 1},
        )
        with self.assertRaisesRegex(ValueError, "strictly before the Classic draw close"):
            inspect_timestamp(data)

    def test_accuracy_interval_ending_one_second_before_close_is_accepted(self):
        result = inspect_timestamp(timestamped_bundle(
            gen_time=datetime(2026, 11, 23, 2, 59, 58, tzinfo=timezone.utc),
            accuracy={"seconds": 1},
        ))
        self.assertEqual(
            result.accuracy_upper_bound_utc,
            datetime(2026, 11, 23, 2, 59, 59, tzinfo=timezone.utc),
        )

    def test_accuracy_interval_starting_before_received_time_is_rejected(self):
        data = timestamped_bundle(
            gen_time=datetime(2026, 11, 23, 2, 45, tzinfo=timezone.utc),
            accuracy={"seconds": 1},
        )
        with self.assertRaisesRegex(ValueError, "lower accuracy bound precedes"):
            inspect_timestamp(data)

    def test_missing_accuracy_cannot_prove_preclose_signature_existence(self):
        data = timestamped_bundle(accuracy=None)
        with self.assertRaisesRegex(ValueError, "accuracy is absent"):
            inspect_timestamp(data)

    def test_wrong_tsa_root_fingerprint_is_rejected(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            inspect_timestamp(data, expected_tsa_root_sha256="0" * 64)

    def test_wrong_nonce_is_rejected(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "nonce does not match"):
            inspect_timestamp(data, expected_nonce=12346)

    def test_stateful_caller_timezone_is_sampled_once(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        tz = StatefulOffsetTimezone()
        data["verification_time"] = datetime(2026, 11, 23, 2, 0, tzinfo=tz)
        result = inspect_timestamp(data)
        self.assertEqual(tz.calls, 1)
        self.assertEqual(result.custody_chain.verification_time_utc, NOW)

    def test_event_id_rejects_noncanonical_signature_digest(self):
        with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
            custody_signature_timestamp_event_id("A" * 64)

    def test_nonpositive_nonce_is_rejected_before_timestamp_parsing(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "exact positive integer"):
            inspect_timestamp(data, expected_nonce=0)

    def test_provenance_remains_blocked_even_when_signature_time_is_verified(self):
        result = inspect_timestamp(timestamped_bundle(accuracy={"seconds": 1}))
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn(
            "TSA_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
            result.remaining_blockers,
        )
        self.assertIn(
            "DETACHED_TIMESTAMP_SIDECAR_NOT_ANCHORED_IN_EXTERNAL_WITNESSED_LEDGER",
            result.remaining_blockers,
        )


if __name__ == "__main__":
    unittest.main()
