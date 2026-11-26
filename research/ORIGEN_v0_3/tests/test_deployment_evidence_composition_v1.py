from __future__ import annotations

import base64
import hashlib
import inspect
import json
import unittest
from dataclasses import replace
from datetime import timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.deployment_evidence_composition_v1 import (
    _require_used_policy_keys_cover_time_window,
    inspect_custody_ledger_witness_with_deployment_provider_v1,
)
from origen.deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    DeploymentTrustSnapshot,
    TrustStateRejected,
)
from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from origen.physical_trust_context_v1 import (
    PhysicalTrustContextV1,
    physical_trust_context_sha256,
)
from origen.trust_policy_envelope_v3 import verify_signed_trust_policy_v3
from test_custody_ledger_witness_integration_v1 import _build_case
from test_custody_receipt_verifier_v3 import POLICY_SEQUENCE, ROOT_KEY_ID
from test_deployment_trust_provider_v1 import SyntheticTrustProvider, signed_clock_sample
from test_transparency_checkpoint_consistency_v1 import NOW
from test_transparency_ledger_verifier_v1 import (
    LOG_ID as LEDGER_LOG_ID,
    LOG_KEY_ID,
)
from test_checkpoint_witness_quorum_v1 import (
    REGISTRY_ID,
    ROOT_KEY_ID as WITNESS_ROOT_KEY_ID,
    ROOT_PRIVATE,
)
from test_transparency_checkpoint_consistency_v1 import public_bytes


class SyntheticPhysicalTrustProvider(SyntheticTrustProvider):
    def __init__(self, snapshot, context):
        super().__init__(snapshot)
        self.physical_context = context
        self.physical_context_read_count = 0
        self.context_drift_before_commit = False

    def read_physical_trust_context(self, *, policy_domain):
        self.physical_context_read_count += 1
        if policy_domain != "origen.chispazo.classic.physical":
            raise ValueError("wrong physical trust policy domain")
        return self.physical_context

    def compare_and_advance(self, **kwargs):
        if self.context_drift_before_commit:
            self.snapshot = replace(
                self.snapshot,
                physical_trust_context_generation=self.snapshot.physical_trust_context_generation + 1,
                physical_trust_context_sha256="c" * 64,
            )
        return super().compare_and_advance(**kwargs)


def _provider_for(data, ledger):
    context = PhysicalTrustContextV1(
        policy_tsa_root_certificate_der=data["pinned_policy_tsa_root_certificate_der"],
        policy_tsa_root_sha256=data["expected_policy_tsa_root_sha256"],
        policy_tsa_policy_oid=data["expected_policy_tsa_policy_oid"],
        policy_root_public_key_bytes=data["pinned_root_public_key_bytes"],
        policy_root_key_id=data["expected_root_key_id"],
        minimum_policy_sequence=data["minimum_policy_sequence"],
        custody_tsa_root_certificate_der=data["pinned_tsa_root_certificate_der"],
        custody_tsa_root_sha256=data["expected_tsa_root_sha256"],
        log_public_key_bytes=ledger["log_public"],
        log_id=LEDGER_LOG_ID,
        log_key_id=LOG_KEY_ID,
        registry_root_public_key_bytes=public_bytes(ROOT_PRIVATE),
        registry_root_key_id=WITNESS_ROOT_KEY_ID,
        registry_id=REGISTRY_ID,
        minimum_registry_sequence=7,
        minimum_log_tree_size=len(ledger["leaves"]),
        context_generation=4,
    )
    context_digest = physical_trust_context_sha256(context)
    clock_private = data["clock_private"]
    clock_public = data["clock_public_key_bytes"]
    clock_key_id = data["clock_key_id"]
    sample_valid_until = NOW + timedelta(seconds=60)
    sample_bytes = signed_clock_sample(
        clock_private,
        clock_source_id="synthetic-clock",
        clock_sample_id="synthetic-clock-sample-0001",
        key_id=clock_key_id,
        trusted_time_utc=NOW,
        uncertainty_ms=0,
        valid_until_utc=sample_valid_until,
    )
    snapshot = DeploymentTrustSnapshot(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        root_public_key_bytes=data["pinned_root_public_key_bytes"],
        root_key_id=data["expected_root_key_id"],
        root_generation=1,
        minimum_policy_sequence=data["minimum_policy_sequence"],
        state_generation=7,
        accepted_policy_sequence=data["minimum_policy_sequence"] - 1,
        accepted_policy_envelope_sha256="a" * 64,
        trusted_time_latest_utc=NOW - timedelta(seconds=1),
        trusted_time_utc=NOW,
        clock_uncertainty_ms=0,
        maximum_clock_uncertainty_ms=100,
        clock_source_id="synthetic-clock",
        clock_sample_key_id=clock_key_id,
        clock_sample_public_key_bytes=clock_public,
        clock_sample_envelope_bytes=sample_bytes,
        clock_sample_id="synthetic-clock-sample-0001",
        clock_sample_valid_until_utc=sample_valid_until,
        maximum_clock_sample_age_ms=120_000,
        state_backend_id="synthetic-cas-store",
        provisioning_record_sha256="b" * 64,
        physical_trust_context_generation=context.context_generation,
        physical_trust_context_sha256=context_digest,
    )
    return SyntheticPhysicalTrustProvider(snapshot, context)


def _arguments(data, ledger, batches):
    return {
        "original_receipt_bytes": data["original_receipt_bytes"],
        "signed_policy_envelope_bytes": data["signed_policy_envelope_bytes"],
        "custody_record_bytes": data["custody_record_bytes"],
        "portfolio_bytes": data["portfolio_bytes"],
        "custody_signature_bytes": data["custody_signature_bytes"],
        "custodian_key_id": data["custodian_key_id"],
        "timestamp_token_der": data["timestamp_token_der"],
        "policy_timestamp_token_der": data["policy_timestamp_token_der"],
        "policy_timestamp_expected_nonce": data["policy_timestamp_expected_nonce"],
        "expected_nonce": data["expected_nonce"],
        "raw_manifest_bytes": ledger["manifest_bytes"],
        "artifact_bytes_by_sha256": data["artifact_bytes_by_sha256"],
        "signature_bytes_by_sha256": data["signature_bytes_by_sha256"],
        "raw_ledger_entry_bytes": ledger["entry_bytes"],
        "raw_inclusion_proof_bytes": ledger["inclusion_bytes"],
        "raw_old_checkpoint_bytes": ledger["old_bytes"],
        "raw_new_checkpoint_bytes": ledger["new_bytes"],
        "raw_consistency_proof_bytes": ledger["consistency_bytes"],
        "witness_observation_batches": batches,
    }


def _inspect(data, ledger, batches, provider, **overrides):
    arguments = _arguments(data, ledger, batches)
    arguments.update(overrides)
    arguments["provider"] = provider
    return inspect_custody_ledger_witness_with_deployment_provider_v1(**arguments)


class DeploymentEvidenceCompositionV1Tests(unittest.TestCase):
    def test_full_evidence_chain_uses_one_snapshot_and_advances_only_after_success(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)

        result = _inspect(data, ledger, batches, provider)

        self.assertIs(type(result.provenance_status), ProvenanceStatus)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIs(result.evidence.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIs(result.evidence.independent_boundary_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.policy_envelope_sha256, hashlib.sha256(data["signed_policy_envelope_bytes"]).hexdigest())
        self.assertEqual(result.policy_sequence, data["minimum_policy_sequence"])
        self.assertEqual(result.physical_trust_context_generation, 4)
        self.assertEqual(result.physical_trust_context_sha256, provider.snapshot.physical_trust_context_sha256)
        self.assertEqual(result.trusted_time_earliest_utc, NOW)
        self.assertEqual(result.trusted_time_latest_utc, NOW)
        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 1)
        self.assertEqual(provider.snapshot.accepted_policy_sequence, data["minimum_policy_sequence"])
        self.assertEqual(provider.snapshot.trusted_time_latest_utc, NOW)
        self.assertEqual(result.deployment_trust.state_generation_before, 7)
        self.assertEqual(result.deployment_trust.state_generation_after, 8)
        self.assertNotIn(
            "TSA_ROOT_AND_LOG_ROOT_ARE_CALLER_SUPPLIED_NOT_OUT_OF_BAND_PROVISIONED",
            result.remaining_blockers,
        )
        self.assertNotIn(
            "VERIFICATION_CLOCK_IS_CALLER_SUPPLIED_NOT_AUTHENTICATED",
            result.remaining_blockers,
        )
        self.assertIn(
            "PHYSICAL_TRUST_CONTEXT_IS_PROVIDER_OWNED_BUT_NOT_INSTITUTIONALLY_AUTHENTICATED",
            result.remaining_blockers,
        )
        self.assertIn(
            "TSA_CERTIFICATE_CHAINS_AND_CURRENT_REVOCATION_NOT_INDEPENDENTLY_VERIFIED",
            result.remaining_blockers,
        )

    def test_nested_signature_failure_does_not_advance_provider_state(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        altered = dict(data["signature_bytes_by_sha256"])
        digest = next(iter(altered))
        altered[digest] = altered[digest][:-1] + bytes([altered[digest][-1] ^ 1])

        with self.assertRaisesRegex(ValueError, "signature SHA-256"):
            _inspect(
                data,
                ledger,
                batches,
                provider,
                signature_bytes_by_sha256=altered,
            )

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.commit_count, 0)
        self.assertEqual(provider.snapshot.accepted_policy_sequence, data["minimum_policy_sequence"] - 1)

    def test_missing_exact_witness_checkpoint_does_not_advance_provider_state(self):
        data, ledger, batches, _ = _build_case(omit_ledger_checkpoint=True)
        provider = _provider_for(data, ledger)

        with self.assertRaisesRegex(ValueError, "ledger checkpoint is absent"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_clock_sample_signature_failure_prevents_evidence_and_cas(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        document = json.loads(provider.snapshot.clock_sample_envelope_bytes)
        document["signature"]["signature_b64"] = base64.b64encode(bytes(64)).decode("ascii")
        provider.snapshot = replace(
            provider.snapshot,
            clock_sample_envelope_bytes=json.dumps(
                document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii"),
        )

        with self.assertRaisesRegex(ValueError, "clock sample Ed25519 signature verification failed"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_wrong_policy_root_fails_before_evidence_or_cas(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        other_private = Ed25519PrivateKey.generate()
        other_public = other_private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        provider.snapshot = replace(provider.snapshot, root_public_key_bytes=other_public)
        provider.physical_context = replace(
            provider.physical_context,
            policy_root_public_key_bytes=other_public,
        )
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256=physical_trust_context_sha256(provider.physical_context),
        )

        with self.assertRaisesRegex(ValueError, "trust-policy root signature verification failed"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_provider_cas_race_fails_closed_after_full_evidence(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        provider.race_before_commit = True

        with self.assertRaises(TrustStateRejected):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.commit_count, 1)

    def test_used_physical_key_must_cover_entire_clock_uncertainty_interval(self):
        data, ledger, _, _ = _build_case()
        policy = verify_signed_trust_policy_v3(
            data["signed_policy_envelope_bytes"],
            pinned_root_public_key_bytes=data["pinned_root_public_key_bytes"],
            expected_root_key_id=data["expected_root_key_id"],
            expected_policy_domain=CLASSIC_POLICY_DOMAIN,
            minimum_policy_sequence=data["minimum_policy_sequence"],
            verification_time=NOW,
        )
        manifest = parse_unverified_physical_manifest(ledger["manifest_bytes"])
        claim = manifest.signatures[0]
        keys = list(policy.policy.issuer_keys)
        target_index = next(
            i for i, key in enumerate(keys)
            if key.issuer_id == claim.subject_id and key.key_id == claim.key_id
        )
        keys[target_index] = replace(
            keys[target_index],
            valid_until_utc=NOW + timedelta(milliseconds=1),
        )
        narrowed_policy = replace(
            policy,
            policy=replace(policy.policy, issuer_keys=tuple(keys)),
        )

        with self.assertRaisesRegex(ValueError, "uncertainty interval crosses a physical or custody signer key validity boundary"):
            _require_used_policy_keys_cover_time_window(
                narrowed_policy,
                ledger["manifest_bytes"],
                data["custody_record_bytes"],
                data["custodian_key_id"],
                earliest=NOW - timedelta(milliseconds=1),
                latest=NOW + timedelta(milliseconds=2),
            )

    def test_physical_context_policy_root_must_match_deployment_snapshot(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        other_private = Ed25519PrivateKey.generate()
        other_public = other_private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        mismatched = replace(provider.physical_context, policy_root_public_key_bytes=other_public)
        provider.physical_context = mismatched
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256=physical_trust_context_sha256(mismatched),
        )

        with self.assertRaisesRegex(TrustStateRejected, "policy root/key ID/bootstrap floor differs"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_physical_context_digest_mismatch_fails_before_evidence_and_cas(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        provider.physical_context = replace(
            provider.physical_context,
            log_public_key_bytes=b"x" * 32,
        )

        with self.assertRaisesRegex(TrustStateRejected, "exact generation and digest"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_physical_context_generation_is_bound_to_provider_cas(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        provider.context_drift_before_commit = True

        with self.assertRaises(TrustStateRejected):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 1)

    def test_snapshot_must_bind_physical_context_digest_and_generation(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_generation=None,
            physical_trust_context_sha256=None,
        )

        with self.assertRaisesRegex(TrustStateRejected, "does not bind a physical trust context"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_physical_context_policy_floor_must_match_deployment_snapshot(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        changed = replace(
            provider.physical_context,
            minimum_policy_sequence=provider.physical_context.minimum_policy_sequence + 1,
        )
        provider.physical_context = changed
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256=physical_trust_context_sha256(changed),
        )

        with self.assertRaisesRegex(TrustStateRejected, "bootstrap floor differs"):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_provider_owned_log_tree_floor_is_enforced(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        changed = replace(
            provider.physical_context,
            minimum_log_tree_size=len(ledger["leaves"]) + 1,
        )
        provider.physical_context = changed
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256=physical_trust_context_sha256(changed),
        )

        with self.assertRaises(ValueError):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_provider_owned_registry_sequence_floor_is_enforced(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        changed = replace(
            provider.physical_context,
            minimum_registry_sequence=8,
        )
        provider.physical_context = changed
        provider.snapshot = replace(
            provider.snapshot,
            physical_trust_context_sha256=physical_trust_context_sha256(changed),
        )

        with self.assertRaises(ValueError):
            _inspect(data, ledger, batches, provider)

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.physical_context_read_count, 1)
        self.assertEqual(provider.commit_count, 0)

    def test_provider_without_physical_context_fails_before_evidence_and_cas(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        provider_without_context = SyntheticTrustProvider(provider.snapshot)

        with self.assertRaisesRegex(Exception, "lacks read_physical_trust_context"):
            _inspect(data, ledger, batches, provider_without_context)

        self.assertEqual(provider_without_context.read_count, 1)
        self.assertEqual(provider_without_context.commit_count, 0)

    def test_request_api_does_not_accept_caller_root_floor_or_clock(self):
        parameters = inspect.signature(
            inspect_custody_ledger_witness_with_deployment_provider_v1
        ).parameters
        self.assertNotIn("pinned_root_public_key_bytes", parameters)
        self.assertNotIn("expected_root_key_id", parameters)
        self.assertNotIn("minimum_policy_sequence", parameters)
        self.assertNotIn("verification_time", parameters)
