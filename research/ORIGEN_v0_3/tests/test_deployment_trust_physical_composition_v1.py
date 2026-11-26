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


NOW = datetime(2026, 11, 26, 20, 0, tzinfo=timezone.utc)
RECEIPT = b"synthetic exact receipt"
POLICY = b"synthetic exact signed policy"


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
        snapshot = SimpleNamespace(trusted_time_utc=NOW)

        class Provider:
            def read_snapshot(self, *, policy_domain):
                events.append(("snapshot", policy_domain))
                return snapshot

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

        self.assertEqual([event[0] for event in events], ["snapshot", "physical", "provider"])
        self.assertEqual(events[1][1:3], (RECEIPT, POLICY))
        self.assertEqual(events[1][3], NOW)  # caller time is overwritten
        self.assertEqual(events[2][1:3], (RECEIPT, POLICY))
        self.assertIs(events[2][3], provider)
        self.assertIs(events[2][4], snapshot)
        self.assertEqual(result.receipt_sha256, hashlib.sha256(RECEIPT).hexdigest())
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertNotIn(
            "PHYSICAL_VERIFIER_CLOCK_IS_CALLER_SUPPLIED_NOT_PROVIDER_SNAPSHOT",
            result.remaining_blockers,
        )

    def test_failed_physical_bundle_never_reads_or_advances_provider(self):
        class Provider:
            def read_snapshot(self, *, policy_domain):
                return object()

        provider = Provider()
        with (
            patch(
                "origen.deployment_trust_physical_composition_v1._snapshot_copy",
                return_value=SimpleNamespace(trusted_time_utc=NOW),
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
