"""Synthetic orchestration tests; no institutional trust is represented."""
from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from origen.deployment_trust_provider_v1 import DeploymentTrustInspection
from origen.deployment_trust_physical_composition_v1 import (
    verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1,
)
from origen.custody_ledger_witness_integration_v1 import CustodyLedgerWitnessInspectionV1
from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_trust_context_v1 import (
    PhysicalTrustContextV1,
    physical_trust_context_sha256,
)


NOW = datetime(2026, 11, 26, 20, 0, tzinfo=timezone.utc)
RECEIPT = b"synthetic exact receipt"
POLICY = b"synthetic exact signed policy"



def physical_context():
    policy_tsa = b"synthetic policy TSA certificate"
    custody_tsa = b"synthetic custody TSA certificate"
    return PhysicalTrustContextV1(
        policy_tsa_root_certificate_der=policy_tsa,
        policy_tsa_root_sha256=hashlib.sha256(policy_tsa).hexdigest(),
        policy_tsa_policy_oid="1.2.3.4",
        policy_root_public_key_bytes=b"p" * 32,
        policy_root_key_id="synthetic-policy-root",
        minimum_policy_sequence=7,
        custody_tsa_root_certificate_der=custody_tsa,
        custody_tsa_root_sha256=hashlib.sha256(custody_tsa).hexdigest(),
        log_public_key_bytes=b"l" * 32,
        log_id="synthetic-log",
        log_key_id="synthetic-log-key",
        registry_root_public_key_bytes=b"r" * 32,
        registry_root_key_id="synthetic-registry-root",
        registry_id="synthetic-registry",
        minimum_registry_sequence=4,
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
        snapshot = SimpleNamespace(
            trusted_time_utc=NOW,
            physical_trust_context_sha256=physical_trust_context_sha256(context),
        )

        class Provider:
            def read_snapshot(self, *, policy_domain):
                events.append(("snapshot", policy_domain))
                return snapshot

            def read_physical_trust_context(self, *, policy_domain):
                events.append(("physical-context", policy_domain))
                return context

        provider = Provider()

        def physical(receipt, policy, **kwargs):
            events.append(("physical", receipt, policy, kwargs["verification_time"]))
            return physical_result()

        def deployment(receipt, policy, *, provider, **kwargs):
            events.append(("provider", receipt, policy, provider, kwargs.get("provider_snapshot")))
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
                "origen.deployment_trust_physical_composition_v1.inspect_receipt_with_deployment_trust_provider",
                side_effect=deployment,
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
        self.assertEqual(result.receipt_sha256, hashlib.sha256(RECEIPT).hexdigest())
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn(
            "PHYSICAL_VERIFIER_CLOCK_IS_CALLER_SUPPLIED_NOT_PROVIDER_SNAPSHOT",
            result.remaining_blockers,
        )

    def test_changed_physical_context_is_rejected_before_verification(self):
        original_context = physical_context()
        changed_context = physical_context(log_id="attacker-substituted-log")
        snapshot = SimpleNamespace(
            trusted_time_utc=NOW,
            physical_trust_context_sha256=physical_trust_context_sha256(original_context),
        )

        class Provider:
            def read_snapshot(self, *, policy_domain):
                return object()

            def read_physical_trust_context(self, *, policy_domain):
                return changed_context

        with (
            patch(
                "origen.deployment_trust_physical_composition_v1._snapshot_copy",
                return_value=snapshot,
            ),
            patch(
                "origen.deployment_trust_physical_composition_v1.verify_custody_timestamp_ledger_witness_v1"
            ) as physical,
        ):
            with self.assertRaisesRegex(RuntimeError, "does not bind the exact physical trust context"):
                verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
                    RECEIPT,
                    POLICY,
                    provider=Provider(),
                    physical_verification_kwargs={},
                )
        physical.assert_not_called()

    def test_failed_physical_bundle_never_reads_or_advances_provider(self):
        context = physical_context()
        snapshot = SimpleNamespace(
            trusted_time_utc=NOW,
            physical_trust_context_sha256=physical_trust_context_sha256(context),
        )

        class Provider:
            def read_snapshot(self, *, policy_domain):
                return object()

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
                "origen.deployment_trust_physical_composition_v1.inspect_receipt_with_deployment_trust_provider"
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
