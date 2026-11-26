"""Research-only composition of deployment trust state with the complete ORIGEN evidence bundle.

The provider snapshot supplies the CLASSIC policy root, minimum sequence,
authenticated-clock claims and anti-rollback state. The exact same immutable
snapshot is used for the entire evidence verification and the final CAS. The
CAS is deliberately delayed until custody, nested signatures, both RFC 3161
paths, ledger continuity and witness observations have all passed.

This module does not authenticate the provider implementation or its
institutional provisioning. TSA, transparency-log and witness-registry pins
remain explicit research inputs. Every successful result remains
BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from .custody_ledger_witness_integration_v1 import (
    CustodyLedgerWitnessInspectionV1,
    verify_custody_timestamp_ledger_witness_v1,
)
from .custody_receipt_verifier_v3 import CUSTODY_SIGNER_ROLE
from .deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    DeploymentTrustInspection,
    DeploymentTrustProvider,
    DeploymentTrustSnapshot,
    TrustProviderUnavailable,
    TrustStateRejected,
    _clock_sample_sha256,
    _require_clock_sample_key_authorized,
    _require_policy_and_receipt_inside_time_window,
    _snapshot_copy,
    _time_window,
    _trust_configuration_sha256,
    inspect_receipt_with_deployment_trust_provider,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from .trust_policy_envelope_v1 import MAX_POLICY_BYTES
from .trust_policy_envelope_v3 import (
    VerifiedTrustPolicyV3,
    verify_signed_trust_policy_v3,
)
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)


PROVIDER_COMPOSITION_BLOCKERS = (
    "DEPLOYMENT_TRUST_PROVIDER_IMPLEMENTATION_AND_PROVISIONING_NOT_AUTHENTICATED_BY_THIS_LIBRARY",
    "TSA_ROOT_REMAINS_CALLER_SUPPLIED_AND_NOT_OUT_OF_BAND_PROVISIONED",
    "TRANSPARENCY_LOG_ROOT_REMAINS_CALLER_SUPPLIED_AND_NOT_OUT_OF_BAND_PROVISIONED",
    "WITNESS_REGISTRY_ROOT_REMAINS_CALLER_SUPPLIED_AND_NOT_OUT_OF_BAND_PROVISIONED",
    "PHYSICAL_ARTIFACT_ORIGIN_AND_INSTITUTIONAL_DELEGATION_NOT_AUTHENTICATED",
    "INDEPENDENT_CUSTODY_AND_PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class DeploymentEvidenceInspectionV1:
    """Combined diagnostic only; never an authenticated capability or eligibility token."""

    deployment_trust: DeploymentTrustInspection
    evidence: CustodyLedgerWitnessInspectionV1
    receipt_sha256: str
    policy_envelope_sha256: str
    policy_sequence: int
    root_key_id: str
    root_generation: int
    trust_configuration_sha256: str
    clock_sample_sha256: str
    trusted_time_earliest_utc: datetime
    trusted_time_latest_utc: datetime
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


class _PinnedSnapshotProvider:
    """Reuse one validated snapshot; delegate only the final atomic CAS."""

    __slots__ = ("_snapshot", "_compare_and_advance")

    def __init__(self, snapshot: DeploymentTrustSnapshot, compare_and_advance):
        self._snapshot = snapshot
        self._compare_and_advance = compare_and_advance

    def read_snapshot(self, *, policy_domain: str) -> DeploymentTrustSnapshot:
        if policy_domain != CLASSIC_POLICY_DOMAIN:
            raise ValueError("pinned provider snapshot is scoped only to CLASSIC")
        return self._snapshot

    def compare_and_advance(self, **kwargs):
        return self._compare_and_advance(**kwargs)


def _require_used_policy_keys_cover_time_window(
    verified_policy: VerifiedTrustPolicyV3,
    raw_manifest_bytes: bytes,
    custody_record_bytes: bytes,
    custodian_key_id: str,
    *,
    earliest: datetime,
    latest: datetime,
) -> None:
    """Require every key used by this bundle to cover the whole clock interval."""
    manifest = parse_unverified_physical_manifest(raw_manifest_bytes)
    pairs = {
        (claim.subject_id, claim.key_id)
        for claim in manifest.signatures
    }

    custody_digest = hashlib.sha256(custody_record_bytes).hexdigest()
    custody_events = [
        event for event in manifest.custody_events
        if event.artifact_sha256 == custody_digest
    ]
    if len(custody_events) != 1:
        raise ValueError(
            "manifest must contain exactly one custody event for the exact custody-record bytes"
        )
    custody_event = custody_events[0]
    if custody_event.custodian_role != CUSTODY_SIGNER_ROLE:
        raise ValueError("exact custody event does not declare the external-custodian role")
    pairs.add((custody_event.custodian_subject_id, custodian_key_id))

    keys = verified_policy.policy.issuer_keys
    if type(keys) is not tuple:
        raise TypeError("verified policy issuer keys must be an exact tuple")
    for issuer_id, key_id in sorted(pairs):
        matches = [
            key for key in keys
            if key.issuer_id == issuer_id and key.key_id == key_id
        ]
        if len(matches) != 1:
            raise ValueError(
                "a physical or custody signer is missing or ambiguous in the root-signed policy"
            )
        key = matches[0]
        if key.revoked:
            raise ValueError("a physical or custody signer key is revoked")
        if not (key.valid_from_utc <= earliest and latest <= key.valid_until_utc):
            raise ValueError(
                "trusted-time uncertainty interval crosses a physical or custody signer key validity boundary"
            )


def inspect_custody_ledger_witness_with_deployment_provider_v1(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    custody_record_bytes: bytes,
    portfolio_bytes: bytes,
    custody_signature_bytes: bytes,
    custodian_key_id: str,
    timestamp_token_der: bytes,
    policy_timestamp_token_der: bytes,
    pinned_policy_tsa_root_certificate_der: bytes,
    expected_policy_tsa_root_sha256: str,
    expected_policy_tsa_policy_oid: str,
    policy_timestamp_expected_nonce: int,
    pinned_tsa_root_certificate_der: bytes,
    expected_tsa_root_sha256: str,
    expected_nonce: int,
    raw_manifest_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    raw_ledger_entry_bytes: bytes,
    raw_inclusion_proof_bytes: bytes,
    raw_old_checkpoint_bytes: bytes,
    raw_new_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    witness_observation_batches: tuple,
    *,
    provider: DeploymentTrustProvider,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    expected_log_key_id: str,
    minimum_new_tree_size: int,
    pinned_registry_root_public_key_bytes: bytes,
    expected_registry_root_key_id: str,
    expected_registry_id: str,
    minimum_registry_sequence: int,
) -> DeploymentEvidenceInspectionV1:
    """Verify a complete Classic evidence bundle against one provider snapshot.

    Root pin, root key ID, policy sequence floor and verification time are
    intentionally absent from the request API. They are obtained from one
    provider snapshot, copied and validated before evidence verification.

    The provider's atomic compare-and-advance is invoked only after the full
    custody/signature/RFC3161/ledger/witness composition succeeds. The exact
    same cached snapshot is then rechecked by the existing provider boundary
    before CAS. A physical-evidence failure therefore cannot advance policy or
    time state.

    TSA, log and witness-registry roots remain caller-supplied research inputs;
    this function does not claim that those trust domains are provisioned.
    """
    if type(original_receipt_bytes) is not bytes or not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must be non-empty exact bytes")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError("original_receipt_bytes exceeds the trust receipt size limit")
    if type(signed_policy_envelope_bytes) is not bytes or not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must be non-empty exact bytes")
    if len(signed_policy_envelope_bytes) > MAX_POLICY_BYTES:
        raise ValueError("signed_policy_envelope_bytes exceeds the trust policy size limit")
    if type(custody_record_bytes) is not bytes:
        raise TypeError("custody_record_bytes must be exact bytes")
    if type(raw_manifest_bytes) is not bytes:
        raise TypeError("raw_manifest_bytes must be exact bytes")

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
        raise ValueError("trusted-time uncertainty interval exceeds the provider clock sample lease")

    effective_floor = max(
        snapshot.minimum_policy_sequence,
        snapshot.accepted_policy_sequence,
    )
    verified_policy = verify_signed_trust_policy_v3(
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

    if (
        snapshot.trusted_time_latest_utc is not None
        and earliest < snapshot.trusted_time_latest_utc
    ):
        raise TrustStateRejected(
            "trusted-time interval regressed behind the persisted time watermark"
        )
    if snapshot.accepted_policy_sequence == verified_policy.policy_sequence:
        if snapshot.accepted_policy_envelope_sha256 != policy_digest:
            raise TrustStateRejected(
                "same policy sequence is already bound to a different envelope digest"
            )

    verified_receipt = verify_receipt_attestation(
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
    _require_used_policy_keys_cover_time_window(
        verified_policy,
        raw_manifest_bytes,
        custody_record_bytes,
        custodian_key_id,
        earliest=earliest,
        latest=latest,
    )

    # No provider state is advanced before this complete evidence chain returns.
    evidence = verify_custody_timestamp_ledger_witness_v1(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        custody_record_bytes,
        portfolio_bytes,
        custody_signature_bytes,
        custodian_key_id,
        timestamp_token_der,
        policy_timestamp_token_der,
        pinned_policy_tsa_root_certificate_der,
        expected_policy_tsa_root_sha256,
        expected_policy_tsa_policy_oid,
        policy_timestamp_expected_nonce,
        snapshot.root_public_key_bytes,
        snapshot.root_key_id,
        effective_floor,
        pinned_tsa_root_certificate_der,
        expected_tsa_root_sha256,
        expected_nonce,
        raw_manifest_bytes,
        artifact_bytes_by_sha256,
        signature_bytes_by_sha256,
        raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes,
        witness_observation_batches,
        pinned_log_public_key_bytes=pinned_log_public_key_bytes,
        expected_log_id=expected_log_id,
        expected_log_key_id=expected_log_key_id,
        minimum_new_tree_size=minimum_new_tree_size,
        pinned_registry_root_public_key_bytes=pinned_registry_root_public_key_bytes,
        expected_registry_root_key_id=expected_registry_root_key_id,
        expected_registry_id=expected_registry_id,
        minimum_registry_sequence=minimum_registry_sequence,
        verification_time=snapshot.trusted_time_utc,
    )
    if type(evidence) is not CustodyLedgerWitnessInspectionV1:
        raise TypeError("evidence composition returned an unexpected result type")
    if (
        type(evidence.provenance_status) is not ProvenanceStatus
        or evidence.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
        or evidence.independent_boundary_status is not ProvenanceStatus.BLOCKED_PROVENANCE
    ):
        raise RuntimeError("complete evidence composition did not preserve BLOCKED_PROVENANCE")
    if (
        evidence.custody_timestamp.custody_chain.policy_envelope_sha256 != policy_digest
        or evidence.custody_timestamp.custody_chain.policy_sequence != verified_policy.policy_sequence
        or evidence.custody_timestamp.custody_chain.verification_time_utc != snapshot.trusted_time_utc
    ):
        raise RuntimeError("complete evidence composition did not consume the provider-verified policy and time")

    # The existing provider boundary repeats root, clock, policy, receipt and
    # independent-gate checks using this exact cached snapshot, then commits.
    # It cannot silently read a second caller-controlled snapshot.
    pinned_provider = _PinnedSnapshotProvider(snapshot, compare_and_advance)
    deployment_trust = inspect_receipt_with_deployment_trust_provider(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        provider=pinned_provider,
    )
    if type(deployment_trust) is not DeploymentTrustInspection:
        raise TypeError("deployment trust boundary returned an unexpected result type")
    if (
        deployment_trust.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
        or deployment_trust.policy_envelope_sha256 != policy_digest
        or deployment_trust.policy_sequence != verified_policy.policy_sequence
        or deployment_trust.root_key_id != snapshot.root_key_id
        or deployment_trust.root_generation != snapshot.root_generation
        or deployment_trust.trust_configuration_sha256 != trust_configuration_digest
        or deployment_trust.clock_sample_sha256 != clock_sample_digest
    ):
        raise RuntimeError("deployment trust commit is not bound to the exact verified evidence snapshot")

    blockers = tuple(dict.fromkeys(
        tuple(evidence.remaining_blockers)
        + PROVIDER_COMPOSITION_BLOCKERS
    ))
    return DeploymentEvidenceInspectionV1(
        deployment_trust=deployment_trust,
        evidence=evidence,
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        policy_envelope_sha256=policy_digest,
        policy_sequence=verified_policy.policy_sequence,
        root_key_id=snapshot.root_key_id,
        root_generation=snapshot.root_generation,
        trust_configuration_sha256=trust_configuration_digest,
        clock_sample_sha256=clock_sample_digest,
        trusted_time_earliest_utc=earliest,
        trusted_time_latest_utc=latest,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
