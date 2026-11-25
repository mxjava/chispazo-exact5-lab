"""Adversarial tests for non-circular RFC3161 custody-record binding.

All keys, certificates, records, receipts, and timestamp tokens are synthetic.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from origen.custody_receipt_verifier_v3 import canonical_custody_signature_payload
from origen.custody_record_timestamp_integration_v1 import (
    custody_record_timestamp_event_id,
    verify_receipt_custody_record_timestamp_v1,
)
from origen.independent_trust_adapter import ProvenanceStatus
from test_custody_receipt_verifier_v3 import (
    CUSTODIAN_KEY_ID,
    StatefulOffsetTimezone,
    bundle,
    sign_receipt,
)
from test_rfc3161_tsa_verifier_v1 import _token
from test_trust_verifier_v1 import NOW


AUTHORITY_ID = "tsa-test"
GEN_TIME = datetime(2026, 11, 23, 2, 50, tzinfo=timezone.utc)


def _resign_receipt_and_custody(data, document):
    receipt_bytes = sign_receipt(document, data["receipt_private"])
    data["original_receipt_bytes"] = receipt_bytes
    data["custody_signature_bytes"] = data["custodian_private"].sign(
        canonical_custody_signature_payload(
            data["custody_record_bytes"],
            hashlib.sha256(receipt_bytes).hexdigest(),
            data["custodian_key_id"],
        )
    )


def timestamped_bundle(*, gen_time=GEN_TIME, accuracy=None, timestamp_data=None):
    data = bundle()
    target = data["custody_record_bytes"] if timestamp_data is None else timestamp_data
    token, tsa_root = _token(data=target, accuracy=accuracy, gen_time=gen_time)
    record_sha = hashlib.sha256(data["custody_record_bytes"]).hexdigest()
    document = json.loads(data["original_receipt_bytes"])
    document["trusted_time_proofs"].append({
        "authority_id": AUTHORITY_ID,
        "event_id": custody_record_timestamp_event_id(record_sha),
        "event_at_utc": gen_time.isoformat().replace("+00:00", "Z"),
        "proof_sha256": hashlib.sha256(token).hexdigest(),
    })
    _resign_receipt_and_custody(data, document)
    data.update({
        "timestamp_token_der": token,
        "pinned_tsa_root_certificate_der": tsa_root,
        "expected_tsa_root_sha256": hashlib.sha256(tsa_root).hexdigest(),
        "expected_tsa_authority_id": AUTHORITY_ID,
        "expected_nonce": 12345,
    })
    return data


def inspect_timestamp(data, **overrides):
    args = dict(data)
    args.pop("receipt_private", None)
    args.pop("custodian_private", None)
    args.update(overrides)
    return verify_receipt_custody_record_timestamp_v1(**args)


class CustodyRecordTimestampIntegrationV1Tests(unittest.TestCase):
    def test_valid_record_timestamp_is_bound_to_receipt_but_provenance_stays_blocked(self):
        result = inspect_timestamp(timestamped_bundle(accuracy={"seconds": 1}))
        self.assertTrue(result.record_existence_interval_preclose_verified)
        self.assertFalse(result.detached_signature_timestamped)
        self.assertEqual(result.timestamp_event_id, custody_record_timestamp_event_id(
            result.custody_chain.custody_record_sha256
        ))
        self.assertEqual(result.timestamp.accuracy_microseconds, 1_000_000)
        self.assertLess(result.accuracy_lower_bound_utc, result.timestamp.gen_time_utc)
        self.assertGreater(result.accuracy_upper_bound_utc, result.timestamp.gen_time_utc)
        self.assertIn("DETACHED_CUSTODY_SIGNATURE_ITSELF_NOT_TIME_STAMPED", result.remaining_blockers)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_exact_accuracy_boundary_at_received_time_is_accepted(self):
        result = inspect_timestamp(timestamped_bundle(
            gen_time=datetime(2026, 11, 23, 2, 46, tzinfo=timezone.utc),
            accuracy={"seconds": 60},
        ))
        self.assertEqual(
            result.accuracy_lower_bound_utc,
            datetime(2026, 11, 23, 2, 45, tzinfo=timezone.utc),
        )

    def test_exact_accuracy_upper_boundary_at_classic_close_is_rejected(self):
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

    def test_accuracy_interval_starting_before_custodian_receipt_is_rejected(self):
        data = timestamped_bundle(
            gen_time=datetime(2026, 11, 23, 2, 45, tzinfo=timezone.utc),
            accuracy={"seconds": 1},
        )
        with self.assertRaisesRegex(ValueError, "lower accuracy bound precedes"):
            inspect_timestamp(data)

    def test_missing_accuracy_cannot_establish_a_bounded_preclose_interval(self):
        data = timestamped_bundle(accuracy=None)
        with self.assertRaisesRegex(ValueError, "accuracy is absent"):
            inspect_timestamp(data)

    def test_token_must_imprint_exact_canonical_custody_record_bytes(self):
        data = timestamped_bundle(timestamp_data=b"not the custody record", accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "message imprint"):
            inspect_timestamp(data)

    def test_token_digest_must_be_bound_by_the_root_signed_receipt(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        document = json.loads(data["original_receipt_bytes"])
        document["trusted_time_proofs"][-1]["proof_sha256"] = "f" * 64
        _resign_receipt_and_custody(data, document)
        with self.assertRaisesRegex(ValueError, "must match exactly one root-receipt"):
            inspect_timestamp(data)

    def test_event_identity_must_bind_exact_record_digest(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        document = json.loads(data["original_receipt_bytes"])
        document["trusted_time_proofs"][-1]["event_id"] = "another-event"
        _resign_receipt_and_custody(data, document)
        with self.assertRaisesRegex(ValueError, "event ID does not bind"):
            inspect_timestamp(data)

    def test_authority_must_match_caller_expected_tsa_authority(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        document = json.loads(data["original_receipt_bytes"])
        document["trusted_time_proofs"][-1]["authority_id"] = "other-tsa"
        _resign_receipt_and_custody(data, document)
        with self.assertRaisesRegex(ValueError, "authority does not match"):
            inspect_timestamp(data)

    def test_proof_event_time_must_match_token_gen_time(self):
        data = timestamped_bundle(accuracy={"seconds": 1})
        document = json.loads(data["original_receipt_bytes"])
        document["trusted_time_proofs"][-1]["event_at_utc"] = "2026-11-23T02:50:01Z"
        _resign_receipt_and_custody(data, document)
        with self.assertRaisesRegex(ValueError, "genTime does not match"):
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

    def test_event_id_rejects_noncanonical_record_digest(self):
        with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
            custody_record_timestamp_event_id("A" * 64)


if __name__ == "__main__":
    unittest.main()
