"""Research-only deployment trust-provider boundary with atomic anti-rollback CAS.

This module defines the application-facing contract for a separately provisioned
trust-state service. It deliberately includes no production provider or local
fallback. Test providers are synthetic and belong only in the test suite.

A provider object is a trusted composition-root dependency, not an unforgeable
Python capability. The contract cannot authenticate its own implementation.
Every successful inspection still returns BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .independent_trust_adapter import (
    ProvenanceStatus,
    _verify_independent_provenance_with_explicit_context,
)
from .physical_trust_context_v1 import PhysicalTrustContextV1
from .timestamp_nonce_challenge_v1 import TimestampNonceChallengeV1
from .trust_policy_envelope_v1 import (
    MAX_POLICY_BYTES,
    MAX_POLICY_SEQUENCE,
)
from .trust_policy_envelope_v3 import (
    VerifiedTrustPolicyV3,
    verify_signed_trust_policy_v3,
)
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)

CLASSIC_POLICY_DOMAIN = "origen.chispazo.classic.provenance"
CLOCK_SAMPLE_SCHEMA = "origen.clock-sample-attestation.v1"
MAX_CLOCK_SAMPLE_BYTES = 4096
MAX_OPERATION_RECEIPT_BYTES = 8192
OPERATION_RECEIPT_SCHEMA = "origen.deployment-trust-operation-receipt.v1"
_CLOCK_SAMPLE_UTC = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z"
)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class TrustStateOutcome(str, Enum):
    """Outcome codes for an atomic provider transaction."""

    ADVANCED = "ADVANCED"
    IDEMPOTENT = "IDEMPOTENT"
    CONFLICT = "CONFLICT"
    ROLLBACK = "ROLLBACK"
    TIME_ROLLBACK = "TIME_ROLLBACK"
    TIME_ADVANCED = "TIME_ADVANCED"
    EVIDENCE_ADVANCED = "EVIDENCE_ADVANCED"
    TIME_AND_EVIDENCE_ADVANCED = "TIME_AND_EVIDENCE_ADVANCED"
    EQUIVOCATION = "EQUIVOCATION"


@dataclass(frozen=True, slots=True)
class ExternalEvidenceWatermarkV1:
    """Last externally verified ledger checkpoint and witness registry version."""

    policy_domain: str
    state_backend_id: str
    log_id: str
    log_key_id: str
    log_public_key_sha256: str
    ledger_tree_size: int
    ledger_root_sha256: str
    ledger_checkpoint_sha256: str
    registry_id: str
    registry_root_key_id: str
    registry_root_public_key_sha256: str
    registry_sequence: int
    registry_sha256: str


@dataclass(frozen=True, slots=True)
class ExternalEvidenceAdvanceV1:
    """One complete exact-byte evidence bundle proposed for one provider CAS."""

    policy_domain: str
    state_backend_id: str
    log_id: str
    log_key_id: str
    log_public_key_sha256: str
    old_tree_size: int
    old_root_sha256: str
    old_checkpoint_sha256: str
    new_tree_size: int
    new_root_sha256: str
    new_checkpoint_sha256: str
    registry_id: str
    registry_root_key_id: str
    registry_root_public_key_sha256: str
    registry_sequence: int
    registry_sha256: str
    raw_manifest_bytes: bytes
    raw_ledger_entry_bytes: bytes
    raw_inclusion_proof_bytes: bytes
    raw_old_checkpoint_bytes: bytes
    raw_new_checkpoint_bytes: bytes
    raw_consistency_proof_bytes: bytes
    raw_registry_bytes: bytes
    raw_witness_statement_bytes: tuple[bytes, ...]
    receipt_sha256: str
    policy_envelope_sha256: str
    raw_receipt_bytes: bytes
    raw_policy_envelope_bytes: bytes
    raw_custody_record_bytes: bytes
    raw_portfolio_bytes: bytes
    raw_custody_signature_bytes: bytes
    custodian_key_id: str
    raw_timestamp_token_der: bytes
    raw_policy_timestamp_token_der: bytes
    raw_artifact_bytes_by_sha256: tuple[tuple[str, bytes], ...]
    raw_signature_bytes_by_sha256: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True, slots=True)
class DeploymentTrustSnapshot:
    """One immutable snapshot returned by the deployment trust-state provider.

    All fields are metadata from the provider boundary. This dataclass is not
    proof that the provider is institutionally trusted or correctly deployed.
    """

    policy_domain: str
    root_public_key_bytes: bytes
    root_key_id: str
    root_generation: int
    minimum_policy_sequence: int
    state_generation: int
    accepted_policy_sequence: int
    accepted_policy_envelope_sha256: str | None
    trusted_time_latest_utc: datetime | None
    trusted_time_utc: datetime
    clock_uncertainty_ms: int
    maximum_clock_uncertainty_ms: int
    clock_source_id: str
    clock_sample_key_id: str
    clock_sample_public_key_bytes: bytes
    clock_sample_envelope_bytes: bytes
    clock_sample_id: str
    clock_sample_valid_until_utc: datetime
    maximum_clock_sample_age_ms: int
    state_backend_id: str
    provisioning_record_sha256: str
    physical_trust_context_generation: int | None = None
    physical_trust_context_sha256: str | None = None
    accepted_external_evidence_watermark: ExternalEvidenceWatermarkV1 | None = None
    operation_receipt_key_id: str | None = None
    operation_receipt_public_key_bytes: bytes | None = None


@dataclass(frozen=True, slots=True)
class DeploymentTrustCommit:
    """Result of a linearizable compare-and-advance operation."""

    outcome: TrustStateOutcome
    state_generation: int
    policy_sequence: int
    policy_envelope_sha256: str
    trusted_time_latest_utc: datetime
    accepted_external_evidence_watermark_sha256: str | None = None
    receipt_sha256: str | None = None
    operation_id_sha256: str | None = None
    operation_replayed: bool = False
    operation_receipt_sha256: str | None = None


class DeploymentTrustProvider(Protocol):
    """Trusted composition-root dependency; no implementation ships here.

    read_snapshot must return one internally consistent snapshot of root pin,
    sequence state, generation, and authenticated clock metadata.

    compare_and_advance must be linearizable. It must compare the exact state
    generation and expected trust-configuration digest observed by read_snapshot
    and atomically enforce monotonic sequence/digest/time semantics for every
    inspection. It must recompute the configuration digest from authoritative
    provider state; it must not trust the caller's digest as a replacement for
    that comparison. It must also re-verify the exact signed clock-sample bytes
    against its authoritative provisioned clock key and current source sample
    inside the same transaction. Candidate earliest time is derived from the
    provider's authenticated signed clock sample (sampled_at_utc minus its
    uncertainty) and must not precede the stored trusted_time_latest_utc. No
    caller timestamp or uncertainty is a source of trusted time. The expected clock-sample digest must be
    recomputed against the authoritative current source sample inside the
    transaction; reject a changed sample or an expired sample lease. For a
    higher sequence, persist the candidate sequence, digest, and latest time. For the same sequence and digest, persist
    a later disjoint time watermark with one generation increment and return
    TIME_ADVANCED; if the watermark is unchanged, return IDEMPOTENT without a
    generation increment. It must also compare the exact persisted ledger / witness watermark digest and
    atomically enforce checkpoint continuity, registry sequence/digest monotonicity,
    and identity continuity with the current physical trust context. Before advancing,
    it must independently re-verify the complete exact-byte evidence envelope:
    receipt and signed policy bytes, custody record, portfolio, detached custody
    signature and custodian identity, both RFC 3161 token DER blobs, artifact and
    signature byte maps, manifest, ledger entry, inclusion proof, old/new signed
    checkpoints, consistency proof, signed witness registry and every witness
    statement. Verification must use provider-owned roots/pins, trusted time,
    revocation state and quorum policy. It must not trust caller-computed digests
    or the application's prior verification as a substitute. This verification
    and the compare-and-advance must be serialized so no trust configuration or
    accepted checkpoint can change between them. It must never silently reset or restore any value. A missing
    external-evidence genesis watermark is a hard failure; it must not be initialized
    from caller-supplied evidence.
    """

    def read_snapshot(self, *, policy_domain: str) -> DeploymentTrustSnapshot:
        ...

    def read_physical_trust_context(
        self, *, policy_domain: str
    ) -> PhysicalTrustContextV1:
        """Return the context bound by the same snapshot's digest and generation.

        The context generation and exact canonical context digest must match
        physical_trust_context_generation / physical_trust_context_sha256 in
        read_snapshot. compare_and_advance must recompute that binding from
        authoritative state inside the same transaction as the policy/time CAS.
        """
        ...

    def read_timestamp_nonce_challenge(
        self,
        *,
        policy_domain: str,
        expected_state_backend_id: str,
        expected_state_generation: int,
        expected_root_generation: int,
        expected_physical_trust_context_generation: int,
        expected_physical_trust_context_sha256: str,
    ) -> TimestampNonceChallengeV1:
        """Return a provider-issued, one-use challenge bound to this snapshot.

        The provider must create unpredictable RFC 3161 nonces, persist the
        pending challenge, and reject stale, expired, or already-consumed
        challenges. The exact policy domain and state_backend_id are part of the
        challenge digest and must match the authoritative provider instance.
        This prevents accidental cross-domain or cross-backend challenge reuse.
        The challenge is not trusted merely because this interface returns it;
        the deployment implementation and its state remain external.
        """
        ...

    def read_operation_receipt(
        self,
        *,
        policy_domain: str,
        expected_state_backend_id: str,
        operation_id_sha256: str,
    ) -> bytes | None:
        """Read an exact provider-signed durable operation receipt without mutation.

        The lookup is by the stable operation ID and must occur before applying
        the current policy sequence floor. A returned record binds the exact
        policy/receipt digests, CLASSIC domain, backend, original state
        transition, and provider key ID. It must be signed by the provider's
        separately provisioned operation-receipt key exposed in the same
        snapshot. The query must not consume a timestamp nonce or change state.
        Return None only when no durable record exists. Never synthesize a
        receipt from current state or caller assertions.
        """
        ...

    def compare_and_advance(
        self,
        *,
        expected_state_generation: int,
        expected_trust_configuration_sha256: str,
        expected_clock_sample_sha256: str,
        operation_id_sha256: str,
        policy_domain: str,
        root_key_id: str,
        root_generation: int,
        policy_sequence: int,
        policy_envelope_sha256: str,
        raw_policy_envelope_bytes: bytes,
        raw_receipt_bytes: bytes,
        expected_external_evidence_watermark_sha256: str,
        external_evidence_advance: ExternalEvidenceAdvanceV1 | None = None,
        timestamp_nonce_challenge_id: str | None = None,
        timestamp_nonce_challenge_sha256: str | None = None,
    ) -> DeploymentTrustCommit:
        """Atomically re-verify exact policy/receipt bytes and advance trust state.

        The provider must independently parse and verify raw_policy_envelope_bytes
        against its authoritative root, policy domain, key ID, durable sequence
        floor and its own authenticated current clock. It must recompute the policy
        digest and sequence, then verify raw_receipt_bytes against that policy and
        the complete signed-time uncertainty interval. These exact byte inputs are
        mandatory even when external_evidence_advance is absent. If a full evidence
        advance is supplied, its embedded policy and receipt bytes must equal these
        exact arguments. The caller's digests and sequence are assertions only.
        A successful commit must return receipt_sha256 computed from raw_receipt_bytes.

        operation_id_sha256 is a deterministic, domain-separated identity of the
        exact stable evidence request: policy domain, original policy bytes,
        original receipt bytes, and every field/byte of the complete external
        evidence advance when present. It deliberately excludes transient snapshot
        generation, clock sample and one-use nonce challenge so the same evidence
        can be retried after an ambiguous acknowledgement. The provider must
        recompute this identity from the exact bytes, persist its operation receipt
        atomically with the trust-state transition, and check the operation ledger
        before stale-snapshot rejection. A repeated ID with the same exact evidence
        returns the prior result as IDEMPOTENT without applying policy, evidence or
        nonce consumption twice. A repeated ID with different evidence is
        EQUIVOCATION. The ID is not an authentication credential.

        The API intentionally has no accepted_at_utc or clock_uncertainty_ms inputs.
        The provider derives both from its own currently authenticated signed clock
        sample and rechecks that sample, its lease and state generation in this
        same linearizable transaction.

        When challenge fields are present, the backend must look up its own
        pending challenge, recompute the exact digest, verify the same policy
        domain, backend identity, state generation and trust configuration,
        and consume both nonce values in this same linearizable transaction.
        It must reject cross-backend/domain challenge use and challenge or
        nonce reuse. It must compare expected_external_evidence_watermark_sha256
        with authoritative state and, when an advance is supplied, atomically
        require the exact old checkpoint to equal the accepted checkpoint,
        the new checkpoint to advance monotonically, and the registry sequence /
        digest to avoid rollback or same-sequence equivocation. The CAS must
        return the resulting accepted watermark digest in the commit.
        """
        ...


@dataclass(frozen=True, slots=True)
class DeploymentTrustInspection:
    """Audit output only. It is never an eligibility or authentication token."""

    receipt_sha256: str
    policy_envelope_sha256: str
    policy_domain: str
    policy_sequence: int
    root_key_id: str
    root_generation: int
    provisioning_record_sha256: str
    trust_configuration_sha256: str
    clock_source_id: str
    clock_sample_sha256: str
    clock_sample_valid_until_utc: datetime
    state_backend_id: str
    time_window_start_utc: datetime
    time_window_end_utc: datetime
    state_generation_before: int
    state_generation_after: int
    state_outcome: TrustStateOutcome
    provenance_status: ProvenanceStatus
    timestamp_nonce_challenge_id: str | None = None
    timestamp_nonce_challenge_sha256: str | None = None
    operation_id_sha256: str | None = None


class TrustProviderUnavailable(RuntimeError):
    """The external provider could not supply or commit trusted state."""

    def __init__(self, message: str, *, operation_id_sha256: str | None = None):
        super().__init__(message)
        self.operation_id_sha256 = operation_id_sha256


class TrustStateRejected(RuntimeError):
    """The provider state was stale, rolled back, equivocated, or conflicted."""


def _require_identifier(value: object, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _require_sha256(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _accepted_external_evidence_watermark_sha256(
    value: ExternalEvidenceWatermarkV1 | None,
) -> str:
    """Hash the exact accepted ledger/witness state, including the empty state."""
    if value is None:
        payload = {
            "schema": "origen.deployment-external-evidence-watermark.v1",
            "state": "EMPTY",
        }
    else:
        copied = _external_evidence_watermark_copy(value)
        payload = {
            "schema": "origen.deployment-external-evidence-watermark.v1",
            "state": "ACCEPTED",
            "policy_domain": copied.policy_domain,
            "state_backend_id": copied.state_backend_id,
            "log_id": copied.log_id,
            "log_key_id": copied.log_key_id,
            "log_public_key_sha256": copied.log_public_key_sha256,
            "ledger_tree_size": copied.ledger_tree_size,
            "ledger_root_sha256": copied.ledger_root_sha256,
            "ledger_checkpoint_sha256": copied.ledger_checkpoint_sha256,
            "registry_id": copied.registry_id,
            "registry_root_key_id": copied.registry_root_key_id,
            "registry_root_public_key_sha256": copied.registry_root_public_key_sha256,
            "registry_sequence": copied.registry_sequence,
            "registry_sha256": copied.registry_sha256,
        }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(b"ORIGEN_EXTERNAL_EVIDENCE_WATERMARK_V1\x00" + canonical).hexdigest()


def _external_evidence_watermark_copy(value: object) -> ExternalEvidenceWatermarkV1 | None:
    if value is None:
        return None
    if type(value) is not ExternalEvidenceWatermarkV1:
        raise TypeError("provider accepted external evidence watermark has an unexpected type")
    copied = ExternalEvidenceWatermarkV1(
        policy_domain=value.policy_domain,
        state_backend_id=value.state_backend_id,
        log_id=value.log_id,
        log_key_id=value.log_key_id,
        log_public_key_sha256=value.log_public_key_sha256,
        ledger_tree_size=value.ledger_tree_size,
        ledger_root_sha256=value.ledger_root_sha256,
        ledger_checkpoint_sha256=value.ledger_checkpoint_sha256,
        registry_id=value.registry_id,
        registry_root_key_id=value.registry_root_key_id,
        registry_root_public_key_sha256=value.registry_root_public_key_sha256,
        registry_sequence=value.registry_sequence,
        registry_sha256=value.registry_sha256,
    )
    if copied.policy_domain != CLASSIC_POLICY_DOMAIN:
        raise ValueError("external evidence watermark is not scoped to the fixed CLASSIC domain")
    for field, actual in (
        ("state_backend_id", copied.state_backend_id),
        ("log_id", copied.log_id),
        ("log_key_id", copied.log_key_id),
        ("registry_id", copied.registry_id),
        ("registry_root_key_id", copied.registry_root_key_id),
    ):
        _require_identifier(actual, field)
    for field, actual in (
        ("ledger_root_sha256", copied.ledger_root_sha256),
        ("ledger_checkpoint_sha256", copied.ledger_checkpoint_sha256),
        ("log_public_key_sha256", copied.log_public_key_sha256),
        ("registry_root_public_key_sha256", copied.registry_root_public_key_sha256),
        ("registry_sha256", copied.registry_sha256),
    ):
        _require_sha256(actual, field)
    if type(copied.ledger_tree_size) is not int or not 1 <= copied.ledger_tree_size <= 2**63 - 1:
        raise ValueError("ledger_tree_size must be an exact positive signed-64-bit integer")
    if type(copied.registry_sequence) is not int or not 1 <= copied.registry_sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError("registry_sequence must be an exact positive bounded integer")
    return copied


def _external_evidence_advance_copy(value: object) -> ExternalEvidenceAdvanceV1:
    if type(value) is not ExternalEvidenceAdvanceV1:
        raise TypeError("external evidence advance must be an exact ExternalEvidenceAdvanceV1")
    copied = ExternalEvidenceAdvanceV1(
        policy_domain=value.policy_domain,
        state_backend_id=value.state_backend_id,
        log_id=value.log_id,
        log_key_id=value.log_key_id,
        log_public_key_sha256=value.log_public_key_sha256,
        old_tree_size=value.old_tree_size,
        old_root_sha256=value.old_root_sha256,
        old_checkpoint_sha256=value.old_checkpoint_sha256,
        new_tree_size=value.new_tree_size,
        new_root_sha256=value.new_root_sha256,
        new_checkpoint_sha256=value.new_checkpoint_sha256,
        registry_id=value.registry_id,
        registry_root_key_id=value.registry_root_key_id,
        registry_root_public_key_sha256=value.registry_root_public_key_sha256,
        registry_sequence=value.registry_sequence,
        registry_sha256=value.registry_sha256,
        raw_manifest_bytes=value.raw_manifest_bytes,
        raw_ledger_entry_bytes=value.raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes=value.raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes=value.raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes=value.raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes=value.raw_consistency_proof_bytes,
        raw_registry_bytes=value.raw_registry_bytes,
        raw_witness_statement_bytes=value.raw_witness_statement_bytes,
        receipt_sha256=value.receipt_sha256,
        policy_envelope_sha256=value.policy_envelope_sha256,
        raw_receipt_bytes=value.raw_receipt_bytes,
        raw_policy_envelope_bytes=value.raw_policy_envelope_bytes,
        raw_custody_record_bytes=value.raw_custody_record_bytes,
        raw_portfolio_bytes=value.raw_portfolio_bytes,
        raw_custody_signature_bytes=value.raw_custody_signature_bytes,
        custodian_key_id=value.custodian_key_id,
        raw_timestamp_token_der=value.raw_timestamp_token_der,
        raw_policy_timestamp_token_der=value.raw_policy_timestamp_token_der,
        raw_artifact_bytes_by_sha256=value.raw_artifact_bytes_by_sha256,
        raw_signature_bytes_by_sha256=value.raw_signature_bytes_by_sha256,
    )
    if copied.policy_domain != CLASSIC_POLICY_DOMAIN:
        raise ValueError("external evidence advance is not scoped to the fixed CLASSIC domain")
    for field, actual in (
        ("state_backend_id", copied.state_backend_id),
        ("log_id", copied.log_id),
        ("log_key_id", copied.log_key_id),
        ("registry_id", copied.registry_id),
        ("registry_root_key_id", copied.registry_root_key_id),
        ("custodian_key_id", copied.custodian_key_id),
    ):
        _require_identifier(actual, field)
    for field, actual in (
        ("old_root_sha256", copied.old_root_sha256),
        ("old_checkpoint_sha256", copied.old_checkpoint_sha256),
        ("new_root_sha256", copied.new_root_sha256),
        ("new_checkpoint_sha256", copied.new_checkpoint_sha256),
        ("log_public_key_sha256", copied.log_public_key_sha256),
        ("registry_root_public_key_sha256", copied.registry_root_public_key_sha256),
        ("registry_sha256", copied.registry_sha256),
        ("receipt_sha256", copied.receipt_sha256),
        ("policy_envelope_sha256", copied.policy_envelope_sha256),
    ):
        _require_sha256(actual, field)
    for field, actual in (
        ("old_tree_size", copied.old_tree_size),
        ("new_tree_size", copied.new_tree_size),
    ):
        if type(actual) is not int or not 1 <= actual <= 2**63 - 1:
            raise ValueError(f"{field} must be an exact positive signed-64-bit integer")
    if copied.new_tree_size <= copied.old_tree_size:
        raise ValueError("new ledger checkpoint tree size must exceed the old tree size")
    if type(copied.registry_sequence) is not int or not 1 <= copied.registry_sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError("registry_sequence must be an exact positive bounded integer")

    raw_byte_fields = (
        ("raw_manifest_bytes", copied.raw_manifest_bytes),
        ("raw_ledger_entry_bytes", copied.raw_ledger_entry_bytes),
        ("raw_inclusion_proof_bytes", copied.raw_inclusion_proof_bytes),
        ("raw_old_checkpoint_bytes", copied.raw_old_checkpoint_bytes),
        ("raw_new_checkpoint_bytes", copied.raw_new_checkpoint_bytes),
        ("raw_consistency_proof_bytes", copied.raw_consistency_proof_bytes),
        ("raw_registry_bytes", copied.raw_registry_bytes),
        ("raw_receipt_bytes", copied.raw_receipt_bytes),
        ("raw_policy_envelope_bytes", copied.raw_policy_envelope_bytes),
        ("raw_custody_record_bytes", copied.raw_custody_record_bytes),
        ("raw_portfolio_bytes", copied.raw_portfolio_bytes),
        ("raw_custody_signature_bytes", copied.raw_custody_signature_bytes),
        ("raw_timestamp_token_der", copied.raw_timestamp_token_der),
        ("raw_policy_timestamp_token_der", copied.raw_policy_timestamp_token_der),
    )
    total_bytes = 0
    for field, actual in raw_byte_fields:
        if type(actual) is not bytes or not actual:
            raise ValueError(f"{field} must be non-empty exact bytes")
        total_bytes += len(actual)

    if type(copied.raw_witness_statement_bytes) is not tuple or not 2 <= len(copied.raw_witness_statement_bytes) <= 128:
        raise ValueError("raw_witness_statement_bytes must be an exact bounded tuple of 2..128 statements")
    for statement in copied.raw_witness_statement_bytes:
        if type(statement) is not bytes or not statement:
            raise ValueError("each raw witness statement must be non-empty exact bytes")
        total_bytes += len(statement)

    for field, pairs in (
        ("raw_artifact_bytes_by_sha256", copied.raw_artifact_bytes_by_sha256),
        ("raw_signature_bytes_by_sha256", copied.raw_signature_bytes_by_sha256),
    ):
        if type(pairs) is not tuple or not 1 <= len(pairs) <= 256:
            raise ValueError(f"{field} must be an exact bounded tuple of 1..256 digest/byte pairs")
        previous_digest = None
        for pair in pairs:
            if type(pair) is not tuple or len(pair) != 2:
                raise ValueError(f"{field} entries must be exact two-item tuples")
            digest, raw = pair
            _require_sha256(digest, f"{field} digest")
            if previous_digest is not None and digest <= previous_digest:
                raise ValueError(f"{field} must be sorted by unique digest")
            if type(raw) is not bytes or not raw:
                raise ValueError(f"{field} values must be non-empty exact bytes")
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError(f"{field} digest does not bind the exact bytes")
            previous_digest = digest
            total_bytes += len(raw)

    if total_bytes > 8 * 1024 * 1024:
        raise ValueError("external evidence advance exceeds the aggregate byte limit")
    exact_digests = (
        ("receipt_sha256", copied.receipt_sha256, copied.raw_receipt_bytes),
        ("policy_envelope_sha256", copied.policy_envelope_sha256, copied.raw_policy_envelope_bytes),
        ("old_checkpoint_sha256", copied.old_checkpoint_sha256, copied.raw_old_checkpoint_bytes),
        ("new_checkpoint_sha256", copied.new_checkpoint_sha256, copied.raw_new_checkpoint_bytes),
        ("registry_sha256", copied.registry_sha256, copied.raw_registry_bytes),
    )
    for field, expected, raw in exact_digests:
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"{field} does not bind the exact external evidence bytes")
    return copied


def _validated_external_evidence_watermark(
    snapshot: DeploymentTrustSnapshot,
    expected_sha256: str,
    advance: ExternalEvidenceAdvanceV1 | None,
    *,
    allow_replay_candidate: bool = False,
) -> ExternalEvidenceWatermarkV1 | None:
    """Validate one candidate against the exact accepted watermark in a snapshot.

    A real provider must repeat this logic against authoritative state inside
    its linearizable CAS transaction; this application-side check is not a
    substitute for durable independent storage.
    """
    if type(allow_replay_candidate) is not bool:
        raise TypeError("allow_replay_candidate must be an exact bool")
    _require_sha256(expected_sha256, "expected_external_evidence_watermark_sha256")
    current = _external_evidence_watermark_copy(snapshot.accepted_external_evidence_watermark)
    if current is not None and (
        current.policy_domain != snapshot.policy_domain
        or current.state_backend_id != snapshot.state_backend_id
    ):
        raise TrustStateRejected(
            "persisted external evidence watermark is not bound to the exact policy domain and state backend"
        )
    if expected_sha256 != _accepted_external_evidence_watermark_sha256(current):
        raise TrustStateRejected("external evidence watermark changed since the provider snapshot")
    if advance is None:
        return current
    candidate = _external_evidence_advance_copy(advance)
    if current is None:
        raise TrustStateRejected("external ledger/witness genesis watermark is not independently provisioned")
    if candidate.policy_domain != snapshot.policy_domain or candidate.state_backend_id != snapshot.state_backend_id:
        raise TrustStateRejected("external evidence advance is not bound to the exact policy domain and state backend")
    if (
        candidate.log_id != current.log_id
        or candidate.log_key_id != current.log_key_id
        or candidate.log_public_key_sha256 != current.log_public_key_sha256
        or candidate.registry_id != current.registry_id
        or candidate.registry_root_key_id != current.registry_root_key_id
        or candidate.registry_root_public_key_sha256 != current.registry_root_public_key_sha256
    ):
        raise TrustStateRejected("external ledger or witness-registry identity changed without an authorized transition")

    # A retry after a lost CAS acknowledgement may observe the exact new
    # watermark already persisted. This local equality is only a replay
    # candidate; the provider must confirm the matching durable operation ID
    # before returning IDEMPOTENT. Without that operation record, its CAS must
    # reject the stale old checkpoint.
    if allow_replay_candidate and (
        candidate.new_tree_size == current.ledger_tree_size
        and candidate.new_root_sha256 == current.ledger_root_sha256
        and candidate.new_checkpoint_sha256 == current.ledger_checkpoint_sha256
        and candidate.registry_sequence == current.registry_sequence
        and candidate.registry_sha256 == current.registry_sha256
    ):
        return current

    if candidate.new_tree_size < current.ledger_tree_size:
        raise TrustStateRejected("ledger checkpoint tree-size rollback detected")
    if candidate.new_tree_size == current.ledger_tree_size and (
        candidate.new_root_sha256 != current.ledger_root_sha256
        or candidate.new_checkpoint_sha256 != current.ledger_checkpoint_sha256
    ):
        raise TrustStateRejected("same-size ledger checkpoint equivocation detected")
    if (
        candidate.old_tree_size != current.ledger_tree_size
        or candidate.old_root_sha256 != current.ledger_root_sha256
        or candidate.old_checkpoint_sha256 != current.ledger_checkpoint_sha256
    ):
        raise TrustStateRejected("new ledger checkpoint does not extend the exact persisted checkpoint")
    if candidate.new_tree_size == current.ledger_tree_size:
        raise TrustStateRejected(
            "external evidence advance must strictly increase the persisted ledger checkpoint tree size"
        )

    if candidate.registry_sequence < current.registry_sequence:
        raise TrustStateRejected("witness registry sequence rollback detected")
    if (
        candidate.registry_sequence == current.registry_sequence
        and candidate.registry_sha256 != current.registry_sha256
    ):
        raise TrustStateRejected("same-sequence witness registry digest equivocation detected")

    return ExternalEvidenceWatermarkV1(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id=snapshot.state_backend_id,
        log_id=candidate.log_id,
        log_key_id=candidate.log_key_id,
        log_public_key_sha256=candidate.log_public_key_sha256,
        ledger_tree_size=candidate.new_tree_size,
        ledger_root_sha256=candidate.new_root_sha256,
        ledger_checkpoint_sha256=candidate.new_checkpoint_sha256,
        registry_id=candidate.registry_id,
        registry_root_key_id=candidate.registry_root_key_id,
        registry_root_public_key_sha256=candidate.registry_root_public_key_sha256,
        registry_sequence=candidate.registry_sequence,
        registry_sha256=candidate.registry_sha256,
    )


def _hash_operation_component(digest, value: object) -> None:
    """Hash one exact typed component with unambiguous length framing."""
    if value is None:
        digest.update(b"N")
        return
    if type(value) is bytes:
        digest.update(b"B")
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
        return
    if type(value) is str:
        raw = value.encode("utf-8")
        digest.update(b"S")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
        return
    if type(value) is int:
        raw = str(value).encode("ascii")
        digest.update(b"I")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
        return
    if type(value) is tuple:
        digest.update(b"T")
        digest.update(len(value).to_bytes(8, "big"))
        for item in value:
            _hash_operation_component(digest, item)
        return
    raise TypeError("operation identity contains an unsupported component type")


def _deployment_trust_operation_id_sha256(
    raw_policy_envelope_bytes: bytes,
    raw_receipt_bytes: bytes,
    external_evidence_advance: ExternalEvidenceAdvanceV1 | None,
) -> str:
    """Stable identity for exact evidence, independent of transient provider state."""
    if type(raw_policy_envelope_bytes) is not bytes or not raw_policy_envelope_bytes:
        raise ValueError("operation identity requires exact non-empty policy bytes")
    if type(raw_receipt_bytes) is not bytes or not raw_receipt_bytes:
        raise ValueError("operation identity requires exact non-empty receipt bytes")
    if external_evidence_advance is not None and type(external_evidence_advance) is not ExternalEvidenceAdvanceV1:
        raise TypeError("operation identity requires an exact external evidence advance")
    digest = hashlib.sha256()
    digest.update(b"ORIGEN_DEPLOYMENT_TRUST_OPERATION_V1\x00")
    _hash_operation_component(digest, CLASSIC_POLICY_DOMAIN)
    _hash_operation_component(digest, raw_policy_envelope_bytes)
    _hash_operation_component(digest, raw_receipt_bytes)
    if external_evidence_advance is None:
        _hash_operation_component(digest, None)
    else:
        digest.update(b"A")
        for item in fields(ExternalEvidenceAdvanceV1):
            _hash_operation_component(digest, item.name)
            _hash_operation_component(digest, getattr(external_evidence_advance, item.name))
    return digest.hexdigest()


def _operation_receipt_pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("operation receipt contains a duplicate JSON key")
        result[key] = value
    return result


def _operation_receipt_reject_constant(value: str):
    raise ValueError("operation receipt contains a non-finite JSON number")


def _verify_deployment_trust_operation_receipt(
    raw: bytes,
    *,
    snapshot: DeploymentTrustSnapshot,
    expected_operation_id_sha256: str,
    raw_policy_envelope_bytes: bytes,
    raw_receipt_bytes: bytes,
) -> dict[str, object]:
    """Verify a provider-signed durable record for one exact evidence operation."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_OPERATION_RECEIPT_BYTES:
        raise ValueError("operation receipt must be exact bytes within size limit")
    if (
        type(snapshot.operation_receipt_key_id) is not str
        or type(snapshot.operation_receipt_public_key_bytes) is not bytes
        or len(snapshot.operation_receipt_public_key_bytes) != 32
    ):
        raise ValueError("provider operation-receipt verification key is not provisioned")

    try:
        document = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_operation_receipt_pairs_no_duplicates,
            parse_constant=_operation_receipt_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("operation receipt must be valid ASCII JSON") from exc
    if type(document) is not dict:
        raise ValueError("operation receipt must be a JSON object")
    fields_expected = {
        "schema", "policy_domain", "state_backend_id", "operation_id_sha256",
        "policy_envelope_sha256", "receipt_sha256", "policy_sequence",
        "state_generation_before", "state_generation_after", "outcome",
        "accepted_external_evidence_watermark_sha256", "trusted_time_latest_utc",
        "root_key_id", "root_generation", "provisioning_record_sha256",
        "trust_configuration_sha256", "clock_source_id", "clock_sample_sha256",
        "clock_sample_valid_until_utc", "time_window_start_utc",
        "time_window_end_utc", "provider_key_id", "signature_b64",
    }
    if set(document) != fields_expected:
        raise ValueError("operation receipt fields mismatch")
    canonical_document = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    if raw != canonical_document:
        raise ValueError("operation receipt is not canonical JSON")
    if document["schema"] != OPERATION_RECEIPT_SCHEMA:
        raise ValueError("unsupported operation receipt schema")
    if document["policy_domain"] != CLASSIC_POLICY_DOMAIN:
        raise ValueError("operation receipt is not scoped to the fixed CLASSIC domain")
    if document["state_backend_id"] != snapshot.state_backend_id:
        raise ValueError("operation receipt belongs to a different state backend")
    if document["operation_id_sha256"] != expected_operation_id_sha256:
        raise ValueError("operation receipt does not bind the exact evidence operation ID")

    policy_digest = hashlib.sha256(raw_policy_envelope_bytes).hexdigest()
    receipt_digest = hashlib.sha256(raw_receipt_bytes).hexdigest()
    if document["policy_envelope_sha256"] != policy_digest:
        raise ValueError("operation receipt does not bind the exact policy envelope bytes")
    if document["receipt_sha256"] != receipt_digest:
        raise ValueError("operation receipt does not bind the exact receipt bytes")
    _require_sha256(document["operation_id_sha256"], "operation receipt operation_id_sha256")
    _require_sha256(document["policy_envelope_sha256"], "operation receipt policy_envelope_sha256")
    _require_sha256(document["receipt_sha256"], "operation receipt receipt_sha256")
    _require_sha256(
        document["accepted_external_evidence_watermark_sha256"],
        "operation receipt accepted_external_evidence_watermark_sha256",
    )
    _require_sha256(document["provisioning_record_sha256"], "operation receipt provisioning_record_sha256")
    _require_sha256(document["trust_configuration_sha256"], "operation receipt trust_configuration_sha256")
    _require_sha256(document["clock_sample_sha256"], "operation receipt clock_sample_sha256")
    _require_identifier(document["root_key_id"], "operation receipt root_key_id")
    _require_identifier(document["clock_source_id"], "operation receipt clock_source_id")
    if document["provider_key_id"] != snapshot.operation_receipt_key_id:
        raise ValueError("operation receipt provider key ID does not match the pinned snapshot key")
    if type(document["root_generation"]) is not int or not 1 <= document["root_generation"] <= MAX_POLICY_SEQUENCE:
        raise ValueError("operation receipt root_generation is invalid")
    if type(document["policy_sequence"]) is not int or not 1 <= document["policy_sequence"] <= MAX_POLICY_SEQUENCE:
        raise ValueError("operation receipt policy_sequence is invalid")
    before = document["state_generation_before"]
    after = document["state_generation_after"]
    if type(before) is not int or type(after) is not int or not 0 <= before <= after <= MAX_POLICY_SEQUENCE:
        raise ValueError("operation receipt state generations are invalid")
    try:
        outcome = TrustStateOutcome(document["outcome"])
    except (TypeError, ValueError) as exc:
        raise ValueError("operation receipt outcome is invalid") from exc
    if outcome not in {
        TrustStateOutcome.ADVANCED,
        TrustStateOutcome.IDEMPOTENT,
        TrustStateOutcome.TIME_ADVANCED,
        TrustStateOutcome.EVIDENCE_ADVANCED,
        TrustStateOutcome.TIME_AND_EVIDENCE_ADVANCED,
    }:
        raise ValueError("operation receipt cannot attest a rejected provider outcome")
    if (outcome is TrustStateOutcome.IDEMPOTENT and after != before) or (
        outcome is not TrustStateOutcome.IDEMPOTENT and after != before + 1
    ):
        raise ValueError("operation receipt state-generation transition is inconsistent")

    trusted_latest = _clock_sample_timestamp(
        document["trusted_time_latest_utc"], "operation receipt trusted_time_latest_utc"
    )
    clock_valid_until = _clock_sample_timestamp(
        document["clock_sample_valid_until_utc"], "operation receipt clock_sample_valid_until_utc"
    )
    window_start = _clock_sample_timestamp(
        document["time_window_start_utc"], "operation receipt time_window_start_utc"
    )
    window_end = _clock_sample_timestamp(
        document["time_window_end_utc"], "operation receipt time_window_end_utc"
    )
    if not window_start <= window_end <= clock_valid_until <= trusted_latest:
        raise ValueError("operation receipt time interval is inconsistent")
    signature_b64 = document["signature_b64"]
    if type(signature_b64) is not str:
        raise ValueError("operation receipt signature_b64 must be canonical base64")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("operation receipt signature_b64 is invalid") from exc
    if len(signature) != 64 or base64.b64encode(signature).decode("ascii") != signature_b64:
        raise ValueError("operation receipt signature must be 64 canonical base64 bytes")
    unsigned = dict(document)
    unsigned.pop("signature_b64")
    message = b"ORIGEN_DEPLOYMENT_TRUST_OPERATION_RECEIPT_V1\\x00" + json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    try:
        Ed25519PublicKey.from_public_bytes(
            snapshot.operation_receipt_public_key_bytes
        ).verify(signature, message)
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("provider operation receipt signature verification failed") from exc
    return document


def _read_verified_operation_receipt(
    provider: DeploymentTrustProvider,
    snapshot: DeploymentTrustSnapshot,
    *,
    operation_id_sha256: str,
    raw_policy_envelope_bytes: bytes,
    raw_receipt_bytes: bytes,
) -> DeploymentTrustInspection | None:
    reader = getattr(provider, "read_operation_receipt", None)
    if not callable(reader):
        return None
    try:
        raw = reader(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            expected_state_backend_id=snapshot.state_backend_id,
            operation_id_sha256=operation_id_sha256,
        )
    except Exception as exc:
        raise TrustProviderUnavailable(
            "provider operation-receipt query failed; durable outcome remains unknown",
            operation_id_sha256=operation_id_sha256,
        ) from exc
    if raw is None:
        return None
    try:
        document = _verify_deployment_trust_operation_receipt(
            raw,
            snapshot=snapshot,
            expected_operation_id_sha256=operation_id_sha256,
            raw_policy_envelope_bytes=raw_policy_envelope_bytes,
            raw_receipt_bytes=raw_receipt_bytes,
        )
        state_generation_after = document["state_generation_after"]
        if state_generation_after > snapshot.state_generation:
            raise ValueError("operation receipt is ahead of the current provider state generation")
        if document["policy_sequence"] > snapshot.accepted_policy_sequence:
            raise ValueError("operation receipt policy sequence is ahead of current provider state")
        if (
            document["policy_sequence"] == snapshot.accepted_policy_sequence
            and document["policy_envelope_sha256"] != snapshot.accepted_policy_envelope_sha256
        ):
            raise ValueError("operation receipt conflicts with the current accepted policy digest")
        if document["root_generation"] > snapshot.root_generation:
            raise ValueError("operation receipt root generation is ahead of current provider state")
        if (
            document["root_generation"] == snapshot.root_generation
            and document["root_key_id"] != snapshot.root_key_id
        ):
            raise ValueError("operation receipt root key conflicts with current provider state")
        latest = _clock_sample_timestamp(
            document["trusted_time_latest_utc"], "operation receipt trusted_time_latest_utc"
        )
        if snapshot.trusted_time_latest_utc is None or latest > snapshot.trusted_time_latest_utc:
            raise ValueError("operation receipt is ahead of the current trusted-time watermark")
        return DeploymentTrustInspection(
            receipt_sha256=document["receipt_sha256"],
            policy_envelope_sha256=document["policy_envelope_sha256"],
            policy_domain=document["policy_domain"],
            policy_sequence=document["policy_sequence"],
            root_key_id=document["root_key_id"],
            root_generation=document["root_generation"],
            provisioning_record_sha256=document["provisioning_record_sha256"],
            trust_configuration_sha256=document["trust_configuration_sha256"],
            clock_source_id=document["clock_source_id"],
            clock_sample_sha256=document["clock_sample_sha256"],
            clock_sample_valid_until_utc=_clock_sample_timestamp(
                document["clock_sample_valid_until_utc"],
                "operation receipt clock_sample_valid_until_utc",
            ),
            state_backend_id=document["state_backend_id"],
            time_window_start_utc=_clock_sample_timestamp(
                document["time_window_start_utc"], "operation receipt time_window_start_utc"
            ),
            time_window_end_utc=_clock_sample_timestamp(
                document["time_window_end_utc"], "operation receipt time_window_end_utc"
            ),
            state_generation_before=document["state_generation_before"],
            state_generation_after=document["state_generation_after"],
            state_outcome=TrustStateOutcome(document["outcome"]),
            provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
            timestamp_nonce_challenge_id=None,
            timestamp_nonce_challenge_sha256=None,
            operation_id_sha256=operation_id_sha256,
            operation_replayed=True,
            operation_receipt_sha256=hashlib.sha256(raw).hexdigest(),
        )
    except (TypeError, ValueError) as exc:
        raise TrustProviderUnavailable(
            "provider returned an invalid or nonmatching signed operation receipt; "
            "durable outcome remains unknown",
            operation_id_sha256=operation_id_sha256,
        ) from exc


def _trust_configuration_sha256(snapshot: DeploymentTrustSnapshot) -> str:
    """Fingerprint immutable deployment trust configuration, not its authenticity."""
    payload = {
        "schema": "origen.deployment-trust-configuration.v1",
        "policy_domain": snapshot.policy_domain,
        "root_public_key_sha256": hashlib.sha256(snapshot.root_public_key_bytes).hexdigest(),
        "root_key_id": snapshot.root_key_id,
        "root_generation": snapshot.root_generation,
        "minimum_policy_sequence": snapshot.minimum_policy_sequence,
        "maximum_clock_uncertainty_ms": snapshot.maximum_clock_uncertainty_ms,
        "maximum_clock_sample_age_ms": snapshot.maximum_clock_sample_age_ms,
        "clock_source_id": snapshot.clock_source_id,
        "clock_sample_key_id": snapshot.clock_sample_key_id,
        "clock_sample_public_key_sha256": hashlib.sha256(
            snapshot.clock_sample_public_key_bytes
        ).hexdigest(),
        "state_backend_id": snapshot.state_backend_id,
        "provisioning_record_sha256": snapshot.provisioning_record_sha256,
        "operation_receipt_key_id": snapshot.operation_receipt_key_id,
        "operation_receipt_public_key_sha256": (
            None if snapshot.operation_receipt_public_key_bytes is None
            else hashlib.sha256(snapshot.operation_receipt_public_key_bytes).hexdigest()
        ),
    }
    if snapshot.physical_trust_context_generation is not None:
        payload["physical_trust_context_generation"] = snapshot.physical_trust_context_generation
        payload["physical_trust_context_sha256"] = snapshot.physical_trust_context_sha256
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()

def _clock_sample_pairs_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("clock sample contains a duplicate JSON key")
        result[key] = value
    return result


def _clock_sample_reject_constant(value: str):
    raise ValueError("clock sample contains a non-finite JSON number")


def _clock_sample_timestamp(value: object, field: str) -> datetime:
    if type(value) is not str or not _CLOCK_SAMPLE_UTC.fullmatch(value):
        raise ValueError(f"{field} must be canonical UTC with six fractional digits")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid UTC calendar timestamp") from exc


def _clock_sample_canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _verify_clock_sample_attestation(snapshot: DeploymentTrustSnapshot) -> None:
    """Verify the provider-issued clock sample under its separately provisioned key.

    The key is supplied by the trusted deployment provider and is not an
    institutional identity claim. The provider must independently repeat this
    verification against its authoritative key and current sample inside CAS.
    """
    raw = snapshot.clock_sample_envelope_bytes
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_CLOCK_SAMPLE_BYTES:
        raise ValueError("clock sample attestation must be exact bytes within size limit")
    if type(snapshot.clock_sample_public_key_bytes) is not bytes or len(
        snapshot.clock_sample_public_key_bytes
    ) != 32:
        raise ValueError("clock sample Ed25519 public key must be exactly 32 immutable bytes")
    _require_identifier(snapshot.clock_sample_key_id, "clock_sample_key_id")

    try:
        document = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_clock_sample_pairs_no_duplicates,
            parse_constant=_clock_sample_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("clock sample attestation must be canonical ASCII JSON") from exc
    if type(document) is not dict:
        raise ValueError("clock sample attestation must be a JSON object")
    expected_fields = {
        "schema",
        "policy_domain",
        "clock_source_id",
        "clock_sample_id",
        "sampled_at_utc",
        "uncertainty_ms",
        "valid_until_utc",
        "key_id",
        "signature",
    }
    if set(document) != expected_fields:
        raise ValueError("clock sample attestation fields do not match the exact schema")
    if _clock_sample_canonical(document) != raw:
        raise ValueError("clock sample attestation bytes are not canonical JSON")

    signature = document["signature"]
    if type(signature) is not dict or set(signature) != {"algorithm", "signature_b64"}:
        raise ValueError("clock sample signature object does not match the exact schema")
    if signature["algorithm"] != "ed25519":
        raise ValueError("clock sample signature algorithm must be ed25519")
    encoded = signature["signature_b64"]
    if type(encoded) is not str:
        raise ValueError("clock sample signature must be canonical base64 text")
    try:
        signature_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("clock sample signature is not valid base64") from exc
    if (
        len(signature_bytes) != 64
        or base64.b64encode(signature_bytes).decode("ascii") != encoded
    ):
        raise ValueError("clock sample signature must be exactly 64 canonical base64 bytes")

    if document["schema"] != CLOCK_SAMPLE_SCHEMA:
        raise ValueError("clock sample attestation schema is unsupported")
    if document["policy_domain"] != CLASSIC_POLICY_DOMAIN:
        raise ValueError("clock sample attestation is not scoped to the fixed CLASSIC domain")
    if document["clock_source_id"] != snapshot.clock_source_id:
        raise ValueError("clock sample attestation source does not match provider snapshot")
    if document["clock_sample_id"] != snapshot.clock_sample_id:
        raise ValueError("clock sample attestation ID does not match provider snapshot")
    if document["key_id"] != snapshot.clock_sample_key_id:
        raise ValueError("clock sample attestation key ID does not match provider pin")

    sampled_at = _clock_sample_timestamp(document["sampled_at_utc"], "sampled_at_utc")
    valid_until = _clock_sample_timestamp(document["valid_until_utc"], "valid_until_utc")
    uncertainty = document["uncertainty_ms"]
    if type(uncertainty) is not int or not 0 <= uncertainty <= 2**31 - 1:
        raise ValueError("clock sample uncertainty_ms must be an exact bounded integer")
    if sampled_at != snapshot.trusted_time_utc:
        raise ValueError("signed clock sample time does not match provider snapshot")
    if uncertainty != snapshot.clock_uncertainty_ms:
        raise ValueError("signed clock sample uncertainty does not match provider snapshot")
    if valid_until != snapshot.clock_sample_valid_until_utc:
        raise ValueError("signed clock sample lease does not match provider snapshot")

    unsigned = dict(document)
    unsigned.pop("signature")
    message = b"ORIGEN_CLOCK_SAMPLE_V1\x00" + _clock_sample_canonical(unsigned)
    try:
        Ed25519PublicKey.from_public_bytes(
            snapshot.clock_sample_public_key_bytes
        ).verify(signature_bytes, message)
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("clock sample Ed25519 signature verification failed") from exc


def _require_clock_sample_key_authorized(
    verified_policy: VerifiedTrustPolicyV3,
    snapshot: DeploymentTrustSnapshot,
    *,
    earliest: datetime,
    latest: datetime,
) -> None:
    """Require the root-signed V3 policy to authorize this exact clock key."""
    matches = [
        key for key in verified_policy.policy.issuer_keys
        if key.issuer_id == snapshot.clock_source_id
        and key.key_id == snapshot.clock_sample_key_id
    ]
    if len(matches) != 1:
        raise ValueError("signed root policy does not contain exactly one clock-source key")
    key = matches[0]
    if key.public_key_bytes != snapshot.clock_sample_public_key_bytes:
        raise ValueError("clock sample public key does not match the root-authorized key")
    if key.revoked:
        raise ValueError("root-authorized clock sample key is revoked")
    if not (key.valid_from_utc <= earliest and latest <= key.valid_until_utc):
        raise ValueError("trusted-time uncertainty interval crosses clock key validity")
    required = (
        snapshot.clock_source_id,
        snapshot.clock_sample_key_id,
        "TRUSTED_TIME_AUTHORITY",
        ("CLOCK_SAMPLE",),
    )
    if required not in verified_policy.key_authorizations:
        raise ValueError("root-signed policy does not authorize clock-sample attestation role")


def _clock_sample_sha256(snapshot: DeploymentTrustSnapshot) -> str:
    """Hash the exact signed source sample bytes supplied to the provider CAS."""
    return hashlib.sha256(snapshot.clock_sample_envelope_bytes).hexdigest()


def _snapshot_copy(value: object) -> DeploymentTrustSnapshot:
    if type(value) is not DeploymentTrustSnapshot:
        raise TypeError("provider must return an exact DeploymentTrustSnapshot")

    # Copy all primitive immutable fields before any verification or provider
    # write so later provider-side mutation cannot change this operation.
    snapshot = DeploymentTrustSnapshot(
        policy_domain=value.policy_domain,
        root_public_key_bytes=value.root_public_key_bytes,
        root_key_id=value.root_key_id,
        root_generation=value.root_generation,
        minimum_policy_sequence=value.minimum_policy_sequence,
        state_generation=value.state_generation,
        accepted_policy_sequence=value.accepted_policy_sequence,
        accepted_policy_envelope_sha256=value.accepted_policy_envelope_sha256,
        trusted_time_latest_utc=value.trusted_time_latest_utc,
        trusted_time_utc=value.trusted_time_utc,
        clock_uncertainty_ms=value.clock_uncertainty_ms,
        maximum_clock_uncertainty_ms=value.maximum_clock_uncertainty_ms,
        clock_source_id=value.clock_source_id,
        clock_sample_key_id=value.clock_sample_key_id,
        clock_sample_public_key_bytes=value.clock_sample_public_key_bytes,
        clock_sample_envelope_bytes=value.clock_sample_envelope_bytes,
        clock_sample_id=value.clock_sample_id,
        clock_sample_valid_until_utc=value.clock_sample_valid_until_utc,
        maximum_clock_sample_age_ms=value.maximum_clock_sample_age_ms,
        state_backend_id=value.state_backend_id,
        provisioning_record_sha256=value.provisioning_record_sha256,
        physical_trust_context_generation=value.physical_trust_context_generation,
        physical_trust_context_sha256=value.physical_trust_context_sha256,
        accepted_external_evidence_watermark=_external_evidence_watermark_copy(
            value.accepted_external_evidence_watermark
        ),
        operation_receipt_key_id=value.operation_receipt_key_id,
        operation_receipt_public_key_bytes=value.operation_receipt_public_key_bytes,
    )

    if (
        snapshot.accepted_external_evidence_watermark is not None
        and (
            snapshot.accepted_external_evidence_watermark.policy_domain != snapshot.policy_domain
            or snapshot.accepted_external_evidence_watermark.state_backend_id != snapshot.state_backend_id
        )
    ):
        raise ValueError("accepted external evidence watermark is not bound to the deployment snapshot")

    if type(snapshot.policy_domain) is not str or snapshot.policy_domain != CLASSIC_POLICY_DOMAIN:
        raise ValueError("deployment trust snapshot is not scoped to the fixed CLASSIC domain")
    if type(snapshot.root_public_key_bytes) is not bytes or len(snapshot.root_public_key_bytes) != 32:
        raise ValueError("deployment root pin must be exactly 32 immutable bytes")
    _require_identifier(snapshot.root_key_id, "root_key_id")
    _require_identifier(snapshot.clock_source_id, "clock_source_id")
    _require_identifier(snapshot.clock_sample_key_id, "clock_sample_key_id")
    _require_identifier(snapshot.clock_sample_id, "clock_sample_id")
    _require_identifier(snapshot.state_backend_id, "state_backend_id")
    _require_sha256(snapshot.provisioning_record_sha256, "provisioning_record_sha256")
    context_generation = snapshot.physical_trust_context_generation
    context_digest = snapshot.physical_trust_context_sha256
    if (context_generation is None) != (context_digest is None):
        raise ValueError("physical trust context generation and digest must be supplied together")
    if context_generation is not None:
        if type(context_generation) is not int or not 1 <= context_generation <= MAX_POLICY_SEQUENCE:
            raise ValueError("physical_trust_context_generation must be an exact positive integer")
        _require_sha256(context_digest, "physical_trust_context_sha256")

    if (snapshot.operation_receipt_key_id is None) != (
        snapshot.operation_receipt_public_key_bytes is None
    ):
        raise ValueError("operation receipt key ID and public key must be supplied together")
    if snapshot.operation_receipt_key_id is not None:
        _require_identifier(snapshot.operation_receipt_key_id, "operation_receipt_key_id")
        if type(snapshot.operation_receipt_public_key_bytes) is not bytes or len(
            snapshot.operation_receipt_public_key_bytes
        ) != 32:
            raise ValueError("operation receipt public key must be exactly 32 immutable bytes")

    integer_fields = (
        ("root_generation", snapshot.root_generation, 1, MAX_POLICY_SEQUENCE),
        ("minimum_policy_sequence", snapshot.minimum_policy_sequence, 1, MAX_POLICY_SEQUENCE),
        ("state_generation", snapshot.state_generation, 0, MAX_POLICY_SEQUENCE),
        ("accepted_policy_sequence", snapshot.accepted_policy_sequence, 0, MAX_POLICY_SEQUENCE),
        ("clock_uncertainty_ms", snapshot.clock_uncertainty_ms, 0, 2**31 - 1),
        ("maximum_clock_uncertainty_ms", snapshot.maximum_clock_uncertainty_ms, 0, 2**31 - 1),
        ("maximum_clock_sample_age_ms", snapshot.maximum_clock_sample_age_ms, 1, 2**31 - 1),
    )
    for field, actual, minimum, maximum in integer_fields:
        if type(actual) is not int or not minimum <= actual <= maximum:
            raise ValueError(f"{field} must be an exact integer in the permitted range")

    if snapshot.accepted_policy_sequence == 0:
        if (
            snapshot.accepted_policy_envelope_sha256 is not None
            or snapshot.trusted_time_latest_utc is not None
        ):
            raise ValueError("empty accepted sequence must not have an envelope digest or accepted time")
    else:
        _require_sha256(
            snapshot.accepted_policy_envelope_sha256,
            "accepted_policy_envelope_sha256",
        )
        if (
            type(snapshot.trusted_time_latest_utc) is not datetime
            or snapshot.trusted_time_latest_utc.tzinfo is not timezone.utc
        ):
            raise ValueError("non-empty accepted sequence requires an exact normalized UTC trusted-time watermark")
    # The bootstrap floor and the last accepted sequence are independent
    # monotonic constraints. The effective floor is their maximum below; the
    # bootstrap floor may legitimately remain lower than accepted state.

    if type(snapshot.trusted_time_utc) is not datetime or snapshot.trusted_time_utc.tzinfo is not timezone.utc:
        raise ValueError("provider time must be one exact normalized UTC datetime")
    if (
        type(snapshot.clock_sample_valid_until_utc) is not datetime
        or snapshot.clock_sample_valid_until_utc.tzinfo is not timezone.utc
    ):
        raise ValueError("clock sample valid-until must be exact normalized UTC")
    sample_lifetime = snapshot.clock_sample_valid_until_utc - snapshot.trusted_time_utc
    if sample_lifetime <= timedelta(0):
        raise ValueError("provider clock sample lease is already expired")
    if sample_lifetime > timedelta(milliseconds=snapshot.maximum_clock_sample_age_ms):
        raise ValueError("clock sample lease exceeds the provisioned maximum age")
    if snapshot.clock_uncertainty_ms > snapshot.maximum_clock_uncertainty_ms:
        raise ValueError("provider clock uncertainty exceeds the provisioned maximum")
    _verify_clock_sample_attestation(snapshot)

    return snapshot


def _commit_copy(value: object) -> DeploymentTrustCommit:
    if type(value) is not DeploymentTrustCommit:
        raise TypeError("provider must return an exact DeploymentTrustCommit")
    if type(value.outcome) is not TrustStateOutcome:
        raise TypeError("provider commit outcome must be an exact TrustStateOutcome")
    if type(value.state_generation) is not int or not 0 <= value.state_generation <= MAX_POLICY_SEQUENCE:
        raise ValueError("provider commit state_generation is invalid")
    if type(value.policy_sequence) is not int or not 1 <= value.policy_sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError("provider commit policy_sequence is invalid")
    _require_sha256(value.policy_envelope_sha256, "provider commit policy_envelope_sha256")
    if (
        type(value.trusted_time_latest_utc) is not datetime
        or value.trusted_time_latest_utc.tzinfo is not timezone.utc
    ):
        raise ValueError("provider commit trusted_time_latest_utc must be exact normalized UTC")
    accepted_watermark_sha256 = value.accepted_external_evidence_watermark_sha256
    if accepted_watermark_sha256 is not None:
        _require_sha256(
            accepted_watermark_sha256,
            "provider commit accepted_external_evidence_watermark_sha256",
        )
    receipt_sha256 = value.receipt_sha256
    if receipt_sha256 is not None:
        _require_sha256(receipt_sha256, "provider commit receipt_sha256")
    operation_id_sha256 = value.operation_id_sha256
    if operation_id_sha256 is not None:
        _require_sha256(operation_id_sha256, "provider commit operation_id_sha256")
    return DeploymentTrustCommit(
        outcome=value.outcome,
        state_generation=value.state_generation,
        policy_sequence=value.policy_sequence,
        policy_envelope_sha256=value.policy_envelope_sha256,
        trusted_time_latest_utc=value.trusted_time_latest_utc,
        accepted_external_evidence_watermark_sha256=accepted_watermark_sha256,
        receipt_sha256=receipt_sha256,
        operation_id_sha256=operation_id_sha256,
    )


def _time_window(snapshot: DeploymentTrustSnapshot) -> tuple[datetime, datetime]:
    uncertainty = timedelta(milliseconds=snapshot.clock_uncertainty_ms)
    try:
        earliest = snapshot.trusted_time_utc - uncertainty
        latest = snapshot.trusted_time_utc + uncertainty
    except OverflowError as exc:
        raise ValueError("provider time uncertainty interval overflows UTC datetime") from exc
    return earliest, latest


def _require_policy_and_receipt_inside_time_window(
    verified_policy: VerifiedTrustPolicyV3,
    verified_receipt: CryptographicallyVerifiedReceipt,
    *,
    earliest: datetime,
    latest: datetime,
) -> None:
    # The whole clock uncertainty interval must fit inside the signed policy
    # validity interval; checking only its midpoint is insufficient.
    if not (
        verified_policy.issued_at_utc <= earliest
        and verified_policy.not_before_utc <= earliest
        and latest < verified_policy.expires_at_utc
    ):
        raise ValueError("trusted-time uncertainty interval crosses the signed policy validity boundary")

    attestation = verified_receipt.receipt.attestation
    try:
        signed_at = datetime.fromisoformat(
            attestation.signed_at_utc.replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except (AttributeError, ValueError) as exc:
        raise ValueError("receipt attestation signing time is not parseable") from exc
    # A policy that becomes effective after the receipt was signed must not
    # retroactively authorize that earlier attestation. The independent
    # provenance boundary repeats this check later, but reject here before the
    # expensive physical-signature / RFC 3161 / ledger / witness composition.
    if not (
        verified_policy.not_before_utc <= signed_at
        < verified_policy.expires_at_utc
    ):
        raise ValueError("receipt signing time is outside the signed policy effective interval")
    if signed_at > earliest:
        raise ValueError("receipt signing time is not provably before the earliest trusted verification time")

    matching_keys = [
        key for key in verified_policy.policy.issuer_keys
        if key.issuer_id == verified_receipt.verified_issuer_id
        and key.key_id == verified_receipt.verified_key_id
    ]
    if len(matching_keys) != 1:
        raise ValueError("verified policy does not contain exactly one receipt issuer key")
    key = matching_keys[0]
    if not (key.valid_from_utc <= earliest and latest <= key.valid_until_utc):
        raise ValueError("trusted-time uncertainty interval crosses the receipt issuer-key validity boundary")


def _inspect_receipt_with_deployment_trust_provider_snapshot(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    provider: DeploymentTrustProvider,
    provider_snapshot: DeploymentTrustSnapshot,
    timestamp_nonce_challenge_id: str | None = None,
    timestamp_nonce_challenge_sha256: str | None = None,
    external_evidence_advance: ExternalEvidenceAdvanceV1 | None = None,
) -> DeploymentTrustInspection:
    """Internal composition helper bound to one provider snapshot.

    The top-level public API obtains its own snapshot before calling this
    helper. The full-evidence composition module may call it with the exact
    snapshot that module already obtained and validated, avoiding a second
    provider read and preserving one-snapshot composition across physical,
    policy, clock and CAS checks. The helper is private by convention, not an
    unforgeable Python capability; the provider CAS must bind the supplied
    snapshot to authoritative state. No institutional provider is included.
    Every successful inspection remains BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes or not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must be non-empty exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes or not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must be non-empty exact bytes")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError("original_receipt_bytes exceeds the trust receipt size limit")
    if len(signed_policy_envelope_bytes) > MAX_POLICY_BYTES:
        raise ValueError("signed_policy_envelope_bytes exceeds the trust policy size limit")

    if (timestamp_nonce_challenge_id is None) != (timestamp_nonce_challenge_sha256 is None):
        raise ValueError("timestamp nonce challenge ID and digest must be supplied together")
    if timestamp_nonce_challenge_id is not None:
        _require_identifier(timestamp_nonce_challenge_id, "timestamp_nonce_challenge_id")
        _require_sha256(timestamp_nonce_challenge_sha256, "timestamp_nonce_challenge_sha256")

    compare_and_advance = getattr(provider, "compare_and_advance", None)
    if not callable(compare_and_advance):
        raise TypeError("provider must implement compare_and_advance")
    snapshot = _snapshot_copy(provider_snapshot)
    external_evidence_advance = (
        None
        if external_evidence_advance is None
        else _external_evidence_advance_copy(external_evidence_advance)
    )
    operation_id_sha256 = _deployment_trust_operation_id_sha256(
        signed_policy_envelope_bytes,
        original_receipt_bytes,
        external_evidence_advance,
    )
    expected_external_evidence_watermark_sha256 = (
        _accepted_external_evidence_watermark_sha256(snapshot.accepted_external_evidence_watermark)
    )
    next_external_evidence_watermark = _validated_external_evidence_watermark(
        snapshot,
        expected_external_evidence_watermark_sha256,
        external_evidence_advance,
        allow_replay_candidate=True,
    )
    next_external_evidence_watermark_sha256 = (
        _accepted_external_evidence_watermark_sha256(next_external_evidence_watermark)
    )
    replay = _read_verified_operation_receipt(
        provider,
        snapshot,
        operation_id_sha256=operation_id_sha256,
        raw_policy_envelope_bytes=signed_policy_envelope_bytes,
        raw_receipt_bytes=original_receipt_bytes,
    )
    if replay is not None:
        return replay
    trust_configuration_digest = _trust_configuration_sha256(snapshot)
    clock_sample_digest = _clock_sample_sha256(snapshot)
    earliest, latest = _time_window(snapshot)
    if latest > snapshot.clock_sample_valid_until_utc:
        raise ValueError("trusted-time uncertainty interval exceeds the provider clock sample lease")

    effective_floor = max(
        snapshot.minimum_policy_sequence,
        snapshot.accepted_policy_sequence,
    )
    verified_policy: VerifiedTrustPolicyV3 = verify_signed_trust_policy_v3(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=snapshot.root_public_key_bytes,
        expected_root_key_id=snapshot.root_key_id,
        expected_policy_domain=CLASSIC_POLICY_DOMAIN,
        minimum_policy_sequence=effective_floor,
        verification_time=snapshot.trusted_time_utc,
    )
    if type(verified_policy) is not VerifiedTrustPolicyV3:
        raise TypeError("policy verifier returned an unexpected result type")
    _require_clock_sample_key_authorized(
        verified_policy,
        snapshot,
        earliest=earliest,
        latest=latest,
    )

    policy_digest = hashlib.sha256(signed_policy_envelope_bytes).hexdigest()
    if verified_policy.envelope_sha256 != policy_digest:
        raise ValueError("verified policy does not bind the exact envelope bytes")
    if external_evidence_advance is not None and (
        external_evidence_advance.raw_receipt_bytes != original_receipt_bytes
        or external_evidence_advance.raw_policy_envelope_bytes != signed_policy_envelope_bytes
    ):
        raise TrustStateRejected(
            "external evidence advance does not carry the exact receipt and policy bytes supplied to the verifier"
        )
    # The trusted clock must remain monotonic across every inspection. The
    # provider persists later same-sequence observations too; checking only
    # against the last policy acceptance would permit rollback after a newer
    # idempotent read.
    if (
        snapshot.trusted_time_latest_utc is not None
        and earliest < snapshot.trusted_time_latest_utc
    ):
        raise TrustStateRejected(
            "trusted-time interval regressed behind the persisted time watermark"
        )
    if snapshot.accepted_policy_sequence == verified_policy.policy_sequence:
        if snapshot.accepted_policy_envelope_sha256 != policy_digest:
            raise TrustStateRejected("same policy sequence is already bound to a different envelope digest")

    verified_receipt: CryptographicallyVerifiedReceipt = verify_receipt_attestation(
        original_receipt_bytes,
        verified_policy.policy,
        verification_time=snapshot.trusted_time_utc,
    )
    if type(verified_receipt) is not CryptographicallyVerifiedReceipt:
        raise TypeError("receipt verifier returned an unexpected result type")
    _require_policy_and_receipt_inside_time_window(
        verified_policy,
        verified_receipt,
        earliest=earliest,
        latest=latest,
    )

    provenance = _verify_independent_provenance_with_explicit_context(
        original_receipt_bytes,
        signed_policy_envelope_bytes=signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=snapshot.root_public_key_bytes,
        expected_root_key_id=snapshot.root_key_id,
        minimum_policy_sequence=effective_floor,
        verification_time=snapshot.trusted_time_utc,
    )
    if provenance is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("independent provenance gate returned an unsupported non-blocked status")

    try:
        supplied_commit = compare_and_advance(
            expected_state_generation=snapshot.state_generation,
            expected_trust_configuration_sha256=trust_configuration_digest,
            expected_clock_sample_sha256=clock_sample_digest,
            operation_id_sha256=operation_id_sha256,
            policy_domain=CLASSIC_POLICY_DOMAIN,
            root_key_id=snapshot.root_key_id,
            root_generation=snapshot.root_generation,
            policy_sequence=verified_policy.policy_sequence,
            policy_envelope_sha256=policy_digest,
            raw_policy_envelope_bytes=signed_policy_envelope_bytes,
            raw_receipt_bytes=original_receipt_bytes,
            expected_external_evidence_watermark_sha256=expected_external_evidence_watermark_sha256,
            external_evidence_advance=external_evidence_advance,
            timestamp_nonce_challenge_id=timestamp_nonce_challenge_id,
            timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256,
        )
    except Exception as exc:
        # A provider/RPC exception is not an authenticated transaction result.
        # The backend may have committed before an adapter raised any local
        # exception class, including TrustStateRejected. Only a validated
        # DeploymentTrustCommit outcome below can establish an explicit rejection.
        raise TrustProviderUnavailable(
            "deployment trust sequence transaction failed; transaction outcome is unknown; "
            "retry only with the same exact evidence operation ID after provider reconciliation",
            operation_id_sha256=operation_id_sha256,
        ) from exc
    try:
        commit = _commit_copy(supplied_commit)
    except (TypeError, ValueError) as exc:
        raise TrustProviderUnavailable(
            "provider commit acknowledgement is malformed; transaction outcome is unknown; "
            "reconcile before retrying",
            operation_id_sha256=operation_id_sha256,
        ) from exc

    if commit.outcome in {
        TrustStateOutcome.CONFLICT,
        TrustStateOutcome.ROLLBACK,
        TrustStateOutcome.TIME_ROLLBACK,
        TrustStateOutcome.EQUIVOCATION,
    }:
        raise TrustStateRejected(
            "provider compare-and-advance rejected a stale, regressed, or equivocal state"
        )
    if commit.operation_id_sha256 != operation_id_sha256:
        raise TrustProviderUnavailable(
            "provider commit acknowledgement does not bind the exact evidence operation ID; "
            "transaction outcome is unknown; reconcile before retrying",
            operation_id_sha256=operation_id_sha256,
        )
    if (
        commit.policy_sequence != verified_policy.policy_sequence
        or commit.policy_envelope_sha256 != policy_digest
    ):
        raise TrustProviderUnavailable(
            "provider commit acknowledgement does not bind the exact verified policy; "
            "transaction outcome is unknown; reconcile before retrying",
            operation_id_sha256=operation_id_sha256,
        )
    receipt_digest = hashlib.sha256(original_receipt_bytes).hexdigest()
    if commit.receipt_sha256 != receipt_digest:
        raise TrustProviderUnavailable(
            "provider commit acknowledgement does not bind the exact verified receipt; "
            "transaction outcome is unknown; reconcile before retrying",
            operation_id_sha256=operation_id_sha256,
        )
    if commit.accepted_external_evidence_watermark_sha256 != next_external_evidence_watermark_sha256:
        raise TrustProviderUnavailable(
            "provider commit acknowledgement does not bind the resulting external ledger/witness watermark; "
            "transaction outcome is unknown; reconcile before retrying",
            operation_id_sha256=operation_id_sha256,
        )

    policy_advanced = snapshot.accepted_policy_sequence < verified_policy.policy_sequence
    time_advanced = (
        snapshot.trusted_time_latest_utc is None
        or latest > snapshot.trusted_time_latest_utc
    )
    evidence_advanced = (
        next_external_evidence_watermark_sha256 != expected_external_evidence_watermark_sha256
    )
    expected_latest = latest if time_advanced else snapshot.trusted_time_latest_utc

    if policy_advanced:
        expected_outcome = TrustStateOutcome.ADVANCED
    elif evidence_advanced and time_advanced:
        expected_outcome = TrustStateOutcome.TIME_AND_EVIDENCE_ADVANCED
    elif evidence_advanced:
        expected_outcome = TrustStateOutcome.EVIDENCE_ADVANCED
    elif time_advanced:
        expected_outcome = TrustStateOutcome.TIME_ADVANCED
    else:
        expected_outcome = TrustStateOutcome.IDEMPOTENT

    expected_generation = snapshot.state_generation + (1 if expected_outcome is not TrustStateOutcome.IDEMPOTENT else 0)
    if (
        commit.outcome is not expected_outcome
        or commit.state_generation != expected_generation
        or commit.trusted_time_latest_utc != expected_latest
    ):
        raise TrustProviderUnavailable(
            "provider commit acknowledgement does not match the expected policy/time/evidence transition; "
            "transaction outcome is unknown; reconcile durable provider state before retrying"
        )

    return DeploymentTrustInspection(
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        policy_envelope_sha256=policy_digest,
        policy_domain=CLASSIC_POLICY_DOMAIN,
        policy_sequence=verified_policy.policy_sequence,
        root_key_id=snapshot.root_key_id,
        root_generation=snapshot.root_generation,
        provisioning_record_sha256=snapshot.provisioning_record_sha256,
        trust_configuration_sha256=trust_configuration_digest,
        clock_source_id=snapshot.clock_source_id,
        clock_sample_sha256=clock_sample_digest,
        clock_sample_valid_until_utc=snapshot.clock_sample_valid_until_utc,
        state_backend_id=snapshot.state_backend_id,
        time_window_start_utc=earliest,
        time_window_end_utc=latest,
        state_generation_before=snapshot.state_generation,
        state_generation_after=commit.state_generation,
        state_outcome=commit.outcome,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        timestamp_nonce_challenge_id=timestamp_nonce_challenge_id,
        timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256,
        operation_id_sha256=operation_id_sha256,
    )

def _inspect_receipt_with_deployment_trust_provider_using_provider(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    provider: DeploymentTrustProvider,
    timestamp_nonce_challenge_id: str | None = None,
    timestamp_nonce_challenge_sha256: str | None = None,
    external_evidence_advance: ExternalEvidenceAdvanceV1 | None = None,
) -> DeploymentTrustInspection:
    """Private provider-backed implementation used only by deployment composition."""
    read_snapshot = getattr(provider, "read_snapshot", None)
    if not callable(read_snapshot):
        raise TypeError("provider must implement read_snapshot")
    try:
        snapshot = read_snapshot(policy_domain=CLASSIC_POLICY_DOMAIN)
    except Exception as exc:
        raise TrustProviderUnavailable("deployment trust snapshot could not be read") from exc
    return _inspect_receipt_with_deployment_trust_provider_snapshot(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        provider=provider,
        provider_snapshot=snapshot,
        timestamp_nonce_challenge_id=timestamp_nonce_challenge_id,
        timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256,
        external_evidence_advance=external_evidence_advance,
    )


def inspect_receipt_with_deployment_trust_provider(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    timestamp_nonce_challenge_id: str | None = None,
    timestamp_nonce_challenge_sha256: str | None = None,
) -> DeploymentTrustInspection:

    """Public fail-closed facade; provider configuration is deployment-owned."""
    from .deployment_trust_provider_bootstrap import _load_deployment_trust_provider

    try:
        provider = _load_deployment_trust_provider()
    except Exception as exc:
        raise TrustProviderUnavailable(
            "deployment trust provider bootstrap could not be loaded"
        ) from exc
    if provider is None:
        raise TrustProviderUnavailable(
            "deployment trust provider is not out-of-band provisioned"
        )
    return _inspect_receipt_with_deployment_trust_provider_using_provider(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        provider=provider,
        timestamp_nonce_challenge_id=timestamp_nonce_challenge_id,
        timestamp_nonce_challenge_sha256=timestamp_nonce_challenge_sha256,
    )
