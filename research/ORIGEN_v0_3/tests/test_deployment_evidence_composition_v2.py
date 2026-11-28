from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import timedelta

from origen.deployment_evidence_composition_v2 import (
    inspect_provider_bound_transparency_ledger_bundle_transition_v2,
)
from origen.deployment_trust_provider_v1 import (
    TrustProviderUnavailable,
    TrustStateRejected,
)
from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_trust_context_v1 import physical_trust_context_sha256
from test_custody_ledger_witness_integration_v1 import _build_case
from test_deployment_evidence_composition_v1 import _provider_for
from test_transparency_checkpoint_consistency_v1 import NOW
from test_transparency_ledger_bundle_transition_v2 import build_transition_case


_BYTE_ARGUMENTS = (
    "raw_manifest_bytes",
    "raw_ledger_entry_bytes",
    "raw_inclusion_proof_bytes",
    "raw_old_checkpoint_bytes",
    "raw_signed_checkpoint_bytes",
    "raw_consistency_proof_bytes",
    "raw_timestamp_bundle_bytes",
    "timestamp_token_der",
    "signed_policy_envelope_bytes",
    "artifact_bytes_by_sha256",
    "signature_bytes_by_sha256",
)


def build_provider_bound_case(*, uncertainty_ms=0):
    values = build_transition_case()
    data, ledger, _, _ = _build_case()
    provider = _provider_for(data, ledger, uncertainty_ms=uncertainty_ms)

    context = replace(
        provider.physical_context,
        nested_signature_bundle_tsa_root_certificate_der=(
            values["pinned_tsa_root_certificate_der"]
        ),
        nested_signature_bundle_tsa_root_sha256=(
            values["expected_tsa_root_sha256"]
        ),
        nested_signature_bundle_tsa_policy_oid=(
            values["expected_tsa_policy_oid"]
        ),
    )
    context_digest = physical_trust_context_sha256(context)
    current = provider.snapshot.accepted_external_evidence_watermark
    watermark = replace(
        current,
        ledger_tree_size=values["expected_old_tree_size"],
        ledger_root_sha256=values["expected_old_root_sha256"],
        ledger_checkpoint_sha256=values["expected_old_checkpoint_sha256"],
    )
    snapshot = replace(
        provider.snapshot,
        physical_trust_context_generation=context.context_generation,
        physical_trust_context_sha256=context_digest,
        accepted_external_evidence_watermark=watermark,
    )
    challenge = replace(
        provider.nonce_challenge,
        physical_trust_context_sha256=context_digest,
        nested_signature_bundle_timestamp_nonce=values["expected_nonce"],
    )
    provider.snapshot = snapshot
    provider.physical_context = context
    provider.nonce_challenge = challenge
    provider.pending_timestamp_nonce_challenge = challenge
    return values, provider


def inspect(values, provider):
    return inspect_provider_bound_transparency_ledger_bundle_transition_v2(
        **{key: values[key] for key in _BYTE_ARGUMENTS},
        provider=provider,
    )


class ProviderBoundTransparencyLedgerBundleTransitionV2Tests(unittest.TestCase):
    def test_valid_transition_uses_one_provider_snapshot_context_and_three_nonce_challenge(self):
        values, provider = build_provider_bound_case()
        result = inspect(values, provider)

        self.assertTrue(result.transition.inclusion.inclusion_verified)
        self.assertTrue(result.transition.checkpoint_consistency.consistency_verified)
        self.assertEqual(
            result.accepted_watermark_sha256,
            result.transition.accepted_old_checkpoint_sha256
            and result.accepted_watermark_sha256,
        )
        self.assertEqual(result.timestamp_nonce_challenge_id, provider.nonce_challenge.challenge_id)
        self.assertEqual(result.provider_state_generation, provider.snapshot.state_generation)
        self.assertEqual(
            result.physical_trust_context_sha256,
            provider.snapshot.physical_trust_context_sha256,
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn("PROVIDER_CAS_NOT_PERFORMED", result.remaining_blockers)
        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.timestamp_nonce_challenge_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_context_digest_drift_is_rejected_before_transition_verification(self):
        values, provider = build_provider_bound_case()
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256="c" * 64,
        )
        with self.assertRaisesRegex(TrustStateRejected, "exact snapshot generation and digest"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)

    def test_watermark_log_identity_must_match_provider_owned_context(self):
        values, provider = build_provider_bound_case()
        context = replace(
            provider.physical_context,
            log_public_key_bytes=bytes([provider.physical_context.log_public_key_bytes[0] ^ 1])
            + provider.physical_context.log_public_key_bytes[1:],
        )
        digest = physical_trust_context_sha256(context)
        provider.physical_context = context
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256=digest,
        )
        with self.assertRaisesRegex(TrustStateRejected, "watermark identity differs"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)

    def test_provider_challenge_must_include_third_nonce(self):
        values, provider = build_provider_bound_case()
        challenge = replace(
            provider.nonce_challenge,
            nested_signature_bundle_timestamp_nonce=None,
        )
        provider.nonce_challenge = challenge
        provider.pending_timestamp_nonce_challenge = challenge
        with self.assertRaisesRegex(TrustStateRejected, "third timestamp nonce"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)

    def test_challenge_must_cover_full_clock_uncertainty_interval(self):
        values, provider = build_provider_bound_case(uncertainty_ms=100)
        challenge = replace(
            provider.nonce_challenge,
            expires_at_utc=NOW + timedelta(milliseconds=50),
        )
        provider.nonce_challenge = challenge
        provider.pending_timestamp_nonce_challenge = challenge
        with self.assertRaisesRegex(TrustStateRejected, "complete provider time interval"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)

    def test_missing_independent_genesis_watermark_is_rejected(self):
        values, provider = build_provider_bound_case()
        provider.snapshot = replace(
            provider.snapshot,
            accepted_external_evidence_watermark=None,
        )
        with self.assertRaisesRegex(TrustStateRejected, "independently provisioned accepted watermark"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)

    def test_old_checkpoint_must_match_the_provider_watermark_not_caller_claim(self):
        values, provider = build_provider_bound_case()
        watermark = replace(
            provider.snapshot.accepted_external_evidence_watermark,
            ledger_checkpoint_sha256="0" * 64,
        )
        provider.snapshot = replace(
            provider.snapshot,
            accepted_external_evidence_watermark=watermark,
        )
        with self.assertRaisesRegex(ValueError, "old checkpoint digest does not match"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)

    def test_provider_snapshot_outage_fails_closed(self):
        values, provider = build_provider_bound_case()
        provider.fail_read = True
        with self.assertRaisesRegex(TrustProviderUnavailable, "snapshot could not be read"):
            inspect(values, provider)
        self.assertEqual(provider.commit_count, 0)


if __name__ == "__main__":
    unittest.main()
