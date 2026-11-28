"""Synthetic adversarial tests for the deployment trust-provider contract."""
from __future__ import annotations

import base64
import json
import hashlib
import inspect
import unittest
from enum import Enum
from unittest.mock import patch
from dataclasses import replace
from datetime import timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    DeploymentTrustCommit,
    DeploymentTrustSnapshot,
    ExternalEvidenceAdvanceV1,
    ExternalEvidenceWatermarkV1,
    TrustProviderUnavailable,
    TrustStateOutcome,
    TrustStateRejected,
    _accepted_external_evidence_watermark_sha256,
    _deployment_trust_operation_id_sha256,
    _clock_sample_sha256,
    _trust_configuration_sha256,
    _validated_external_evidence_watermark,
    _verify_clock_sample_attestation,
    _require_policy_and_receipt_inside_time_window,
    _time_window,
    inspect_receipt_with_deployment_trust_provider,
    _inspect_receipt_with_deployment_trust_provider_using_provider,
)
from origen.independent_trust_adapter import ProvenanceStatus, _verify_independent_provenance_with_explicit_context
from origen.timestamp_nonce_challenge_v1 import timestamp_nonce_challenge_sha256 as compute_timestamp_nonce_challenge_sha256
from test_receipt_policy_integration_v3 import (
    POLICY_SEQUENCE,
    ROOT_KEY_ID,
    signed_v3_policy,
)
from test_trust_verifier_v1 import NOW, signed_receipt
from origen.trust_policy_envelope_v3 import verify_signed_trust_policy_v3
from origen.trust_verifier_v1 import verify_receipt_attestation


def _canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def signed_clock_sample(
    private_key,
    *,
    clock_source_id,
    clock_sample_id,
    key_id,
    trusted_time_utc,
    uncertainty_ms,
    valid_until_utc,
):
    document = {
        "schema": "origen.clock-sample-attestation.v1",
        "policy_domain": CLASSIC_POLICY_DOMAIN,
        "clock_source_id": clock_source_id,
        "clock_sample_id": clock_sample_id,
        "sampled_at_utc": trusted_time_utc.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z"),
        "uncertainty_ms": uncertainty_ms,
        "valid_until_utc": valid_until_utc.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z"),
        "key_id": key_id,
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = dict(document)
    unsigned.pop("signature")
    message = b"ORIGEN_CLOCK_SAMPLE_V1\x00" + _canonical(unsigned)
    document["signature"]["signature_b64"] = base64.b64encode(
        private_key.sign(message)
    ).decode("ascii")
    return _canonical(document)


class SyntheticTrustProvider:
    """Test-only CAS provider. It is not a deployment backend."""

    def __init__(self, snapshot):
        self.operation_receipt_private_key = Ed25519PrivateKey.generate()
        self.operation_receipt_key_id = "synthetic-operation-receipt-key-1"
        operation_receipt_public_key = self.operation_receipt_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.snapshot = replace(
            snapshot,
            operation_receipt_key_id=self.operation_receipt_key_id,
            operation_receipt_public_key_bytes=operation_receipt_public_key,
        )
        self.read_count = 0
        self.operation_receipt_read_count = 0
        self.commit_count = 0
        self.last_commit_arguments = None
        self.race_before_commit = False
        self.fail_read = False
        self.fail_commit = False
        self.commit_time_utc = None
        self.pending_timestamp_nonce_challenge = None
        self.consumed_timestamp_nonce_challenge_ids = set()
        self.consumed_timestamp_nonce_values = set()
        self.operation_commits = {}
        self.operation_receipt_records = {}

    def read_snapshot(self, *, policy_domain):
        self.read_count += 1
        if self.fail_read:
            raise OSError("synthetic provider outage")
        # Return the stored snapshot even when it is mis-scoped so the
        # application boundary, not this test double, must reject it.
        return self.snapshot

    def read_operation_receipt(
        self, *, policy_domain, expected_state_backend_id, operation_id_sha256
    ):
        self.operation_receipt_read_count += 1
        if policy_domain != CLASSIC_POLICY_DOMAIN:
            raise ValueError("wrong operation receipt policy domain")
        if expected_state_backend_id != self.snapshot.state_backend_id:
            raise ValueError("wrong operation receipt state backend")
        return self.operation_receipt_records.get(operation_id_sha256)

    def _persist_operation_receipt(
        self,
        *,
        expected_state_generation,
        expected_trust_configuration_sha256,
        expected_clock_sample_sha256,
        root_key_id,
        root_generation,
        policy_sequence,
        policy_envelope_sha256,
        raw_policy_envelope_bytes,
        raw_receipt_bytes,
        operation_id_sha256,
        commit,
    ):
        earliest, latest = _time_window(self.snapshot)
        stamp = lambda value: value.isoformat(timespec="microseconds").replace("+00:00", "Z")
        document = {
            "schema": "origen.deployment-trust-operation-receipt.v1",
            "policy_domain": CLASSIC_POLICY_DOMAIN,
            "state_backend_id": self.snapshot.state_backend_id,
            "operation_id_sha256": operation_id_sha256,
            "policy_envelope_sha256": hashlib.sha256(raw_policy_envelope_bytes).hexdigest(),
            "receipt_sha256": hashlib.sha256(raw_receipt_bytes).hexdigest(),
            "policy_sequence": policy_sequence,
            "state_generation_before": expected_state_generation,
            "state_generation_after": commit.state_generation,
            "outcome": commit.outcome.value,
            "accepted_external_evidence_watermark_sha256": commit.accepted_external_evidence_watermark_sha256,
            "trusted_time_latest_utc": stamp(commit.trusted_time_latest_utc),
            "root_key_id": root_key_id,
            "root_generation": root_generation,
            "provisioning_record_sha256": self.snapshot.provisioning_record_sha256,
            "trust_configuration_sha256": expected_trust_configuration_sha256,
            "clock_source_id": self.snapshot.clock_source_id,
            "clock_sample_sha256": expected_clock_sample_sha256,
            "clock_sample_valid_until_utc": stamp(self.snapshot.clock_sample_valid_until_utc),
            "time_window_start_utc": stamp(earliest),
            "time_window_end_utc": stamp(latest),
            "provider_key_id": self.snapshot.operation_receipt_key_id,
        }
        message = b"ORIGEN_DEPLOYMENT_TRUST_OPERATION_RECEIPT_V1\x00" + _canonical(document)
        document["signature_b64"] = base64.b64encode(
            self.operation_receipt_private_key.sign(message)
        ).decode("ascii")
        self.operation_receipt_records[operation_id_sha256] = _canonical(document)

    def _consume_timestamp_nonce_challenge(self, challenge_id):
        challenge = self.pending_timestamp_nonce_challenge
        self.consumed_timestamp_nonce_challenge_ids.add(challenge_id)
        self.consumed_timestamp_nonce_values.add(challenge.policy_timestamp_nonce)
        self.consumed_timestamp_nonce_values.add(challenge.custody_timestamp_nonce)

    def compare_and_advance(
        self,
        *,
        expected_state_generation,
        expected_trust_configuration_sha256,
        expected_clock_sample_sha256,
        policy_domain,
        root_key_id,
        root_generation,
        policy_sequence,
        policy_envelope_sha256,
        expected_external_evidence_watermark_sha256,
        operation_id_sha256,
        raw_policy_envelope_bytes,
        raw_receipt_bytes,
        external_evidence_advance=None,
        timestamp_nonce_challenge_id=None,
        timestamp_nonce_challenge_sha256=None,
    ):
        self.commit_count += 1
        self.last_commit_arguments = {
            "expected_state_generation": expected_state_generation,
            "expected_trust_configuration_sha256": expected_trust_configuration_sha256,
            "expected_clock_sample_sha256": expected_clock_sample_sha256,
            "policy_domain": policy_domain,
            "root_key_id": root_key_id,
            "root_generation": root_generation,
            "policy_sequence": policy_sequence,
            "policy_envelope_sha256": policy_envelope_sha256,
            "expected_external_evidence_watermark_sha256": expected_external_evidence_watermark_sha256,
            "operation_id_sha256": operation_id_sha256,
            "raw_policy_envelope_bytes": raw_policy_envelope_bytes,
            "raw_receipt_bytes": raw_receipt_bytes,
            "external_evidence_advance": external_evidence_advance,
            "timestamp_nonce_challenge_id": timestamp_nonce_challenge_id,
            "timestamp_nonce_challenge_sha256": timestamp_nonce_challenge_sha256,
        }
        try:
            expected_operation_id = _deployment_trust_operation_id_sha256(
                raw_policy_envelope_bytes,
                raw_receipt_bytes,
                external_evidence_advance,
            )
        except (TypeError, ValueError):
            expected_operation_id = None
        if operation_id_sha256 != expected_operation_id:
            return DeploymentTrustCommit(
                TrustStateOutcome.EQUIVOCATION,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if operation_id_sha256 in self.operation_commits:
            return DeploymentTrustCommit(
                TrustStateOutcome.IDEMPOTENT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
                _accepted_external_evidence_watermark_sha256(
                    self.snapshot.accepted_external_evidence_watermark
                ),
                hashlib.sha256(raw_receipt_bytes).hexdigest(),
                operation_id_sha256,
            )
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
        try:
            _verify_clock_sample_attestation(self.snapshot)
        except (TypeError, ValueError):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if expected_clock_sample_sha256 != _clock_sample_sha256(self.snapshot):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if (
            self.commit_time_utc is not None
            and self.commit_time_utc > self.snapshot.clock_sample_valid_until_utc
        ):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if expected_trust_configuration_sha256 != _trust_configuration_sha256(self.snapshot):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if (
            type(raw_policy_envelope_bytes) is not bytes
            or not raw_policy_envelope_bytes
            or type(raw_receipt_bytes) is not bytes
            or not raw_receipt_bytes
        ):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if external_evidence_advance is not None and (
            external_evidence_advance.raw_policy_envelope_bytes != raw_policy_envelope_bytes
            or external_evidence_advance.raw_receipt_bytes != raw_receipt_bytes
        ):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        try:
            provider_policy = verify_signed_trust_policy_v3(
                raw_policy_envelope_bytes,
                pinned_root_public_key_bytes=self.snapshot.root_public_key_bytes,
                expected_root_key_id=self.snapshot.root_key_id,
                expected_policy_domain=CLASSIC_POLICY_DOMAIN,
                minimum_policy_sequence=max(
                    self.snapshot.minimum_policy_sequence,
                    self.snapshot.accepted_policy_sequence,
                ),
                verification_time=self.snapshot.trusted_time_utc,
            )
            provider_receipt = verify_receipt_attestation(
                raw_receipt_bytes,
                provider_policy.policy,
                verification_time=self.snapshot.trusted_time_utc,
            )
            earliest, latest = _time_window(self.snapshot)
            _require_policy_and_receipt_inside_time_window(
                provider_policy,
                provider_receipt,
                earliest=earliest,
                latest=latest,
            )
        except Exception:
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if (
            provider_policy.policy_sequence != policy_sequence
            or hashlib.sha256(raw_policy_envelope_bytes).hexdigest() != policy_envelope_sha256
        ):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if (timestamp_nonce_challenge_id is None) != (timestamp_nonce_challenge_sha256 is None):
            return DeploymentTrustCommit(
                TrustStateOutcome.CONFLICT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
            )
        if timestamp_nonce_challenge_id is not None:
            challenge = self.pending_timestamp_nonce_challenge
            if (
                challenge is None
                or challenge.challenge_id != timestamp_nonce_challenge_id
                or compute_timestamp_nonce_challenge_sha256(challenge) != timestamp_nonce_challenge_sha256
                or challenge.policy_domain != self.snapshot.policy_domain
                or challenge.state_backend_id != self.snapshot.state_backend_id
                or challenge.challenge_id in self.consumed_timestamp_nonce_challenge_ids
                or challenge.policy_timestamp_nonce in self.consumed_timestamp_nonce_values
                or challenge.custody_timestamp_nonce in self.consumed_timestamp_nonce_values
                or challenge.state_generation != expected_state_generation
                or challenge.state_generation != self.snapshot.state_generation
                or challenge.root_generation != self.snapshot.root_generation
                or challenge.physical_trust_context_generation != self.snapshot.physical_trust_context_generation
                or challenge.physical_trust_context_sha256 != self.snapshot.physical_trust_context_sha256
                or challenge.issued_at_utc > self.snapshot.trusted_time_utc
                or (self.commit_time_utc or self.snapshot.trusted_time_utc) >= challenge.expires_at_utc
            ):
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

        # Provider time is derived from its own signed current sample, not caller input.
        candidate_earliest = self.snapshot.trusted_time_utc - timedelta(
            milliseconds=self.snapshot.clock_uncertainty_ms
        )
        candidate_latest = self.snapshot.trusted_time_utc + timedelta(
            milliseconds=self.snapshot.clock_uncertainty_ms
        )
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

        try:
            next_watermark = _validated_external_evidence_watermark(
                self.snapshot,
                expected_external_evidence_watermark_sha256,
                external_evidence_advance,
            )
        except TrustStateRejected as exc:
            if "new ledger checkpoint does not extend the exact persisted checkpoint" in str(exc):
                return DeploymentTrustCommit(
                    TrustStateOutcome.CONFLICT,
                    self.snapshot.state_generation,
                    policy_sequence,
                    policy_envelope_sha256,
                    self.snapshot.trusted_time_latest_utc,
                )
            raise
        policy_advanced = policy_sequence > self.snapshot.accepted_policy_sequence
        time_advanced = (
            self.snapshot.trusted_time_latest_utc is None
            or candidate_latest > self.snapshot.trusted_time_latest_utc
        )
        evidence_advanced = next_watermark != self.snapshot.accepted_external_evidence_watermark

        if timestamp_nonce_challenge_id is not None:
            self._consume_timestamp_nonce_challenge(timestamp_nonce_challenge_id)

        if not (policy_advanced or time_advanced or evidence_advanced):
            commit = DeploymentTrustCommit(
                TrustStateOutcome.IDEMPOTENT,
                self.snapshot.state_generation,
                policy_sequence,
                policy_envelope_sha256,
                self.snapshot.trusted_time_latest_utc,
                _accepted_external_evidence_watermark_sha256(next_watermark),
                hashlib.sha256(raw_receipt_bytes).hexdigest(),
                operation_id_sha256,
            )
            self.operation_commits[operation_id_sha256] = commit
            self._persist_operation_receipt(
                expected_state_generation=expected_state_generation,
                expected_trust_configuration_sha256=expected_trust_configuration_sha256,
                expected_clock_sample_sha256=expected_clock_sample_sha256,
                root_key_id=root_key_id,
                root_generation=root_generation,
                policy_sequence=policy_sequence,
                policy_envelope_sha256=policy_envelope_sha256,
                raw_policy_envelope_bytes=raw_policy_envelope_bytes,
                raw_receipt_bytes=raw_receipt_bytes,
                operation_id_sha256=operation_id_sha256,
                commit=commit,
            )
            return commit

        if policy_advanced:
            outcome = TrustStateOutcome.ADVANCED
        elif evidence_advanced and time_advanced:
            outcome = TrustStateOutcome.TIME_AND_EVIDENCE_ADVANCED
        elif evidence_advanced:
            outcome = TrustStateOutcome.EVIDENCE_ADVANCED
        else:
            outcome = TrustStateOutcome.TIME_ADVANCED

        next_generation = self.snapshot.state_generation + 1
        self.snapshot = replace(
            self.snapshot,
            state_generation=next_generation,
            accepted_policy_sequence=policy_sequence if policy_advanced else self.snapshot.accepted_policy_sequence,
            accepted_policy_envelope_sha256=policy_envelope_sha256 if policy_advanced else self.snapshot.accepted_policy_envelope_sha256,
            trusted_time_latest_utc=candidate_latest if time_advanced else self.snapshot.trusted_time_latest_utc,
            accepted_external_evidence_watermark=next_watermark,
        )
        commit = DeploymentTrustCommit(
            outcome,
            next_generation,
            policy_sequence,
            policy_envelope_sha256,
            self.snapshot.trusted_time_latest_utc,
            _accepted_external_evidence_watermark_sha256(next_watermark),
            hashlib.sha256(raw_receipt_bytes).hexdigest(),
            operation_id_sha256,
        )
        self.operation_commits[operation_id_sha256] = commit
        self._persist_operation_receipt(
            expected_state_generation=expected_state_generation,
            expected_trust_configuration_sha256=expected_trust_configuration_sha256,
            expected_clock_sample_sha256=expected_clock_sample_sha256,
            root_key_id=root_key_id,
            root_generation=root_generation,
            policy_sequence=policy_sequence,
            policy_envelope_sha256=policy_envelope_sha256,
            raw_policy_envelope_bytes=raw_policy_envelope_bytes,
            raw_receipt_bytes=raw_receipt_bytes,
            operation_id_sha256=operation_id_sha256,
            commit=commit,
        )
        return commit


class TestDeploymentTrustProviderV1(unittest.TestCase):
    def setUp(self):
        self.receipt_bytes, self.receipt_public_key, _ = signed_receipt()
        self.clock_private_key = Ed25519PrivateKey.generate()
        self.clock_public_key_bytes = self.clock_private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        self.clock_sample_key_id = "synthetic-clock-key-1"
        self.clock_sample_id = "synthetic-clock-sample-0001"
        clock_authorization = self.clock_policy_key_entry()
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            additional_issuer_keys=(clock_authorization,),
        )
        self.clock_sample_valid_until_utc = NOW + timedelta(seconds=60)
        self.clock_sample_envelope_bytes = signed_clock_sample(
            self.clock_private_key,
            clock_source_id="synthetic-clock",
            clock_sample_id=self.clock_sample_id,
            key_id=self.clock_sample_key_id,
            trusted_time_utc=NOW,
            uncertainty_ms=0,
            valid_until_utc=self.clock_sample_valid_until_utc,
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
            clock_sample_key_id=self.clock_sample_key_id,
            clock_sample_public_key_bytes=self.clock_public_key_bytes,
            clock_sample_envelope_bytes=self.clock_sample_envelope_bytes,
            clock_sample_id=self.clock_sample_id,
            clock_sample_valid_until_utc=NOW + timedelta(seconds=60),
            maximum_clock_sample_age_ms=120_000,
            state_backend_id="synthetic-cas-store",
            provisioning_record_sha256="b" * 64,
        )
        self.provider = SyntheticTrustProvider(self.snapshot)
        # Subsequent fixture mutations must retain the provider-pinned synthetic
        # operation-receipt verification key and its trust-configuration binding.
        self.snapshot = self.provider.snapshot

    def with_signed_sample(self, snapshot, **changes):
        candidate = replace(snapshot, **changes)
        envelope = signed_clock_sample(
            self.clock_private_key,
            clock_source_id=candidate.clock_source_id,
            clock_sample_id=candidate.clock_sample_id,
            key_id=candidate.clock_sample_key_id,
            trusted_time_utc=candidate.trusted_time_utc,
            uncertainty_ms=candidate.clock_uncertainty_ms,
            valid_until_utc=candidate.clock_sample_valid_until_utc,
        )
        return replace(candidate, clock_sample_envelope_bytes=envelope)

    def clock_policy_key_entry(self, *, revoked=False, role="TRUSTED_TIME_AUTHORITY"):
        return {
            "issuer_id": "synthetic-clock",
            "key_id": self.clock_sample_key_id,
            "public_key_b64": base64.b64encode(self.clock_public_key_bytes).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": revoked,
            "authorizations": [
                {"role": role, "artifact_types": ["CLOCK_SAMPLE"]}
            ],
        }

    def inspect(self, **overrides):
        args = {
            "original_receipt_bytes": self.receipt_bytes,
            "signed_policy_envelope_bytes": self.policy_bytes,
            "provider": self.provider,
        }
        args.update(overrides)
        return _inspect_receipt_with_deployment_trust_provider_using_provider(**args)

    def test_persisted_watermark_backend_mismatch_is_rejected_by_watermark_validator(self):
        watermark = ExternalEvidenceWatermarkV1(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            state_backend_id="another-synthetic-cas-store",
            log_id="synthetic-log",
            log_key_id="synthetic-log-key",
            log_public_key_sha256="a" * 64,
            ledger_tree_size=1,
            ledger_root_sha256="b" * 64,
            ledger_checkpoint_sha256="c" * 64,
            registry_id="synthetic-registry",
            registry_root_key_id="synthetic-registry-root",
            registry_root_public_key_sha256="d" * 64,
            registry_sequence=1,
            registry_sha256="e" * 64,
        )
        snapshot = replace(
            self.snapshot,
            accepted_external_evidence_watermark=watermark,
        )

        with self.assertRaisesRegex(
            TrustStateRejected,
            "persisted external evidence watermark is not bound to the exact policy domain and state backend",
        ):
            _validated_external_evidence_watermark(
                snapshot,
                _accepted_external_evidence_watermark_sha256(watermark),
                None,
            )

    def test_same_size_ledger_checkpoint_requires_exact_old_checkpoint(self):
        raw_current_checkpoint = b"current-signed-checkpoint"
        raw_stale_old_checkpoint = b"stale-old-checkpoint"
        raw_registry = b"signed-registry"
        current = ExternalEvidenceWatermarkV1(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            state_backend_id=self.snapshot.state_backend_id,
            log_id="synthetic-log",
            log_key_id="synthetic-log-key",
            log_public_key_sha256="a" * 64,
            ledger_tree_size=2,
            ledger_root_sha256="b" * 64,
            ledger_checkpoint_sha256=hashlib.sha256(raw_current_checkpoint).hexdigest(),
            registry_id="synthetic-registry",
            registry_root_key_id="synthetic-registry-root",
            registry_root_public_key_sha256="d" * 64,
            registry_sequence=1,
            registry_sha256=hashlib.sha256(raw_registry).hexdigest(),
        )
        snapshot = replace(
            self.snapshot,
            accepted_external_evidence_watermark=current,
        )
        raw_receipt = b"synthetic-stale-checkpoint-receipt"
        raw_policy = b"synthetic-stale-checkpoint-policy"
        raw_artifact = b"synthetic-stale-checkpoint-artifact"
        raw_signature = b"synthetic-stale-checkpoint-signature"
        advance = ExternalEvidenceAdvanceV1(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            state_backend_id=self.snapshot.state_backend_id,
            log_id=current.log_id,
            log_key_id=current.log_key_id,
            log_public_key_sha256=current.log_public_key_sha256,
            old_tree_size=1,
            old_root_sha256="f" * 64,
            old_checkpoint_sha256=hashlib.sha256(raw_stale_old_checkpoint).hexdigest(),
            new_tree_size=2,
            new_root_sha256=current.ledger_root_sha256,
            new_checkpoint_sha256=current.ledger_checkpoint_sha256,
            registry_id=current.registry_id,
            registry_root_key_id=current.registry_root_key_id,
            registry_root_public_key_sha256=current.registry_root_public_key_sha256,
            registry_sequence=current.registry_sequence,
            registry_sha256=current.registry_sha256,
            raw_manifest_bytes=b"manifest",
            raw_ledger_entry_bytes=b"ledger-entry",
            raw_inclusion_proof_bytes=b"inclusion-proof",
            raw_old_checkpoint_bytes=raw_stale_old_checkpoint,
            raw_new_checkpoint_bytes=raw_current_checkpoint,
            raw_consistency_proof_bytes=b"consistency-proof",
            raw_registry_bytes=raw_registry,
            raw_witness_statement_bytes=(b"witness-statement-1", b"witness-statement-2"),
            receipt_sha256=hashlib.sha256(raw_receipt).hexdigest(),
            policy_envelope_sha256=hashlib.sha256(raw_policy).hexdigest(),
            raw_receipt_bytes=raw_receipt,
            raw_policy_envelope_bytes=raw_policy,
            raw_custody_record_bytes=b"synthetic-custody-record",
            raw_portfolio_bytes=b"synthetic-portfolio",
            raw_custody_signature_bytes=b"synthetic-custody-signature",
            custodian_key_id="synthetic-custodian",
            raw_timestamp_token_der=b"synthetic-custody-timestamp-token",
            raw_policy_timestamp_token_der=b"synthetic-policy-timestamp-token",
            raw_artifact_bytes_by_sha256=((hashlib.sha256(raw_artifact).hexdigest(), raw_artifact),),
            raw_signature_bytes_by_sha256=((hashlib.sha256(raw_signature).hexdigest(), raw_signature),),
        )

        with self.assertRaisesRegex(
            TrustStateRejected,
            "new ledger checkpoint does not extend the exact persisted checkpoint",
        ):
            _validated_external_evidence_watermark(
                snapshot,
                _accepted_external_evidence_watermark_sha256(current),
                advance,
            )

    def test_clock_sample_signature_and_exact_bytes_are_verified_before_commit(self):
        document = json.loads(self.snapshot.clock_sample_envelope_bytes)
        document["signature"]["signature_b64"] = base64.b64encode(
            bytes(64)
        ).decode("ascii")
        self.provider.snapshot = replace(
            self.snapshot,
            clock_sample_envelope_bytes=_canonical(document),
        )
        with self.assertRaisesRegex(
            ValueError,
            "clock sample Ed25519 signature verification failed",
        ):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_clock_sample_rejects_duplicate_keys_and_noncanonical_bytes(self):
        self.provider.snapshot = replace(
            self.snapshot,
            clock_sample_envelope_bytes=b'{"schema":"one","schema":"two"}',
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.inspect()
        self.provider.snapshot = replace(
            self.snapshot,
            clock_sample_envelope_bytes=b" " + self.clock_sample_envelope_bytes,
        )
        with self.assertRaisesRegex(ValueError, "not canonical JSON"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_clock_sample_key_fingerprint_is_part_of_trust_configuration_digest(self):
        replacement_key = Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        changed = replace(
            self.snapshot,
            clock_sample_public_key_bytes=replacement_key,
        )
        self.assertNotEqual(
            _trust_configuration_sha256(self.snapshot),
            _trust_configuration_sha256(changed),
        )

    def test_clock_sample_claims_must_match_provider_snapshot(self):
        document = json.loads(self.snapshot.clock_sample_envelope_bytes)
        document["clock_source_id"] = "attacker-clock"
        unsigned = dict(document)
        unsigned.pop("signature")
        document["signature"]["signature_b64"] = base64.b64encode(
            self.clock_private_key.sign(
                b"ORIGEN_CLOCK_SAMPLE_V1\x00" + _canonical(unsigned)
            )
        ).decode("ascii")
        self.provider.snapshot = replace(
            self.snapshot,
            clock_sample_envelope_bytes=_canonical(document),
        )
        with self.assertRaisesRegex(
            ValueError,
            "clock sample attestation source does not match provider snapshot",
        ):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_clock_key_must_be_authorized_by_root_signed_policy(self):
        policy_bytes, root_public = signed_v3_policy(self.receipt_public_key)
        self.provider.snapshot = replace(
            self.snapshot,
            root_public_key_bytes=root_public,
        )
        self.policy_bytes = policy_bytes
        with self.assertRaisesRegex(
            ValueError,
            "does not contain exactly one clock-source key",
        ):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_revoked_clock_key_in_root_signed_policy_is_rejected(self):
        clock_authorization = self.clock_policy_key_entry(revoked=True)
        policy_bytes, root_public = signed_v3_policy(
            self.receipt_public_key,
            additional_issuer_keys=(clock_authorization,),
        )
        self.provider.snapshot = replace(
            self.snapshot,
            root_public_key_bytes=root_public,
        )
        self.policy_bytes = policy_bytes
        with self.assertRaisesRegex(ValueError, "clock sample key is revoked"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

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
        expected_configuration = _trust_configuration_sha256(self.snapshot)
        self.assertEqual(
            self.provider.last_commit_arguments["expected_trust_configuration_sha256"],
            expected_configuration,
        )
        self.assertEqual(result.trust_configuration_sha256, expected_configuration)
        expected_clock_sample = _clock_sample_sha256(self.snapshot)
        self.assertEqual(
            self.provider.last_commit_arguments["expected_clock_sample_sha256"],
            expected_clock_sample,
        )
        self.assertEqual(result.clock_sample_sha256, expected_clock_sample)
        self.assertEqual(
            result.clock_sample_valid_until_utc,
            self.snapshot.clock_sample_valid_until_utc,
        )

    def test_independent_boundary_reverifies_exact_bytes_with_provider_owned_context(self):
        with patch(
            "origen.deployment_trust_provider_v1._verify_independent_provenance_with_explicit_context",
            wraps=_verify_independent_provenance_with_explicit_context,
        ) as boundary:
            result = self.inspect()

        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(boundary.call_count, 1)
        args, kwargs = boundary.call_args
        self.assertEqual(args, (self.receipt_bytes,))
        self.assertEqual(kwargs["signed_policy_envelope_bytes"], self.policy_bytes)
        self.assertEqual(
            kwargs["pinned_root_public_key_bytes"],
            self.snapshot.root_public_key_bytes,
        )
        self.assertEqual(kwargs["expected_root_key_id"], self.snapshot.root_key_id)
        self.assertEqual(
            kwargs["minimum_policy_sequence"],
            max(self.snapshot.minimum_policy_sequence, self.snapshot.accepted_policy_sequence),
        )
        self.assertEqual(kwargs["verification_time"], self.snapshot.trusted_time_utc)
        self.assertNotIn("verified_policy", kwargs)
        self.assertNotIn("verified_receipt", kwargs)
        self.assertEqual(self.provider.commit_count, 1)

    def test_unexpected_future_authenticated_status_never_reaches_provider_cas(self):
        class FutureProvenanceStatus(Enum):
            BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"
            AUTHENTICATED = "AUTHENTICATED"

        with patch(
            "origen.deployment_trust_provider_v1._verify_independent_provenance_with_explicit_context",
            return_value=FutureProvenanceStatus.AUTHENTICATED,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "independent provenance gate returned an unsupported non-blocked status",
            ):
                self.inspect()

        self.assertEqual(self.provider.commit_count, 0)
        self.assertEqual(self.provider.snapshot.state_generation, self.snapshot.state_generation)
        self.assertEqual(
            self.provider.snapshot.accepted_policy_sequence,
            self.snapshot.accepted_policy_sequence,
        )

    def test_same_sequence_and_same_exact_digest_is_idempotent(self):
        import hashlib
        self.provider.snapshot = self.with_signed_sample(
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
        self.provider.snapshot = self.with_signed_sample(
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
        self.provider.snapshot = self.with_signed_sample(
            self.snapshot,
            minimum_policy_sequence=POLICY_SEQUENCE - 1,
            accepted_policy_sequence=POLICY_SEQUENCE,
            accepted_policy_envelope_sha256=hashlib.sha256(self.policy_bytes).hexdigest(),
            trusted_time_latest_utc=NOW,
            trusted_time_utc=NOW + timedelta(seconds=10),
        )
        first = self.inspect()
        self.assertIs(first.state_outcome, TrustStateOutcome.TIME_ADVANCED)
        self.provider.snapshot = self.with_signed_sample(
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
        self.provider.snapshot = self.with_signed_sample(
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
            additional_issuer_keys=(self.clock_policy_key_entry(),),
        )
        second, _ = signed_v3_policy(
            self.receipt_public_key,
            root_private=root_private,
            expires_at_utc="2026-12-02T00:00:00Z",
            additional_issuer_keys=(self.clock_policy_key_entry(),),
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
        with self.assertRaisesRegex(TrustStateRejected, "compare-and-advance rejected"):
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
            additional_issuer_keys=(self.clock_policy_key_entry(),),
        )
        self.provider.snapshot = self.with_signed_sample(
            self.snapshot,
            root_public_key_bytes=self.root_public_key,
            clock_uncertainty_ms=40,
            maximum_clock_uncertainty_ms=40,
        )
        with self.assertRaisesRegex(ValueError, "uncertainty interval crosses"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_uncertainty_interval_must_prove_receipt_precedes_verification(self):
        self.provider.snapshot = self.with_signed_sample(
            self.snapshot,
            trusted_time_latest_utc=NOW - timedelta(hours=2),
            clock_uncertainty_ms=60 * 60 * 1000,
            maximum_clock_uncertainty_ms=60 * 60 * 1000,
            clock_sample_valid_until_utc=NOW + timedelta(hours=1, minutes=1),
            maximum_clock_sample_age_ms=4_000_000,
        )
        with self.assertRaisesRegex(ValueError, "not provably before"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_uncertainty_interval_must_not_cross_policy_expiry(self):
        self.policy_bytes, self.root_public_key = signed_v3_policy(
            self.receipt_public_key,
            expires_at_utc="2026-11-23T04:00:00.500Z",
            additional_issuer_keys=(self.clock_policy_key_entry(),),
        )
        self.provider.snapshot = self.with_signed_sample(
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
        generation_before = self.provider.snapshot.state_generation
        with self.assertRaisesRegex(TrustProviderUnavailable, "commit acknowledgement"):
            self.inspect()
        self.assertGreater(self.provider.snapshot.state_generation, generation_before)


    def test_clock_sample_expiry_and_maximum_age_are_enforced_before_commit(self):
        self.provider.snapshot = self.with_signed_sample(
            self.snapshot,
            clock_sample_valid_until_utc=NOW - timedelta(microseconds=1),
        )
        with self.assertRaisesRegex(ValueError, "provider clock sample lease is already expired"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

        self.provider.snapshot = self.with_signed_sample(
            self.snapshot,
            clock_sample_valid_until_utc=NOW + timedelta(seconds=121),
            maximum_clock_sample_age_ms=120_000,
        )
        with self.assertRaisesRegex(ValueError, "exceeds the provisioned maximum age"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)

    def test_clock_uncertainty_interval_must_fit_inside_sample_lease(self):
        self.provider.snapshot = self.with_signed_sample(
            self.snapshot,
            clock_uncertainty_ms=61_000,
            maximum_clock_uncertainty_ms=61_000,
            clock_sample_valid_until_utc=NOW + timedelta(seconds=60),
            maximum_clock_sample_age_ms=120_000,
        )
        with self.assertRaisesRegex(ValueError, "uncertainty interval exceeds the provider clock sample lease"):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 0)


    def test_provider_rejects_sample_lease_expired_at_cas_time(self):
        # The snapshot was valid when read, but the provider's authoritative
        # clock has passed the source-issued lease by the time CAS executes.
        self.provider.commit_time_utc = NOW + timedelta(seconds=61)
        with self.assertRaisesRegex(
            TrustStateRejected,
            "rejected a stale, regressed, or equivocal state",
        ):
            self.inspect()
        self.assertEqual(self.provider.commit_count, 1)
        self.assertEqual(
            self.provider.snapshot.accepted_policy_sequence,
            POLICY_SEQUENCE - 1,
        )

    def test_provider_rejects_clock_sample_drift_between_read_and_cas(self):
        original_read = self.provider.read_snapshot
        mutations = (
            ("clock_sample_id", "synthetic-clock-sample-0002"),
            ("trusted_time_utc", NOW + timedelta(seconds=1)),
            ("clock_uncertainty_ms", 1),
            ("clock_sample_valid_until_utc", NOW + timedelta(seconds=61)),
        )
        for field, replacement_value in mutations:
            with self.subTest(field=field):
                self.provider.snapshot = self.snapshot
                def read_then_mutate(*, policy_domain):
                    observed = original_read(policy_domain=policy_domain)
                    self.provider.snapshot = replace(
                        self.provider.snapshot,
                        **{field: replacement_value},
                    )
                    return observed
                self.provider.read_snapshot = read_then_mutate
                with self.assertRaisesRegex(
                    TrustStateRejected,
                    "rejected a stale, regressed, or equivocal state",
                ):
                    self.inspect()
                self.assertEqual(
                    self.provider.snapshot.accepted_policy_sequence,
                    POLICY_SEQUENCE - 1,
                )
                self.provider.read_snapshot = original_read
                self.provider.commit_count = 0

    def test_provider_rejects_trust_configuration_drift_without_generation_change(self):
        original_read = self.provider.read_snapshot
        mutations = (
            ("root_public_key_bytes", bytes([153]) * 32),
            ("provisioning_record_sha256", "c" * 64),
            ("clock_source_id", "replacement-clock"),
            ("clock_sample_key_id", "replacement-clock-key"),
            ("clock_sample_public_key_bytes", bytes([154]) * 32),
            ("state_backend_id", "replacement-backend"),
        )
        for field, replacement_value in mutations:
            with self.subTest(field=field):
                self.provider.snapshot = self.snapshot
                def read_then_mutate(*, policy_domain):
                    observed = original_read(policy_domain=policy_domain)
                    self.provider.snapshot = replace(
                        self.provider.snapshot,
                        **{field: replacement_value},
                    )
                    return observed
                self.provider.read_snapshot = read_then_mutate
                if field == "state_backend_id":
                    # A backend change between snapshot and read-only receipt lookup
                    # makes the durable outcome unknown before CAS can be attempted.
                    with self.assertRaisesRegex(
                        TrustProviderUnavailable,
                        "operation-receipt query failed",
                    ):
                        self.inspect()
                    self.assertEqual(self.provider.commit_count, 0)
                else:
                    with self.assertRaisesRegex(
                        TrustStateRejected,
                        "compare-and-advance rejected a stale, regressed, or equivocal state",
                    ):
                        self.inspect()
                    self.assertEqual(self.provider.commit_count, 1)
                self.assertEqual(
                    self.provider.snapshot.accepted_policy_sequence,
                    POLICY_SEQUENCE - 1,
                )
                self.provider.read_snapshot = original_read
                self.provider.commit_count = 0

    def _direct_provider_cas(self, policy_bytes, receipt_bytes):
        provider = SyntheticTrustProvider(self.snapshot)
        commit = provider.compare_and_advance(
            expected_state_generation=self.snapshot.state_generation,
            expected_trust_configuration_sha256=_trust_configuration_sha256(self.snapshot),
            expected_clock_sample_sha256=_clock_sample_sha256(self.snapshot),
            operation_id_sha256=_deployment_trust_operation_id_sha256(
                policy_bytes, receipt_bytes, None
            ),
            policy_domain=CLASSIC_POLICY_DOMAIN,
            root_key_id=self.snapshot.root_key_id,
            root_generation=self.snapshot.root_generation,
            policy_sequence=POLICY_SEQUENCE,
            policy_envelope_sha256=hashlib.sha256(policy_bytes).hexdigest(),
            expected_external_evidence_watermark_sha256=(
                _accepted_external_evidence_watermark_sha256(None)
            ),
            raw_policy_envelope_bytes=policy_bytes,
            raw_receipt_bytes=receipt_bytes,
        )
        return provider, commit

    def test_provider_cas_receives_exact_original_policy_and_receipt_bytes(self):
        self.inspect()
        self.assertEqual(
            self.provider.last_commit_arguments["raw_policy_envelope_bytes"],
            self.policy_bytes,
        )
        self.assertEqual(
            self.provider.last_commit_arguments["raw_receipt_bytes"],
            self.receipt_bytes,
        )

    def test_provider_cas_rejects_tampered_policy_even_when_digest_is_recomputed(self):
        tampered_policy = self.policy_bytes + b" "
        provider, commit = self._direct_provider_cas(tampered_policy, self.receipt_bytes)
        self.assertIs(commit.outcome, TrustStateOutcome.CONFLICT)
        self.assertEqual(provider.snapshot.state_generation, self.snapshot.state_generation)
        self.assertEqual(provider.snapshot.accepted_policy_sequence, self.snapshot.accepted_policy_sequence)

    def test_provider_cas_rejects_tampered_receipt_bytes(self):
        tampered_receipt = self.receipt_bytes + b" "
        provider, commit = self._direct_provider_cas(self.policy_bytes, tampered_receipt)
        self.assertIs(commit.outcome, TrustStateOutcome.CONFLICT)
        self.assertEqual(provider.snapshot.state_generation, self.snapshot.state_generation)
        self.assertEqual(provider.snapshot.accepted_policy_sequence, self.snapshot.accepted_policy_sequence)

    def test_provider_cas_does_not_accept_caller_supplied_time_or_uncertainty(self):
        parameters = inspect.signature(self.provider.compare_and_advance).parameters
        self.assertNotIn("accepted_at_utc", parameters)
        self.assertNotIn("clock_uncertainty_ms", parameters)

    def test_provider_commit_must_bind_exact_receipt_digest(self):
        original = self.provider.compare_and_advance

        def wrong_receipt_digest(**kwargs):
            commit = original(**kwargs)
            return replace(commit, receipt_sha256="f" * 64)

        self.provider.compare_and_advance = wrong_receipt_digest
        generation_before = self.provider.snapshot.state_generation
        with self.assertRaisesRegex(
            TrustProviderUnavailable,
            "commit acknowledgement",
        ):
            self.inspect()
        # The provider's CAS already advanced before returning its bad response.
        # The caller must treat this as an unknown outcome and reconcile, not
        # misclassify it as a rejected transaction and blindly retry.
        self.assertGreater(self.provider.snapshot.state_generation, generation_before)

    def test_malformed_commit_acknowledgement_after_provider_advance_is_outcome_unknown(self):
        original = self.provider.compare_and_advance
        generation_before = self.provider.snapshot.state_generation

        def malformed_acknowledgement(**kwargs):
            original(**kwargs)
            return object()

        self.provider.compare_and_advance = malformed_acknowledgement
        with self.assertRaisesRegex(TrustProviderUnavailable, "commit acknowledgement"):
            self.inspect()
        self.assertGreater(self.provider.snapshot.state_generation, generation_before)
        self.assertEqual(self.provider.commit_count, 1)

    def test_provider_raised_rejection_after_commit_is_unknown_outcome(self):
        original = self.provider.compare_and_advance
        generation_before = self.provider.snapshot.state_generation

        def raise_rejection_after_commit(**kwargs):
            original(**kwargs)
            raise TrustStateRejected("synthetic adapter rejection after durable commit")

        self.provider.compare_and_advance = raise_rejection_after_commit
        with self.assertRaisesRegex(TrustProviderUnavailable, "transaction outcome is unknown"):
            self.inspect()

        # A provider exception is not an authenticated transaction result.
        # The synthetic backend already advanced before raising this local type.
        self.assertGreater(self.provider.snapshot.state_generation, generation_before)
        self.assertEqual(self.provider.commit_count, 1)

    def test_provider_raised_rejection_before_commit_is_also_unknown_outcome(self):
        generation_before = self.provider.snapshot.state_generation

        def raise_rejection_without_commit(**kwargs):
            self.provider.commit_count += 1
            raise TrustStateRejected("synthetic provider exception before commit")

        self.provider.compare_and_advance = raise_rejection_without_commit
        with self.assertRaisesRegex(TrustProviderUnavailable, "transaction outcome is unknown"):
            self.inspect()

        # Even a pre-commit-looking provider exception is not a protocol result.
        # The caller cannot prove from the exception alone whether persistence occurred.
        self.assertEqual(self.provider.snapshot.state_generation, generation_before)
        self.assertEqual(self.provider.commit_count, 1)

    def test_provider_commit_must_bind_exact_policy_digest(self):
        original = self.provider.compare_and_advance

        def wrong_digest(**kwargs):
            commit = original(**kwargs)
            return replace(commit, policy_envelope_sha256="f" * 64)

        self.provider.compare_and_advance = wrong_digest
        with self.assertRaisesRegex(TrustProviderUnavailable, "commit acknowledgement"):
            self.inspect()

    def test_provider_snapshot_override_is_rejected_at_application_boundary(self):
        # The deployment provider, not the request caller, must be the sole
        # source of the snapshot used for policy, clock and CAS verification.
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            self.inspect(provider_snapshot=self.snapshot)

    def test_each_inspection_reads_exactly_one_snapshot_from_provider(self):
        result = self.inspect()
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(self.provider.read_count, 1)
        self.assertEqual(self.provider.commit_count, 1)


    def test_public_provider_entrypoint_does_not_accept_caller_provider(self):
        self.assertNotIn(
            "provider",
            inspect.signature(inspect_receipt_with_deployment_trust_provider).parameters,
        )


    def test_public_provider_facade_fails_closed_without_out_of_band_provider(self):
        with patch(
            "origen.deployment_trust_provider_bootstrap._load_deployment_trust_provider",
            return_value=None,
        ):
            with self.assertRaisesRegex(
                TrustProviderUnavailable,
                "not out-of-band provisioned",
            ):
                inspect_receipt_with_deployment_trust_provider(
                    self.receipt_bytes,
                    self.policy_bytes,
                )

    def test_public_provider_facade_uses_only_deployment_bootstrap(self):
        with patch(
            "origen.deployment_trust_provider_bootstrap._load_deployment_trust_provider",
            return_value=self.provider,
        ):
            result = inspect_receipt_with_deployment_trust_provider(
                self.receipt_bytes,
                self.policy_bytes,
            )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(self.provider.read_count, 1)
        self.assertEqual(self.provider.commit_count, 1)

    def test_public_provider_facade_rejects_caller_provider_keyword(self):
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            inspect_receipt_with_deployment_trust_provider(
                self.receipt_bytes,
                self.policy_bytes,
                provider=self.provider,
            )


    def test_public_provider_facade_fails_closed_on_bootstrap_store_outage(self):
        with patch(
            "origen.deployment_trust_provider_bootstrap._load_deployment_trust_provider",
            side_effect=OSError("synthetic bootstrap store outage"),
        ):
            with self.assertRaisesRegex(
                TrustProviderUnavailable,
                "bootstrap could not be loaded",
            ):
                inspect_receipt_with_deployment_trust_provider(
                    self.receipt_bytes,
                    self.policy_bytes,
                )


    def test_public_receipt_only_facade_cannot_advance_external_ledger_watermark(self):
        # Ledger/witness state may advance only after the complete physical
        # custody + RFC3161 + transparency-ledger + witness composition has
        # verified the exact evidence bytes. A receipt-only API must not accept
        # a caller-created watermark advance.
        self.assertNotIn(
            "external_evidence_advance",
            inspect.signature(
                inspect_receipt_with_deployment_trust_provider
            ).parameters,
        )
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            inspect_receipt_with_deployment_trust_provider(
                self.receipt_bytes,
                self.policy_bytes,
                external_evidence_advance=object(),
            )




    def test_operation_id_is_deterministic_and_binds_exact_policy_and_receipt_bytes(self):
        first = _deployment_trust_operation_id_sha256(
            self.policy_bytes, self.receipt_bytes, None
        )
        repeated = _deployment_trust_operation_id_sha256(
            self.policy_bytes, self.receipt_bytes, None
        )
        changed_receipt = _deployment_trust_operation_id_sha256(
            self.policy_bytes, self.receipt_bytes + b"\\x00", None
        )
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, changed_receipt)
        self.assertEqual(len(first), 64)

    def test_operation_id_binds_nested_custody_signature_bytes(self):
        raw_receipt = b"receipt"
        raw_policy = b"policy"
        artifact = b"artifact"
        signature = b"signature"
        values = {
            "policy_domain": CLASSIC_POLICY_DOMAIN,
            "state_backend_id": "synthetic-cas-store",
            "log_id": "synthetic-log",
            "log_key_id": "synthetic-log-key",
            "log_public_key_sha256": "a" * 64,
            "old_tree_size": 1,
            "old_root_sha256": "b" * 64,
            "old_checkpoint_sha256": "c" * 64,
            "new_tree_size": 2,
            "new_root_sha256": "d" * 64,
            "new_checkpoint_sha256": "e" * 64,
            "registry_id": "synthetic-registry",
            "registry_root_key_id": "synthetic-registry-root",
            "registry_root_public_key_sha256": "f" * 64,
            "registry_sequence": 2,
            "registry_sha256": "1" * 64,
            "raw_manifest_bytes": b"manifest",
            "raw_ledger_entry_bytes": b"ledger",
            "raw_inclusion_proof_bytes": b"inclusion",
            "raw_old_checkpoint_bytes": b"old-checkpoint",
            "raw_new_checkpoint_bytes": b"new-checkpoint",
            "raw_consistency_proof_bytes": b"consistency",
            "raw_registry_bytes": b"registry",
            "raw_witness_statement_bytes": (b"witness-1", b"witness-2"),
            "receipt_sha256": hashlib.sha256(raw_receipt).hexdigest(),
            "policy_envelope_sha256": hashlib.sha256(raw_policy).hexdigest(),
            "raw_receipt_bytes": raw_receipt,
            "raw_policy_envelope_bytes": raw_policy,
            "raw_custody_record_bytes": b"custody-record",
            "raw_portfolio_bytes": b"portfolio",
            "raw_custody_signature_bytes": b"custody-signature",
            "custodian_key_id": "synthetic-custodian",
            "raw_timestamp_token_der": b"custody-tsa",
            "raw_policy_timestamp_token_der": b"policy-tsa",
            "raw_artifact_bytes_by_sha256": ((hashlib.sha256(artifact).hexdigest(), artifact),),
            "raw_signature_bytes_by_sha256": ((hashlib.sha256(signature).hexdigest(), signature),),
        }
        first_advance = ExternalEvidenceAdvanceV1(**values)
        changed_values = dict(values)
        changed_values["raw_custody_signature_bytes"] = b"different-custody-signature"
        second_advance = ExternalEvidenceAdvanceV1(**changed_values)
        first = _deployment_trust_operation_id_sha256(
            raw_policy, raw_receipt, first_advance
        )
        second = _deployment_trust_operation_id_sha256(
            raw_policy, raw_receipt, second_advance
        )
        self.assertNotEqual(first, second)

    def test_lost_acknowledgement_can_retry_same_operation_without_double_advance(self):
        original = self.provider.compare_and_advance
        generation_before = self.provider.snapshot.state_generation

        def commit_then_raise(**kwargs):
            original(**kwargs)
            raise OSError("synthetic acknowledgement lost after durable commit")

        self.provider.compare_and_advance = commit_then_raise
        with self.assertRaises(TrustProviderUnavailable) as raised:
            self.inspect()

        operation_id = raised.exception.operation_id_sha256
        self.assertEqual(
            operation_id,
            _deployment_trust_operation_id_sha256(
                self.policy_bytes, self.receipt_bytes, None
            ),
        )
        generation_after_first = self.provider.snapshot.state_generation
        self.assertGreater(generation_after_first, generation_before)

        self.provider.compare_and_advance = original
        result = self.inspect()
        self.assertEqual(result.operation_id_sha256, operation_id)
        self.assertTrue(result.operation_replayed)
        self.assertEqual(
            result.operation_receipt_sha256,
            hashlib.sha256(self.provider.operation_receipt_records[operation_id]).hexdigest(),
        )
        self.assertIs(result.state_outcome, TrustStateOutcome.ADVANCED)
        self.assertEqual(self.provider.snapshot.state_generation, generation_after_first)
        self.assertEqual(self.provider.commit_count, 1)

    def test_authenticated_operation_receipt_recovers_after_policy_floor_rotation(self):
        first = self.inspect()
        operation_id = first.operation_id_sha256
        generation_after_commit = self.provider.snapshot.state_generation
        original_record = self.provider.operation_receipt_records[operation_id]
        self.assertFalse(first.operation_replayed)

        # Simulate a later authorized policy-floor transition. The old policy
        # bytes are now below the live floor, but the provider retains its
        # signed durable record for the exact original operation.
        self.provider.snapshot = replace(
            self.provider.snapshot,
            state_generation=generation_after_commit + 1,
            minimum_policy_sequence=POLICY_SEQUENCE + 1,
            accepted_policy_sequence=POLICY_SEQUENCE + 1,
            accepted_policy_envelope_sha256="d" * 64,
        )
        commits_before_replay = self.provider.commit_count
        result = self.inspect()

        self.assertTrue(result.operation_replayed)
        self.assertEqual(result.operation_id_sha256, operation_id)
        self.assertEqual(result.operation_receipt_sha256, hashlib.sha256(original_record).hexdigest())
        self.assertEqual(result.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.state_generation_after, generation_after_commit)
        self.assertIs(result.state_outcome, TrustStateOutcome.ADVANCED)
        self.assertEqual(self.provider.commit_count, commits_before_replay)
        self.assertEqual(self.provider.snapshot.state_generation, generation_after_commit + 1)

    def test_invalid_signed_operation_receipt_fails_closed_without_cas_fallback(self):
        first = self.inspect()
        operation_id = first.operation_id_sha256
        record = self.provider.operation_receipt_records[operation_id]
        self.provider.operation_receipt_records[operation_id] = record[:-1] + (
            b" " if record[-1:] != b" " else b"!"
        )
        self.provider.snapshot = replace(
            self.provider.snapshot,
            state_generation=self.provider.snapshot.state_generation + 1,
            minimum_policy_sequence=POLICY_SEQUENCE + 1,
            accepted_policy_sequence=POLICY_SEQUENCE + 1,
            accepted_policy_envelope_sha256="e" * 64,
        )
        commits_before = self.provider.commit_count
        with self.assertRaisesRegex(
            TrustProviderUnavailable,
            "invalid or nonmatching signed operation receipt",
        ) as raised:
            self.inspect()
        self.assertEqual(raised.exception.operation_id_sha256, operation_id)
        self.assertEqual(self.provider.commit_count, commits_before)

    def test_provider_recomputes_operation_id_and_rejects_substituted_evidence(self):
        original = self.provider.compare_and_advance

        def substituted_operation_id(**kwargs):
            kwargs["operation_id_sha256"] = "f" * 64
            return original(**kwargs)

        self.provider.compare_and_advance = substituted_operation_id
        with self.assertRaises(TrustStateRejected):
            self.inspect()
        self.assertEqual(self.provider.snapshot.state_generation, 7)

    def test_provider_commit_must_bind_exact_operation_id(self):
        original = self.provider.compare_and_advance

        def wrong_operation_ack(**kwargs):
            commit = original(**kwargs)
            return replace(commit, operation_id_sha256="f" * 64)

        self.provider.compare_and_advance = wrong_operation_ack
        with self.assertRaisesRegex(
            TrustProviderUnavailable,
            "exact evidence operation ID",
        ) as raised:
            self.inspect()
        self.assertIsNotNone(raised.exception.operation_id_sha256)
        self.assertEqual(self.provider.snapshot.state_generation, 8)


if __name__ == "__main__":
    unittest.main()
