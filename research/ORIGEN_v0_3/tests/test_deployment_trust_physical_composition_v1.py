"""Synthetic orchestration tests; no institutional trust is represented."""
from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from origen.deployment_trust_provider_v1 import DeploymentTrustInspection, TrustStateRejected
from origen.deployment_trust_physical_composition_v1 import (
    verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1,
)
from origen.custody_ledger_witness_integration_v1 import CustodyLedgerWitnessInspectionV1
from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_trust_context_v1 import PhysicalTrustContextV1, physical_trust_context_sha256
from test_deployment_trust_provider_v1 import (
    SyntheticTrustProvider,
    TestDeploymentTrustProviderV1,
)
from test_receipt_policy_integration_v3 import POLICY_SEQUENCE, ROOT_KEY_ID


NOW = datetime(2026, 11, 26, 20, 0, tzinfo=timezone.utc)
RECEIPT = b"synthetic exact receipt"
POLICY = b"synthetic exact signed policy"



def physical_context(
    *,
    policy_root_public_key_bytes=b"p" * 32,
    policy_root_key_id="synthetic-policy-root",
    minimum_policy_sequence=7,
):
    policy_tsa = b"synthetic policy TSA certificate"
    custody_tsa = b"synthetic custody TSA certificate"
    return PhysicalTrustContextV1(
        policy_tsa_root_certificate_der=policy_tsa,
        policy_tsa_root_sha256=hashlib.sha256(policy_tsa).hexdigest(),
        policy_tsa_policy_oid="1.2.3.4",
        policy_root_public_key_bytes=policy_root_public_key_bytes,
        policy_root_key_id=policy_root_key_id,
        minimum_policy_sequence=minimum_policy_sequence,
        custody_tsa_root_certificate_der=custody_tsa,
        custody_tsa_root_sha256=hashlib.sha256(custody_tsa).hexdigest(),
        log_public_key_bytes=b"l" * 32,
        log_id="synthetic-log",
        log_key_id="synthetic-log-key",
        registry_root_public_key_bytes=b"r" * 32,
        registry_root_key_id="synthetic-registry-root",
        registry_id="synthetic-registry",
        minimum_registry_sequence=4,
        context_generation=3,
    )

def provider_snapshot(context, *, context_digest=None, root_public_key_bytes=None):
    return SimpleNamespace(
        trusted_time_utc=NOW,
        policy_domain="origen.chispazo.classic.provenance",
        root_public_key_bytes=(
            context.policy_root_public_key_bytes
            if root_public_key_bytes is None else root_public_key_bytes
        ),
        root_key_id=context.policy_root_key_id,
        minimum_policy_sequence=context.minimum_policy_sequence,
        physical_trust_context_generation=context.context_generation,
        physical_trust_context_sha256=(
            physical_trust_context_sha256(context)
            if context_digest is None else context_digest
        ),
    )


def physical_result():
    return CustodyLedgerWitnessInspectionV1(
        custody_timestamp=None,
        policy_envelope_timestamp=None,
        policy_envelope_timestamp_proof_in_manifest_commitment_verified=True,
        physical_signatures=None,
        ledger=None,
        witness_gossip=None,
        manifest_sha256="a" * 64,
        custody_record_artifact_sha256="b" * 64,
        timestamp_token_sha256="c" * 64,
        timestamp_event_id="synthetic-event",
        ledger_checkpoint_sha256="d" * 64,
        ledger_checkpoint_observed_in_witness_batches=True,
        witness_comparison_status="SYNTHETIC",
        independent_boundary_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=("SYNTHETIC_FIXTURES_ONLY",),
    )


def deployment_result():
    return DeploymentTrustInspection(
        receipt_sha256=hashlib.sha256(RECEIPT).hexdigest(),
        policy_envelope_sha256=hashlib.sha256(POLICY).hexdigest(),
        policy_domain="origen.chispazo.classic.provenance",
        policy_sequence=7,
        root_key_id="synthetic-root",
        root_generation=1,
        provisioning_record_sha256="1" * 64,
        trust_configuration_sha256="2" * 64,
        clock_source_id="synthetic-clock",
        clock_sample_sha256="3" * 64,
        clock_sample_valid_until_utc=NOW,
        state_backend_id="synthetic-cas",
        time_window_start_utc=NOW,
        time_window_end_utc=NOW,
        state_generation_before=1,
        state_generation_after=2,
        state_outcome=None,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
    )


class DeploymentPhysicalCompositionTests(unittest.TestCase):
    def test_physical_bundle_precedes_provider_commit_and_exact_bytes_are_reused(self):
        events = []
        context = physical_context()
        snapshot = provider_snapshot(context)

        class Provider:
            def read_snapshot(self, *, policy_domain):
                events.append(("snapshot", policy_domain))
                return snapshot

            def read_physical_trust_context(self, *, policy_domain):
                events.append(("physical-context", policy_domain))
                return context

        provider = Provider()

        def physical(receipt, policy, **kwargs):
            events.append(("physical", receipt, policy, kwargs["verification_time"], dict(kwargs)))
            return physical_result()

        def deployment(receipt, policy, *, provider, provider_snapshot, physical_trust_context):
            events.append(("provider", receipt, policy, provider, provider_snapshot, physical_trust_context))
            return deployment_result()

        with (
            patch(
                "origen.deployment_trust_physical_composition_v1._snapshot_copy",
                return_value=snapshot,
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1.verify_custody_timestamp_ledger_witness_v1",
                side_effect=physical,
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1._inspect_receipt_with_deployment_trust_provider_snapshot",
                side_effect=deployment,
                create=True,
            ),
        ):
            result = verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                RECEIPT,
                POLICY,
                provider=provider,
                physical_verification_kwargs={"verification_time": datetime(2026, 11, 26, 21, 0, tzinfo=timezone.utc)},
            )

        self.assertEqual(
            [event[0] for event in events],
            ["snapshot", "physical-context", "physical", "provider"],
        )
        self.assertEqual(events[2][1:3], (RECEIPT, POLICY))
        self.assertEqual(events[2][3], NOW)  # caller time is overwritten
        self.assertEqual(events[2][4]["pinned_log_public_key_bytes"], b"l" * 32)
        self.assertEqual(events[2][4]["pinned_registry_root_public_key_bytes"], b"r" * 32)
        self.assertEqual(events[3][1:3], (RECEIPT, POLICY))
        self.assertIs(events[3][3], provider)
        self.assertIs(events[3][4], snapshot)
        self.assertIs(events[3][5], context)
        self.assertEqual(result.receipt_sha256, hashlib.sha256(RECEIPT).hexdigest())
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn(
            "PHYSICAL_VERIFIER_CLOCK_IS_CALLER_SUPPLIED_NOT_PROVIDER_SNAPSHOT",
            result.remaining_blockers,
        )

    def test_failed_physical_bundle_never_reads_or_advances_provider(self):
        context = physical_context()
        snapshot = provider_snapshot(context)

        class Provider:
            def read_snapshot(self, *, policy_domain):
                return snapshot

            def read_physical_trust_context(self, *, policy_domain):
                return context

        provider = Provider()
        with (
            patch(
                "origen.deployment_trust_physical_composition_v1._snapshot_copy",
                return_value=snapshot,
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1.verify_custody_timestamp_ledger_witness_v1",
                side_effect=ValueError("synthetic nested signature failure"),
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1._inspect_receipt_with_deployment_trust_provider_snapshot",
                create=True,
            ) as deployment,
        ):
            with self.assertRaisesRegex(ValueError, "nested signature failure"):
                verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                    RECEIPT,
                    POLICY,
                    provider=provider,
                    physical_verification_kwargs={"verification_time": NOW},
                )
        deployment.assert_not_called()

    def test_physical_context_must_match_provider_snapshot_before_verification(self):
        context = physical_context()
        snapshot = provider_snapshot(context, context_digest="f" * 64)

        class Provider:
            def read_snapshot(self, *, policy_domain):
                return snapshot

            def read_physical_trust_context(self, *, policy_domain):
                return context

        with (
            patch(
                "origen.deployment_trust_physical_composition_v1._snapshot_copy",
                return_value=snapshot,
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1.verify_custody_timestamp_ledger_witness_v1"
            ) as physical,
            patch(
                "origen.deployment_trust_physical_composition_v1._inspect_receipt_with_deployment_trust_provider_snapshot",
                create=True,
            ) as deployment,
        ):
            with self.assertRaisesRegex(
                TrustStateRejected,
                "physical trust context does not match the exact provider snapshot",
            ):
                verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                    RECEIPT,
                    POLICY,
                    provider=Provider(),
                    physical_verification_kwargs={"verification_time": NOW},
                )

        physical.assert_not_called()
        deployment.assert_not_called()

    def test_physical_context_root_must_match_provider_snapshot(self):
        context = physical_context()
        snapshot = provider_snapshot(
            context,
            root_public_key_bytes=b"x" * 32,
        )

        class Provider:
            def read_snapshot(self, *, policy_domain):
                return snapshot

            def read_physical_trust_context(self, *, policy_domain):
                return context

        with (
            patch(
                "origen.deployment_trust_physical_composition_v1._snapshot_copy",
                return_value=snapshot,
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1.verify_custody_timestamp_ledger_witness_v1"
            ) as physical,
            patch(
                "origen.deployment_trust_physical_composition_v1._inspect_receipt_with_deployment_trust_provider_snapshot",
                create=True,
            ) as deployment,
        ):
            with self.assertRaisesRegex(
                TrustStateRejected,
                "policy root/key ID/bootstrap floor differs",
            ):
                verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                    RECEIPT,
                    POLICY,
                    provider=Provider(),
                    physical_verification_kwargs={"verification_time": NOW},
                )

        physical.assert_not_called()
        deployment.assert_not_called()

    def test_real_synthetic_provider_path_reuses_one_snapshot_and_commits(self):
        provider_case = TestDeploymentTrustProviderV1()
        provider_case.setUp()
        context = physical_context(
            policy_root_public_key_bytes=provider_case.root_public_key,
            policy_root_key_id=ROOT_KEY_ID,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
        )
        snapshot = replace(
            provider_case.snapshot,
            physical_trust_context_generation=context.context_generation,
            physical_trust_context_sha256=physical_trust_context_sha256(context),
        )
        inner = provider_case.provider
        inner.snapshot = snapshot

        class Provider:
            def __init__(self):
                self.snapshot_reads = 0
                self.context_reads = 0

            def read_snapshot(self, *, policy_domain):
                self.snapshot_reads += 1
                return inner.read_snapshot(policy_domain=policy_domain)

            def read_physical_trust_context(self, *, policy_domain):
                self.context_reads += 1
                return context

            def compare_and_advance(self, **kwargs):
                return inner.compare_and_advance(**kwargs)

        provider = Provider()
        with patch(
            "origen.deployment_trust_physical_composition_v1.verify_custody_timestamp_ledger_witness_v1",
            return_value=physical_result(),
        ):
            result = verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                provider_case.receipt_bytes,
                provider_case.policy_bytes,
                provider=provider,
                physical_verification_kwargs={},
            )

        self.assertEqual(provider.snapshot_reads, 1)
        self.assertEqual(provider.context_reads, 1)
        self.assertEqual(inner.commit_count, 1)
        self.assertEqual(
            inner.last_commit_arguments["policy_sequence"],
            POLICY_SEQUENCE,
        )
        self.assertEqual(
            inner.last_commit_arguments["expected_state_generation"],
            snapshot.state_generation,
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIs(
            result.deployment_trust_inspection.provenance_status,
            ProvenanceStatus.BLOCKED_PROVENANCE,
        )
        self.assertEqual(
            result.deployment_trust_inspection.state_generation_after,
            snapshot.state_generation + 1,
        )

    def test_caller_cannot_supply_physical_trust_anchors_or_floors(self):
        with self.assertRaisesRegex(ValueError, "caller must not supply physical trust anchors"):
            verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                RECEIPT,
                POLICY,
                provider=object(),
                physical_verification_kwargs={
                    "pinned_log_public_key_bytes": b"caller-controlled",
                },
            )

    def test_shared_bytes_cannot_be_overridden_in_physical_kwargs(self):
        with self.assertRaisesRegex(ValueError, "must not override shared trust inputs"):
            verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                RECEIPT,
                POLICY,
                provider=object(),
                physical_verification_kwargs={
                    "verification_time": NOW,
                    "original_receipt_bytes": b"other",
                },
            )


if __name__ == "__main__":
    unittest.main()
