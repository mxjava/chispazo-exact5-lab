from __future__ import annotations

import hashlib
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from origen.deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    DeploymentTrustSnapshot,
    ExternalEvidenceAdvanceV2,
    TrustStateRejected,
    _external_evidence_advance_copy,
    _require_v2_external_evidence_nonce_binding,
)
from origen.physical_trust_context_v1 import (
    PhysicalTrustContextV1,
    physical_trust_context_sha256,
)
from origen.timestamp_nonce_challenge_v1 import (
    TimestampNonceChallengeV1,
    copy_timestamp_nonce_challenge,
    timestamp_nonce_challenge_sha256,
)
from test_transparency_ledger_bundle_verifier_v2 import build_v2_case


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def valid_advance() -> ExternalEvidenceAdvanceV2:
    values, _ = build_v2_case()
    checkpoint = json.loads(values["raw_signed_checkpoint_bytes"].decode("utf-8"))
    raw_old_checkpoint = b"synthetic-old-checkpoint"
    raw_registry = b"synthetic-witness-registry"
    raw_receipt = b"synthetic-receipt"
    raw_custody = b"synthetic-custody-record"
    raw_portfolio = b"synthetic-portfolio"
    raw_custody_signature = b"synthetic-custody-signature"

    return ExternalEvidenceAdvanceV2(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id="research-backend-1",
        log_id=values["expected_log_id"],
        log_key_id=values["expected_log_key_id"],
        log_public_key_sha256=sha(values["pinned_log_public_key_bytes"]),
        old_tree_size=6,
        old_root_sha256="1" * 64,
        old_checkpoint_sha256=sha(raw_old_checkpoint),
        new_tree_size=checkpoint["tree_size"],
        new_root_sha256=checkpoint["root_hash"],
        new_checkpoint_sha256=sha(values["raw_signed_checkpoint_bytes"]),
        registry_id="research-registry-1",
        registry_root_key_id="research-registry-root-1",
        registry_root_public_key_sha256="2" * 64,
        registry_sequence=1,
        registry_sha256=sha(raw_registry),
        raw_manifest_bytes=values["raw_manifest_bytes"],
        raw_ledger_entry_bytes=values["raw_ledger_entry_bytes"],
        raw_inclusion_proof_bytes=values["raw_inclusion_proof_bytes"],
        raw_old_checkpoint_bytes=raw_old_checkpoint,
        raw_new_checkpoint_bytes=values["raw_signed_checkpoint_bytes"],
        raw_consistency_proof_bytes=b"synthetic-consistency-proof",
        raw_registry_bytes=raw_registry,
        raw_witness_statement_bytes=(b"synthetic-witness-a", b"synthetic-witness-b"),
        receipt_sha256=sha(raw_receipt),
        policy_envelope_sha256=sha(values["signed_policy_envelope_bytes"]),
        raw_receipt_bytes=raw_receipt,
        raw_policy_envelope_bytes=values["signed_policy_envelope_bytes"],
        raw_custody_record_bytes=raw_custody,
        raw_portfolio_bytes=raw_portfolio,
        raw_custody_signature_bytes=raw_custody_signature,
        custodian_key_id="synthetic-custodian-key",
        raw_timestamp_token_der=b"synthetic-custody-token",
        raw_policy_timestamp_token_der=b"synthetic-policy-token",
        raw_artifact_bytes_by_sha256=tuple(
            sorted(values["artifact_bytes_by_sha256"].items())
        ),
        raw_signature_bytes_by_sha256=tuple(
            sorted(values["signature_bytes_by_sha256"].items())
        ),
        raw_timestamp_bundle_bytes=values["raw_timestamp_bundle_bytes"],
        raw_nested_signature_bundle_timestamp_token_der=values["timestamp_token_der"],
        nested_signature_bundle_timestamp_nonce=values["expected_nonce"],
    )


def make_challenge(*, bundle_nonce=33):
    return TimestampNonceChallengeV1(
        challenge_id="research-challenge-1",
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id="research-backend-1",
        policy_timestamp_nonce=11,
        custody_timestamp_nonce=22,
        state_generation=7,
        root_generation=2,
        physical_trust_context_generation=3,
        physical_trust_context_sha256="a" * 64,
        issued_at_utc=datetime(2026, 11, 27, 20, 0, tzinfo=timezone.utc),
        expires_at_utc=datetime(2026, 11, 27, 20, 5, tzinfo=timezone.utc),
        nested_signature_bundle_timestamp_nonce=bundle_nonce,
    )

def make_provider_context(*, nested_pin=True):
    policy_root = b"synthetic-policy-root"
    custody_root = b"synthetic-custody-root"
    nested_root = b"synthetic-nested-bundle-root" if nested_pin else None
    return PhysicalTrustContextV1(
        policy_tsa_root_certificate_der=policy_root,
        policy_tsa_root_sha256=sha(policy_root),
        policy_tsa_policy_oid="1.2.3.4",
        policy_root_public_key_bytes=b"k" * 32,
        policy_root_key_id="synthetic-root-key",
        minimum_policy_sequence=1,
        custody_tsa_root_certificate_der=custody_root,
        custody_tsa_root_sha256=sha(custody_root),
        log_public_key_bytes=b"l" * 32,
        log_id="synthetic-log",
        log_key_id="synthetic-log-key",
        registry_root_public_key_bytes=b"r" * 32,
        registry_root_key_id="synthetic-registry-root",
        registry_id="synthetic-registry",
        minimum_registry_sequence=1,
        context_generation=3,
        nested_signature_bundle_tsa_root_certificate_der=nested_root,
        nested_signature_bundle_tsa_root_sha256=sha(nested_root) if nested_root is not None else None,
        nested_signature_bundle_tsa_policy_oid="1.2.3.4.5" if nested_root is not None else None,
    )


def make_provider_snapshot(context):
    now = datetime(2026, 11, 27, 20, 1, tzinfo=timezone.utc)
    return DeploymentTrustSnapshot(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        root_public_key_bytes=b"k" * 32,
        root_key_id="synthetic-root-key",
        root_generation=2,
        minimum_policy_sequence=1,
        state_generation=7,
        accepted_policy_sequence=1,
        accepted_policy_envelope_sha256="a" * 64,
        trusted_time_latest_utc=now - timedelta(seconds=1),
        trusted_time_utc=now,
        clock_uncertainty_ms=0,
        maximum_clock_uncertainty_ms=100,
        clock_source_id="synthetic-clock",
        clock_sample_key_id="synthetic-clock-key",
        clock_sample_public_key_bytes=b"c" * 32,
        clock_sample_envelope_bytes=b"synthetic-clock-sample",
        clock_sample_id="synthetic-clock-sample-1",
        clock_sample_valid_until_utc=now + timedelta(minutes=3),
        maximum_clock_sample_age_ms=180000,
        state_backend_id="research-backend-1",
        provisioning_record_sha256="b" * 64,
        physical_trust_context_generation=context.context_generation,
        physical_trust_context_sha256=physical_trust_context_sha256(context),
    )


def make_provider_bound_challenge(advance, context, snapshot, *, nonce=None):
    return TimestampNonceChallengeV1(
        challenge_id="synthetic-v2-provider-challenge",
        policy_domain=snapshot.policy_domain,
        state_backend_id=snapshot.state_backend_id,
        policy_timestamp_nonce=11,
        custody_timestamp_nonce=22,
        state_generation=snapshot.state_generation,
        root_generation=snapshot.root_generation,
        physical_trust_context_generation=context.context_generation,
        physical_trust_context_sha256=physical_trust_context_sha256(context),
        issued_at_utc=snapshot.trusted_time_utc - timedelta(seconds=1),
        expires_at_utc=snapshot.trusted_time_utc + timedelta(minutes=2),
        nested_signature_bundle_timestamp_nonce=(
            advance.nested_signature_bundle_timestamp_nonce if nonce is None else nonce
        ),
    )


class ExternalEvidenceAdvanceV2Tests(unittest.TestCase):

    def test_v2_advance_requires_exact_provider_challenge_and_nested_tsa_pin(self):
        advance = valid_advance()
        context = make_provider_context()
        snapshot = make_provider_snapshot(context)
        challenge = make_provider_bound_challenge(advance, context, snapshot)

        _require_v2_external_evidence_nonce_binding(
            advance,
            provider_snapshot=snapshot,
            physical_trust_context=context,
            timestamp_nonce_challenge=challenge,
            timestamp_nonce_challenge_id=challenge.challenge_id,
            timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(challenge),
        )

        with self.assertRaisesRegex(TrustStateRejected, "exact provider-issued three-nonce challenge"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=snapshot,
                physical_trust_context=context,
                timestamp_nonce_challenge=None,
                timestamp_nonce_challenge_id=None,
                timestamp_nonce_challenge_sha256=None,
            )

    def test_v2_advance_rejects_third_nonce_substitution_before_cas(self):
        advance = valid_advance()
        context = make_provider_context()
        snapshot = make_provider_snapshot(context)
        challenge = make_provider_bound_challenge(
            advance, context, snapshot, nonce=advance.nested_signature_bundle_timestamp_nonce + 1
        )

        with self.assertRaisesRegex(TrustStateRejected, "third timestamp nonce does not match"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=snapshot,
                physical_trust_context=context,
                timestamp_nonce_challenge=challenge,
                timestamp_nonce_challenge_id=challenge.challenge_id,
                timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(challenge),
            )

    def test_v2_advance_rejects_unpinned_or_drifted_nested_tsa_context(self):
        advance = valid_advance()
        context = make_provider_context(nested_pin=False)
        snapshot = make_provider_snapshot(context)
        challenge = make_provider_bound_challenge(advance, context, snapshot)
        with self.assertRaisesRegex(TrustStateRejected, "requires the provider-owned nested-signature bundle TSA pin"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=snapshot,
                physical_trust_context=context,
                timestamp_nonce_challenge=challenge,
                timestamp_nonce_challenge_id=challenge.challenge_id,
                timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(challenge),
            )

        pinned = make_provider_context()
        drifted_snapshot = replace(
            make_provider_snapshot(pinned),
            physical_trust_context_sha256="f" * 64,
        )
        drifted_challenge = make_provider_bound_challenge(advance, pinned, drifted_snapshot)
        with self.assertRaisesRegex(TrustStateRejected, "does not match the exact provider snapshot"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=drifted_snapshot,
                physical_trust_context=pinned,
                timestamp_nonce_challenge=drifted_challenge,
                timestamp_nonce_challenge_id=drifted_challenge.challenge_id,
                timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(drifted_challenge),
            )

    def test_v2_advance_rejects_physical_context_policy_root_mismatch(self):
        advance = valid_advance()
        context = make_provider_context()
        mismatched_context = replace(context, policy_root_public_key_bytes=b"q" * 32)
        snapshot = replace(
            make_provider_snapshot(context),
            physical_trust_context_sha256=physical_trust_context_sha256(mismatched_context),
        )
        challenge = make_provider_bound_challenge(advance, mismatched_context, snapshot)

        with self.assertRaisesRegex(TrustStateRejected, "policy root/key ID/bootstrap floor differs"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=snapshot,
                physical_trust_context=mismatched_context,
                timestamp_nonce_challenge=challenge,
                timestamp_nonce_challenge_id=challenge.challenge_id,
                timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(challenge),
            )
    def test_v2_advance_rejects_challenge_id_digest_and_snapshot_substitution(self):
        advance = valid_advance()
        context = make_provider_context()
        snapshot = make_provider_snapshot(context)
        challenge = make_provider_bound_challenge(advance, context, snapshot)
        with self.assertRaisesRegex(TrustStateRejected, "exact challenge ID and digest"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=snapshot,
                physical_trust_context=context,
                timestamp_nonce_challenge=challenge,
                timestamp_nonce_challenge_id="substituted-challenge-id",
                timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(challenge),
            )
        altered = replace(challenge, state_generation=challenge.state_generation + 1)
        with self.assertRaisesRegex(TrustStateRejected, "not bound to the exact provider snapshot"):
            _require_v2_external_evidence_nonce_binding(
                advance,
                provider_snapshot=snapshot,
                physical_trust_context=context,
                timestamp_nonce_challenge=altered,
                timestamp_nonce_challenge_id=altered.challenge_id,
                timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256(altered),
            )

    def test_v2_advance_copies_and_binds_exact_sidecar_token_and_leaf(self):
        advance = valid_advance()

        copied = _external_evidence_advance_copy(advance)

        self.assertIs(type(copied), ExternalEvidenceAdvanceV2)
        self.assertEqual(copied.raw_timestamp_bundle_bytes, advance.raw_timestamp_bundle_bytes)
        self.assertEqual(
            copied.raw_nested_signature_bundle_timestamp_token_der,
            advance.raw_nested_signature_bundle_timestamp_token_der,
        )
        self.assertEqual(copied.nested_signature_bundle_timestamp_nonce, 88091)

    def test_v2_advance_rejects_token_substitution_against_ledger_leaf(self):
        advance = valid_advance()
        altered = replace(
            advance,
            raw_nested_signature_bundle_timestamp_token_der=(
                advance.raw_nested_signature_bundle_timestamp_token_der + b"\\x00"
            ),
        )

        with self.assertRaisesRegex(
            ValueError, "does not commit to the exact RFC 3161 token"
        ):
            _external_evidence_advance_copy(altered)

    def test_v2_advance_rejects_noncanonical_or_substituted_sidecar_bytes(self):
        advance = valid_advance()

        with self.assertRaisesRegex(
            ValueError, "do not equal the canonical exact-evidence sidecar"
        ):
            _external_evidence_advance_copy(
                replace(
                    advance,
                    raw_timestamp_bundle_bytes=advance.raw_timestamp_bundle_bytes + b" ",
                )
            )

    def test_v2_advance_rejects_v1_leaf_downgrade(self):
        advance = valid_advance()
        entry = json.loads(advance.raw_ledger_entry_bytes.decode("utf-8"))
        entry["schema_version"] = "origen.transparency-ledger-entry.v1"
        entry.pop("timestamp_bundle_sha256")
        entry.pop("timestamp_token_sha256")

        with self.assertRaisesRegex(ValueError, "fields mismatch"):
            _external_evidence_advance_copy(
                replace(advance, raw_ledger_entry_bytes=canonical(entry))
            )

    def test_v2_advance_rejects_leaf_with_wrong_sidecar_digest(self):
        advance = valid_advance()
        entry = json.loads(advance.raw_ledger_entry_bytes.decode("utf-8"))
        entry["timestamp_bundle_sha256"] = "0" * 64

        with self.assertRaisesRegex(
            ValueError, "does not commit to the exact timestamp bundle"
        ):
            _external_evidence_advance_copy(
                replace(advance, raw_ledger_entry_bytes=canonical(entry))
            )

    def test_v2_advance_rejects_invalid_third_nonce(self):
        for nonce in (True, 0, -1, (1 << 63)):
            with self.subTest(nonce=nonce):
                with self.assertRaisesRegex(
                    ValueError, "exact positive signed-64-bit integer"
                ):
                    _external_evidence_advance_copy(
                        replace(
                            valid_advance(),
                            nested_signature_bundle_timestamp_nonce=nonce,
                        )
                    )

    def test_optional_third_nonce_is_copied_and_bound_into_challenge_digest(self):
        challenge = make_challenge()

        copied = copy_timestamp_nonce_challenge(challenge)

        self.assertEqual(copied.nested_signature_bundle_timestamp_nonce, 33)
        self.assertEqual(
            timestamp_nonce_challenge_sha256(copied),
            timestamp_nonce_challenge_sha256(challenge),
        )
        self.assertNotEqual(
            timestamp_nonce_challenge_sha256(challenge),
            timestamp_nonce_challenge_sha256(
                replace(challenge, nested_signature_bundle_timestamp_nonce=34)
            ),
        )

    def test_optional_third_nonce_must_be_distinct_from_policy_and_custody_nonces(self):
        with self.assertRaisesRegex(
            ValueError, "all present timestamp challenge nonces must be distinct"
        ):
            make_challenge(bundle_nonce=11)

    def test_v1_challenge_remains_valid_without_the_optional_third_nonce(self):
        challenge = make_challenge(bundle_nonce=None)

        copied = copy_timestamp_nonce_challenge(challenge)

        self.assertIsNone(copied.nested_signature_bundle_timestamp_nonce)


if __name__ == "__main__":
    unittest.main()
