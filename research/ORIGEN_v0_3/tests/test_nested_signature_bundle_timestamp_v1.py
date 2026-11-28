from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timezone

from origen.independent_trust_adapter import ProvenanceStatus
from origen.nested_signature_bundle_timestamp_v1 import (
    canonical_manifest_content_bytes_v1,
    canonical_nested_signature_bundle_timestamp_payload_v1,
    verify_nested_signature_bundle_timestamp_v1,
)
from test_custody_ledger_witness_integration_v1 import _build_case
from origen.transparency_ledger_verifier_v1 import _manifest_commitment_sha256
from test_rfc3161_tsa_verifier_v1 import _token
from test_transparency_checkpoint_consistency_v1 import NOW


CLOSE = datetime(2026, 11, 23, 3, 0, tzinfo=timezone.utc)
PRE_CLOSE = datetime(2026, 11, 23, 2, 59, 50, tzinfo=timezone.utc)


class NestedSignatureBundleTimestampV1Tests(unittest.TestCase):
    def _case(self, *, gen_time=PRE_CLOSE, accuracy=None, nonce=88001):
        data, ledger, _, _ = _build_case()
        payload = canonical_nested_signature_bundle_timestamp_payload_v1(
            ledger["manifest_bytes"],
            data["signed_policy_envelope_bytes"],
            data["artifact_bytes_by_sha256"],
            data["signature_bytes_by_sha256"],
        )
        token, tsa_root = _token(
            data=payload,
            nonce=nonce,
            gen_time=gen_time,
            accuracy={"millis": 250} if accuracy is None else accuracy,
        )
        values = {
            "raw_manifest_bytes": ledger["manifest_bytes"],
            "signed_policy_envelope_bytes": data["signed_policy_envelope_bytes"],
            "artifact_bytes_by_sha256": data["artifact_bytes_by_sha256"],
            "signature_bytes_by_sha256": data["signature_bytes_by_sha256"],
            "timestamp_token_der": token,
            "pinned_root_public_key_bytes": data["pinned_root_public_key_bytes"],
            "expected_root_key_id": data["expected_root_key_id"],
            "minimum_policy_sequence": data["minimum_policy_sequence"],
            "pinned_tsa_root_certificate_der": tsa_root,
            "expected_tsa_root_sha256": hashlib.sha256(tsa_root).hexdigest(),
            "expected_tsa_policy_oid": "1.2.3.4.5",
            "expected_nonce": nonce,
            "verification_time": NOW,
        }
        return data, ledger, payload, values

    def test_exact_manifest_policy_and_every_signature_are_timestamped_preclose(self):
        data, ledger, payload, values = self._case()
        result = verify_nested_signature_bundle_timestamp_v1(**values)

        self.assertEqual(result.manifest_sha256, hashlib.sha256(ledger["manifest_bytes"]).hexdigest())
        self.assertEqual(
            result.manifest_commitment_sha256,
            hashlib.sha256(canonical_manifest_content_bytes_v1(ledger["manifest_bytes"])).hexdigest(),
        )
        self.assertEqual(
            result.manifest_commitment_sha256,
            _manifest_commitment_sha256(ledger["manifest_bytes"]),
        )
        self.assertEqual(result.policy_envelope_sha256, hashlib.sha256(data["signed_policy_envelope_bytes"]).hexdigest())
        self.assertEqual(result.bundle_sha256, hashlib.sha256(payload).hexdigest())
        self.assertEqual(result.timestamp.message_imprint_hex, hashlib.sha256(payload).hexdigest())
        self.assertTrue(result.timestamp.nonce_verified)
        self.assertLess(result.accuracy_upper_bound_utc, CLOSE)
        self.assertTrue(result.signature_existence_preclose_verified)
        self.assertEqual(result.signatures_timestamped, len(data["signature_bytes_by_sha256"]))
        self.assertTrue(all(item.signature_exists_by_timestamp_upper_bound for item in result.signature_results))
        self.assertTrue(all(
            item.key_validity_at_timestamp_status == "VALID_FOR_FULL_TIMESTAMP_ACCURACY_INTERVAL"
            for item in result.signature_results
        ))
        self.assertTrue(all(
            item.key_authorization_at_creation_status == "UNPROVEN_NO_SIGNER_CHALLENGE_BOUND_TO_SIGNATURE"
            for item in result.signature_results
        ))
        self.assertEqual(result.ledger_binding_status, "NOT_BOUND_TO_LEDGER_ENTRY")
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_ledger_inclusion_proof_digest_is_excluded_to_prevent_sidecar_cycle(self):
        data, ledger, payload, _ = self._case()
        document = json.loads(ledger["manifest_bytes"].decode("utf-8"))
        document["ledger_anchor"]["inclusion_proof_sha256"] = "f" * 64
        alternate_manifest = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
        self.assertNotEqual(
            hashlib.sha256(alternate_manifest).hexdigest(),
            hashlib.sha256(ledger["manifest_bytes"]).hexdigest(),
        )
        alternate_payload = canonical_nested_signature_bundle_timestamp_payload_v1(
            alternate_manifest,
            data["signed_policy_envelope_bytes"],
            data["artifact_bytes_by_sha256"],
            data["signature_bytes_by_sha256"],
        )
        self.assertEqual(payload, alternate_payload)
        self.assertEqual(
            _manifest_commitment_sha256(ledger["manifest_bytes"]),
            _manifest_commitment_sha256(alternate_manifest),
        )

    def test_missing_or_extra_signature_bytes_are_rejected(self):
        _, _, _, values = self._case()
        missing = dict(values["signature_bytes_by_sha256"])
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(ValueError, "must exactly match manifest claims"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "signature_bytes_by_sha256": missing}
            )

        extra = dict(values["signature_bytes_by_sha256"])
        extra[hashlib.sha256(b"x" * 64).hexdigest()] = b"x" * 64
        with self.assertRaisesRegex(ValueError, "must exactly match manifest claims"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "signature_bytes_by_sha256": extra}
            )

    def test_artifact_substitution_is_rejected_before_timestamp_acceptance(self):
        _, _, _, values = self._case()
        changed = dict(values["artifact_bytes_by_sha256"])
        digest = next(iter(changed))
        changed[digest] = changed[digest] + b"tampered"
        with self.assertRaisesRegex(ValueError, "digest does not bind exact bytes"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "artifact_bytes_by_sha256": changed}
            )

    def test_signature_substitution_is_rejected_before_timestamp_acceptance(self):
        _, _, _, values = self._case()
        changed = dict(values["signature_bytes_by_sha256"])
        digest = next(iter(changed))
        changed[digest] = bytes([changed[digest][0] ^ 1]) + changed[digest][1:]
        with self.assertRaisesRegex(ValueError, "does not bind exact bytes"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "signature_bytes_by_sha256": changed}
            )

    def test_timestamp_bundle_imprint_must_bind_exact_manifest_policy_and_signatures(self):
        _, _, _, values = self._case()
        wrong_token, wrong_root = _token(
            data=b"not-the-exact-signature-bundle",
            nonce=values["expected_nonce"],
            gen_time=PRE_CLOSE,
            accuracy={"millis": 250},
        )
        with self.assertRaisesRegex(ValueError, "message imprint"):
            verify_nested_signature_bundle_timestamp_v1(
                **{
                    **values,
                    "timestamp_token_der": wrong_token,
                    "pinned_tsa_root_certificate_der": wrong_root,
                    "expected_tsa_root_sha256": hashlib.sha256(wrong_root).hexdigest(),
                }
            )

    def test_accuracy_upper_bound_must_be_strictly_before_classic_close(self):
        _, _, _, values = self._case(
            gen_time=CLOSE,
            accuracy={"seconds": 0},
        )
        with self.assertRaisesRegex(ValueError, "strictly before CLASSIC close"):
            verify_nested_signature_bundle_timestamp_v1(**values)

    def test_tsa_nonce_and_policy_oid_are_mandatory_exact_pins(self):
        _, _, _, values = self._case(nonce=88002)
        with self.assertRaisesRegex(ValueError, "nonce does not match"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "expected_nonce": 88003}
            )
        with self.assertRaisesRegex(ValueError, "policy OID does not match"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "expected_tsa_policy_oid": "1.2.3.4.6"}
            )

    def test_nonclassic_manifest_is_rejected(self):
        _, _, _, values = self._case()
        raw = values["raw_manifest_bytes"].replace(b'"modality":"CLASSIC"', b'"modality":"DE_LAS_TRES"')
        self.assertNotEqual(raw, values["raw_manifest_bytes"])
        with self.assertRaisesRegex(ValueError, "modality|CLASSIC"):
            verify_nested_signature_bundle_timestamp_v1(
                **{**values, "raw_manifest_bytes": raw}
            )


if __name__ == "__main__":
    unittest.main()
