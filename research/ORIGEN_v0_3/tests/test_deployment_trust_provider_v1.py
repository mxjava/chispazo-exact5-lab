"""Synthetic adversarial tests for the deployment trust-provider contract."""
from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    DeploymentTrustCommit,
    DeploymentTrustSnapshot,
    TrustProviderUnavailable,
    TrustStateOutcome,
    TrustStateRejected,
    inspect_receipt_with_deployment_trust_provider,
)
from origen.independent_trust_adapter import ProvenanceStatus
from test_receipt_policy_integration_v3 import (
    POLICY_SEQUENCE,
    ROOT_KEY_ID,
    signed_v3_policy,
)
from test_trust_verifier_v1 import NOW, signed_receipt


class SyntheticTrustProvider:
    """Test-only CAS provider. It is not a deployment backend."""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.read_count = 0
        self.commit_count = 0
        self.last_commit_arguments = None
        self.race_before_commit = False
        self.fail_read = False
        self.fail_commit = False

    def read_snapshot(self, *, policy_domain):
        self.read_count += 1
        if self.fail_read:
            raise OSError("synthetic provider outage")
        # Return the stored snapshot even when it is mis-scoped so the
        # application boundary, not this test double, must reject it.
        return self.snapshot

    def compare_and_advance(
        self,
        *,
        expected_state_generation,
        policy_domain,
        root_key_id,
        root_generation,
        policy_sequence,
        policy_envelope_sha256,
        accepted_at_utc,
        clock_uncertainty_ms,
    ):
        self.commit_count += 1
        self.last_commit_arguments = {
            "expected_state_generation": expected_state_generation,
            "policy_domain": policy_domain,
            "root_key_id": root_key_id,
            "root_generation": root_generation,
            "policy_sequence": policy_sequence,
            "policy_envelope_sha256": policy_envelope_sha256,
            "accepted_at_utc": accepted_at_utc,
            "clock_uncertainty_ms": clock_uncertainty_ms,
        }
        if self.fail_commit:
            raise OSError("synthetic durable commit failure")
        if self.race_before_commit:
            self.snapshot = replace(
                self.snapshot,
                state_generation=self.snapshot.state_generation + 1,
            )
        if expected_state_generation != self.snapshot.state_generation:
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if policy_domain != self.snapshot.policy_domain:
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if root_key_id != self.snapshot.root_key_id or root_generation != self.snapshot.root_generation:
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if policy_sequence < self.snapshot.accepted_policy_sequence:
            return DeploymentTrustCommit(
                TrustStateOutcome.ROLLBACK,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if (
            policy_sequence == self.snapshot.accepted_policy_sequence
            and policy_envelope_sha256 != self.snapshot.accepted_policy_envelope_sha256
        ):
            return DeploymentTrustCommit(
                TrustStateOutcome.EQUIVOCATION,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )

        candidate_earliest = accepted_at_utc - timedelta(milliseconds=clock_uncertainty_ms)
        candidate_latest = accepted_at_utc + timedelta(milliseconds=clock_uncertainty_ms)
        if (
            self.snapshot.trusted_time_latest_utc is not None
            and candidate_earliest < self.snapshot.trusted_time_latest_utc
        ):
            return DeploymentTrustCommit(
                TrustStateOutcome.TIME_ROLLBACK,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )

        if policy_sequence == self.snapshot.accepted_policy_sequence:
            if candidate_latest > self.snapshot.trusted_time_latest_utc:
                next_generation = self.snapshot.state_generation + 1
                self.snapshot = replace(
                    self.snapshot,
                    state_generation=next_generation,
                    trusted_time_latest_utc=candidate_latest,
                )
                return DeploymentTrustCommit(
                    TrustStateOutcome.TIME_ADVANCED,
                    next_generation,
                    policy_sequence,
                    policy_envelope_sha256,
                    candidate_latest,
                )
            return DeploymentTrustCommit(
                TrustStateOutcome.IDEMPOTENT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )

        next_generation = self.snapshot.state_generation + 1
        self.snapshot = replace(
            self.snapshot,
            state_generation=next_generation,
            accepted_policy_sequence=policy_sequence,
            accepted_policy_envelope_sha256=policy_envelope_sha256,
            trusted_time_latest_utc=accepted_at_utc + timedelta(milliseconds=clock_uncertainty_ms),
        )
        return DeploymentTrustCommit(
            TrustStateOutcome.ADVANCED,
            next_generation,
            policy_sequence,
            policy_envelope_sha256,
            self.snapshot.trusted_time_latest_utc,
        )


class TestDeploymentTrustProviderV1(unittest.TestCase):
    def setUp(self):
        self.receipt_bytes, self.receipt_public_key, _ = signed_receipt()
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key
        )
        self.snapshot = DeploymentTrustSnapshot(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            root_public_key_bytes=self.root_public_key,
            root_key_id=ROOT_KEY_ID,
            root_generation=1,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
            state_generation=7,
            accepted_policy_sequence=POLICY_SEQUENCE - 1,
            accepted_policy_envelope_sha256="a" * 64,
            trusted_time_latest_utc=NOW - timedelta(seconds=1),
            trusted_time_utc=NOW,
            clock_uncertainty_ms=0,
            maximum_clock_uncertainty_ms=100,
            clock_source_id="synthetic-clock",
            state_backend_id="synthetic-cas-store",
            provisioning_record_sha256="b" * 64,
        )
        self.provider = SyntheticTrustProvider(self.snapshot)

    def inspect(self, **overrides):
        args = {
            "original_receipt_bytes": self.receipt_bytes,
            "signed_policy_envelope_bytes": self.policy_bytes,
            "provider": self.provider,
        }
        args.update(overrides)
        return inspect_receipt_with_deployment_trust_provider(**args)

    def test_valid_policy_and_receipt_atomically_advance_but_remain_blocked(self):
        result = self.inspect()
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.state_generation_before, 7)
        self.assertEqual(result.state_generation_after, 8)
        self.assertIs(result.state_outcome, TrustStateOutcome.ADVANCED)
        self.assertEqual(self.provider.snapshot.accepted_policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(self.provider.snapshot.trusted_time_latest_utc, NOW)
        self.assertEqual(
            self.provider.snapshot.accepted_policy_envelope_sha256,
            result.policy_envelope_sha256,
        )
        self.assertNotIn("AUTHENTICATED", ProvenanceStatus.__members__)

    def test_same_sequence_and_same_exact_digest_is_idempotent(self):
        import hashlib
        self.provider.snapshot = replace(
            self.snapshot,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
            accepted_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_envelope_sha256=hashlib.sha256(self.policy_bytes).hexdigest(),
            trusted_time_utc=NOW - timedelta(seconds=1),
        )
        result = self.inspect()
        self.assertIs(result.state_outcome, TrustStateOutcome.IDEMPOTENT)
        self.assertEqual(result.state_generation_before, result.state_generation_after)
        self.assertEqual(self.provider.commit_count, 1)

    def test_same_sequence_inspection_persists_later_clock_watermark(self):
        import hashlib
        self.provider.snapshot = replace(
            self.snapshot,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
            accepted_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_envelope_sha256=hashlib.sha256(self.policy_bytes).hexdigest(),
            trusted_time_latest_utc=NOW,
            trusted_time_utc=NOW + timedelta(seconds=10),
        )
        result = self.inspect()
        self.assertIs(result.state_outcome, TrustStateOutcome.TIME_ADVANCED)
        self.assertEqual(result.state_generation_before, 7)
        self.assertEqual(result.state_generation_after, 8)
        self.assertEqual(
            self.provider.snapshot.trusted_time_latest_utc,
            NOW + timedelta(seconds=10),
        )
        self.assertEqual(
            self.provider.snapshot.accepted_policy_sequence,
            POLICY_SEQUENCE,
        )

    def test_clock_rollback_after_later_idempotent_inspection_is_rejected(self):
        import hashlib
        self.provider.snapshot = replace(
            self.snapshot,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
            accepted_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_envelope_sha256=hashlib.sha256(self.policy_bytes).hexdigest(),
            trusted_time_latest_utc=NOW,
            trusted_time_utc=NOW + timedelta(seconds=10),
        )
        first = self.inspect()
        self.assertIs(first.state_outcome, TrustStateOutcome.TIME_ADVANCED)
        self.provider.snapshot = replace(
            self.provider.snapshot,
            trusted_time_utc=NOW + timedelta(seconds=2),
        )
        with self.assertRaisesRegex(
            TrustStateRejected,
            "trusted-time interval regressed behind the persisted time watermark",
        ):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 1)

    def test_same_sequence_idempotency_rejects_trusted_clock_rollback(self):
        import hashlib
        self.provider.snapshot = replace(
            self.snapshot,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
            accepted_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_envelope_sha256=hashlib.sha256(self.policy_bytes).hexdigest(),
            trusted_time_latest_utc=NOW - timedelta(seconds=1),
            trusted_time_utc=NOW - timedelta(seconds=2),
        )
        with self.assertRaisesRegex(
            TrustStateRejected,
            "trusted-time interval regressed behind the persisted time watermark",
        ):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_same_sequence_with_different_valid_envelope_is_equivocation(self):
        root_private = Ed25519PrivateKey.generate()
        first, root_public = signed_v3_policy(
            self.receipt_public_key,
            root_private=root_private,
            expires_at_utc="2026-12-01T00:00:00Z",
        )
        second, _ = signed_v3_policy(
            self.receipt_public_key,
            root_private=root_private,
            expires_at_utc="2026-12-02T00:00:00Z",
        )
        import hashlib
        self.provider.snapshot = replace(
            self.snapshot,
            root_public_key_bytes=root_public,
            minimum_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_envelope_sha256=hashlib.sha256(first).hexdigest(),
        )
        with self.assertRaisesRegex(TrustStateRejected, "different envelope digest"):
            self.inspect(signed_policy_envelope_bytes=second)
        self.assertEqual(self.provider.commit_count, 0)

    def test_lower_sequence_is_rejected_before_provider_commit(self):
        self.provider.snapshot = replace(
            self.snapshot,
            minimum_policy_sequence=POLICY_SEQUENCE + 1,
            accepted_policy_sequence=POLICY_SEQUENCE + 1,
            accepted_policy_envelope_sha256="c" * 64,
        )
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_cas_generation_race_fails_closed(self):
        self.provider.race_before_commit = True
        with self.assertRaisesRegex(TrustStateRejected, "did not commit exactly one generation"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 1)

    def test_provider_read_failure_fails_closed(self):
        self.provider.fail_read = True
        with self.assertRaises(TrustProviderUnavailable):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_provider_durable_commit_failure_fails_closed(self):
        self.provider.fail_commit = True
        with self.assertRaises(TrustProviderUnavailable):
            self.inspect()

    def test_tampered_receipt_never_advances_monotonic_state(self):
        document = json.loads(self.receipt_bytes)
        document["artifacts"][0]["sha256"] = "f" * 64
        tampered = json.dumps(
            document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.inspect(original_receipt_bytes=tampered)
        self.assertEqual(self.provider.commit_count, 0)

    def test_uncertainty_interval_must_not_cross_policy_activation(self):
        activation = NOW - timedelta(milliseconds=30)
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            root_private=None,
            not_before_utc=activation.isoformat().replace("+00:00", "Z"),
        )
        self.provider.snapshot = replace(
            self.snapshot,
            root_public_key_bytes=self.root_public_key,
            clock_uncertainty_ms=40,
            maximum_clock_uncertainty_ms=40,
        )
        with self.assertRaisesRegex(ValueError, "uncertainty interval crosses"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_uncertainty_interval_must_prove_receipt_precedes_verification(self):
        self.provider.snapshot = replace(
            self.snapshot,
            trusted_time_latest_utc=NOW - timedelta(hours=2),
            clock_uncertainty_ms=60 * 60 * 1000,
            maximum_clock_uncertainty_ms=60 * 60 * 1000,
        )
        with self.assertRaisesRegex(ValueError, "not provably before"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_uncertainty_interval_must_not_cross_policy_expiry(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            expires_at_utc="2026-11-23T04:00:00.500Z",
        )
        self.provider.snapshot = replace(
            self.snapshot,
            root_public_key_bytes=self.root_public_key,
            clock_uncertainty_ms=1000,
            maximum_clock_uncertainty_ms=1000,
        )
        with self.assertRaisesRegex(ValueError, "uncertainty interval crosses"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_clock_uncertainty_above_provisioned_limit_is_rejected(self):
        self.provider.snapshot = replace(
            self.snapshot,
            clock_uncertainty_ms=101,
            maximum_clock_uncertainty_ms=100,
        )
        with self.assertRaisesRegex(ValueError, "exceeds the provisioned maximum"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_snapshot_rejects_boolean_sequence_and_wrong_domain(self):
        self.provider.snapshot = replace(
            self.snapshot,
            minimum_policy_sequence=True,
        )
        with self.assertRaisesRegex(ValueError, "minimum_policy_sequence must be an exact integer"):
            self.inspect()
        self.provider.snapshot = replace(
            self.snapshot,
            policy_domain="origen.chispazo.de-las-tres.provenance",
        )
        with self.assertRaisesRegex(ValueError, "fixed CLASSIC domain"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_snapshot_rejects_non_utc_clock_and_missing_provisioning_digest(self):
        self.provider.snapshot = replace(
            self.snapshot,
            trusted_time_utc=NOW.replace(tzinfo=timezone(timedelta(0), name="noncanonical-utc")),
        )
        with self.assertRaisesRegex(ValueError, "exact normalized UTC"):
            self.inspect()
        self.provider.snapshot = replace(
            self.snapshot,
            provisioning_record_sha256="not-a-digest",
        )
        with self.assertRaisesRegex(ValueError, "lowercase SHA-256"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_higher_sequence_rejects_trusted_clock_rollback_before_commit(self):
        self.provider.snapshot = replace(
            self.snapshot,
            trusted_time_latest_utc=NOW + timedelta(milliseconds=1),
        )
        with self.assertRaisesRegex(TrustStateRejected, "regressed behind the persisted time watermark"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_provider_cas_rejects_clock_floor_race(self):
        original = self.provider.compare_and_advance

        def regressed_floor(**kwargs):
            self.provider.snapshot = replace(
                self.provider.snapshot,
                trusted_time_latest_utc=NOW + timedelta(milliseconds=1),
            )
            return original(**kwargs)

        self.provider.compare_and_advance = regressed_floor
        with self.assertRaisesRegex(TrustStateRejected, "compare-and-advance"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 1)
        self.assertEqual(
            self.provider.snapshot.accepted_policy_sequence,
            POLICY_SEQUENCE - 1,
        )

    def test_snapshot_rejects_missing_accepted_time_for_nonempty_sequence(self):
        self.provider.snapshot = replace(
            self.snapshot,
            trusted_time_latest_utc=None,
        )
        with self.assertRaisesRegex(ValueError, "requires an exact normalized UTC trusted-time watermark"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_provider_commit_must_bind_candidate_time_upper_bound(self):
        original = self.provider.compare_and_advance

        def wrong_time(**kwargs):
            commit = original(**kwargs)
            return replace(
                commit,
                trusted_time_latest_utc=NOW - timedelta(seconds=2),
            )

        self.provider.compare_and_advance = wrong_time
        with self.assertRaisesRegex(TrustStateRejected, "candidate clock upper bound"):
            self.inspect()

    def test_provider_commit_must_bind_exact_policy_digest(self):
        original = self.provider.compare_and_advance

        def wrong_digest(**kwargs):
            commit = original(**kwargs)
            return replace(commit, policy_envelope_sha256="f" * 64)

        self.provider.compare_and_advance = wrong_digest
        with self.assertRaisesRegex(TrustStateRejected, "does not bind the exact verified policy"):
            self.inspect()


if __name__ == "__main__":
    unittest.main()
