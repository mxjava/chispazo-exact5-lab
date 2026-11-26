"""Research-only deployment trust-provider boundary with atomic anti-rollback CAS.

This module defines the application-facing contract for a separately provisioned
trust-state service. It deliberately includes no production provider or local
fallback. Test providers are synthetic and belong only in the test suite.

A provider object is a trusted composition-root dependency, not an unforgeable
Python capability. The contract cannot authenticate its own implementation.
Every successful inspection still returns BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Protocol

from .independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
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
    EQUIVOCATION = "EQUIVOCATION"


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
    clock_sample_id: str
    clock_sample_valid_until_utc: datetime
    maximum_clock_sample_age_ms: int
    state_backend_id: str
    provisioning_record_sha256: str


@dataclass(frozen=True, slots=True)
class DeploymentTrustCommit:
    """Result of a linearizable compare-and-advance operation."""

    outcome: TrustStateOutcome
    state_generation: int
    policy_sequence: int
    policy_envelope_sha256: str
    trusted_time_latest_utc: datetime


class DeploymentTrustProvider(Protocol):
    """Trusted composition-root dependency; no implementation ships here.

    read_snapshot must return one internally consistent snapshot of root pin,
    sequence state, generation, and authenticated clock metadata.

    compare_and_advance must be linearizable. It must compare the exact state
    generation and expected trust-configuration digest observed by read_snapshot
    and atomically enforce monotonic sequence/digest/time semantics for every
    inspection. It must recompute the configuration digest from authoritative
    provider state; it must not trust the caller's digest as a replacement for
    that comparison. Candidate earliest
    time (accepted_at_utc - clock_uncertainty) must not precede the stored
    trusted_time_latest_utc. The expected clock-sample digest must be
    recomputed against the authoritative current source sample inside the
    transaction; reject a changed sample or an expired sample lease. For a
    higher sequence, persist the candidate sequence, digest, and latest time. For the same sequence and digest, persist
    a later disjoint time watermark with one generation increment and return
    TIME_ADVANCED; if the watermark is unchanged, return IDEMPOTENT without a
    generation increment. It must never silently reset or restore any value.
    """

    def read_snapshot(self, *, policy_domain: str) -> DeploymentTrustSnapshot:
        ...

    def compare_and_advance(
        self,
        *,
        expected_state_generation: int,
        expected_trust_configuration_sha256: str,
        expected_clock_sample_sha256: str,
        policy_domain: str,
        root_key_id: str,
        root_generation: int,
        policy_sequence: int,
        policy_envelope_sha256: str,
        accepted_at_utc: datetime,
        clock_uncertainty_ms: int,
    ) -> DeploymentTrustCommit:
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


class TrustProviderUnavailable(RuntimeError):
    """The external provider could not supply or commit trusted state."""


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
        "state_backend_id": snapshot.state_backend_id,
        "provisioning_record_sha256": snapshot.provisioning_record_sha256,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()

def _clock_sample_sha256(snapshot: DeploymentTrustSnapshot) -> str:
    """Bind the exact provider-issued clock sample descriptor to the CAS."""
    payload = {
        "schema": "origen.authenticated-clock-sample.v1",
        "clock_source_id": snapshot.clock_source_id,
        "clock_sample_id": snapshot.clock_sample_id,
        "trusted_time_utc": snapshot.trusted_time_utc.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z"),
        "clock_uncertainty_ms": snapshot.clock_uncertainty_ms,
        "clock_sample_valid_until_utc": snapshot.clock_sample_valid_until_utc.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z"),
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()


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
        clock_sample_id=value.clock_sample_id,
        clock_sample_valid_until_utc=value.clock_sample_valid_until_utc,
        maximum_clock_sample_age_ms=value.maximum_clock_sample_age_ms,
        state_backend_id=value.state_backend_id,
        provisioning_record_sha256=value.provisioning_record_sha256,
    )

    if type(snapshot.policy_domain) is not str or snapshot.policy_domain != CLASSIC_POLICY_DOMAIN:
        raise ValueError("deployment trust snapshot is not scoped to the fixed CLASSIC domain")
    if type(snapshot.root_public_key_bytes) is not bytes or len(snapshot.root_public_key_bytes) != 32:
        raise ValueError("deployment root pin must be exactly 32 immutable bytes")
    _require_identifier(snapshot.root_key_id, "root_key_id")
    _require_identifier(snapshot.clock_source_id, "clock_source_id")
    _require_identifier(snapshot.clock_sample_id, "clock_sample_id")
    _require_identifier(snapshot.state_backend_id, "state_backend_id")
    _require_sha256(snapshot.provisioning_record_sha256, "provisioning_record_sha256")

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
        raise ValueError("authenticated clock sample lease is already expired")
    if sample_lifetime > timedelta(milliseconds=snapshot.maximum_clock_sample_age_ms):
        raise ValueError("clock sample lease exceeds the provisioned maximum age")
    if snapshot.clock_uncertainty_ms > snapshot.maximum_clock_uncertainty_ms:
        raise ValueError("provider clock uncertainty exceeds the provisioned maximum")

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
    return DeploymentTrustCommit(
        outcome=value.outcome,
        state_generation=value.state_generation,
        policy_sequence=value.policy_sequence,
        policy_envelope_sha256=value.policy_envelope_sha256,
        trusted_time_latest_utc=value.trusted_time_latest_utc,
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


def inspect_receipt_with_deployment_trust_provider(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    provider: DeploymentTrustProvider,
) -> DeploymentTrustInspection:
    """Inspect policy and receipt through provider-supplied deployment state.

    This function removes root pins, sequence floors, and clock values from
    request-level arguments. It does not authenticate the provider object:
    deployment must construct it in a reviewed composition root backed by an
    independently provisioned trust store, monotonic state service, and
    authenticated clock. No such provider is included in this repository.

    It verifies exact bytes, requires the complete trusted-time uncertainty
    interval to fit policy and signer validity, calls the independent
    provenance boundary, and then performs an atomic sequence/digest
    compare-and-advance. Any provider failure or state conflict raises and
    yields no inspection result. Success remains BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes or not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must be non-empty exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes or not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must be non-empty exact bytes")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError("original_receipt_bytes exceeds the trust receipt size limit")
    if len(signed_policy_envelope_bytes) > MAX_POLICY_BYTES:
        raise ValueError("signed_policy_envelope_bytes exceeds the trust policy size limit")

    read_snapshot = getattr(provider, "read_snapshot", None)
    compare_and_advance = getattr(provider, "compare_and_advance", None)
    if not callable(read_snapshot) or not callable(compare_and_advance):
        raise TypeError("provider must implement read_snapshot and compare_and_advance")

    try:
        supplied_snapshot = read_snapshot(policy_domain=CLASSIC_POLICY_DOMAIN)
    except Exception as exc:
        raise TrustProviderUnavailable("deployment trust snapshot could not be read") from exc
    snapshot = _snapshot_copy(supplied_snapshot)
    trust_configuration_digest = _trust_configuration_sha256(snapshot)
    clock_sample_digest = _clock_sample_sha256(snapshot)
    earliest, latest = _time_window(snapshot)
    if latest > snapshot.clock_sample_valid_until_utc:
        raise ValueError("trusted-time uncertainty interval exceeds the authenticated clock sample lease")

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

    policy_digest = hashlib.sha256(signed_policy_envelope_bytes).hexdigest()
    if verified_policy.envelope_sha256 != policy_digest:
        raise ValueError("verified policy does not bind the exact envelope bytes")
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

    provenance = verify_independent_provenance(
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
            policy_domain=CLASSIC_POLICY_DOMAIN,
            root_key_id=snapshot.root_key_id,
            root_generation=snapshot.root_generation,
            policy_sequence=verified_policy.policy_sequence,
            policy_envelope_sha256=policy_digest,
            accepted_at_utc=snapshot.trusted_time_utc,
            clock_uncertainty_ms=snapshot.clock_uncertainty_ms,
        )
    except Exception as exc:
        raise TrustProviderUnavailable("deployment trust sequence transaction failed") from exc
    commit = _commit_copy(supplied_commit)

    if (
        commit.policy_sequence != verified_policy.policy_sequence
        or commit.policy_envelope_sha256 != policy_digest
    ):
        raise TrustStateRejected("provider commit does not bind the exact verified policy")
    if snapshot.accepted_policy_sequence == verified_policy.policy_sequence:
        if commit.outcome is TrustStateOutcome.IDEMPOTENT:
            if (
                commit.state_generation != snapshot.state_generation
                or commit.trusted_time_latest_utc != snapshot.trusted_time_latest_utc
                or latest != snapshot.trusted_time_latest_utc
            ):
                raise TrustStateRejected("same-sequence idempotency did not preserve the exact time watermark")
        elif commit.outcome is TrustStateOutcome.TIME_ADVANCED:
            if (
                commit.state_generation != snapshot.state_generation + 1
                or commit.trusted_time_latest_utc != latest
                or snapshot.trusted_time_latest_utc is None
                or latest <= snapshot.trusted_time_latest_utc
            ):
                raise TrustStateRejected("same-sequence time advancement did not commit one generation and the new watermark")
        else:
            raise TrustStateRejected("same-sequence policy returned an unsupported provider outcome")
    else:
        if (
            commit.outcome is not TrustStateOutcome.ADVANCED
            or commit.state_generation != snapshot.state_generation + 1
            or commit.trusted_time_latest_utc != latest
        ):
            raise TrustStateRejected(
                "policy sequence compare-and-advance did not commit exactly one generation and the candidate clock upper bound"
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
    )
