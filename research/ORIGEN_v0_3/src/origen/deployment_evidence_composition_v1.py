"""Single-snapshot, provider-owned composition for the complete ORIGEN evidence bundle.

The deployment snapshot supplies the CLASSIC policy root, sequence/time state,
and a digest/generation binding for the physical trust context. The provider-
owned PhysicalTrustContextV1 supplies TSA, transparency-log and witness-
registry pins/floors. Both objects must agree on the policy root and bootstrap
floor; the context digest/generation is part of the provider CAS configuration.

The full custody / nested-signature / RFC 3161 / ledger / witness chain runs
before the final provider CAS. Every successful result remains
BLOCKED_PROVENANCE. Provider implementation and institutional provisioning
remain external and unauthenticated by this library.
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
    ExternalEvidenceAdvanceV1,
    TrustProviderUnavailable,
    TrustStateRejected,
    _accepted_external_evidence_watermark_sha256,
    _clock_sample_sha256,
    _require_clock_sample_key_authorized,
    _require_policy_and_receipt_inside_time_window,
    _snapshot_copy,
    _time_window,
    _trust_configuration_sha256,
    _validated_external_evidence_watermark,
    _inspect_receipt_with_deployment_trust_provider_snapshot,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from .physical_trust_context_v1 import (
    PhysicalTrustContextV1,
    physical_trust_context_sha256,
)
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
from .timestamp_nonce_challenge_v1 import (
    copy_timestamp_nonce_challenge,
    timestamp_nonce_challenge_sha256,
)


CLASSIC_PHYSICAL_POLICY_DOMAIN = "origen.chispazo.classic.physical"

PROVIDER_COMPOSITION_BLOCKERS = (
    "DEPLOYMENT_TRUST_PROVIDER_IMPLEMENTATION_AND_PROVISIONING_NOT_AUTHENTICATED_BY_THIS_LIBRARY",
    "PROVIDER_ANTI_ROLLBACK_BACKEND_NOT_INDEPENDENTLY_AUTHENTICATED_OR_DEPLOYED",
    "PHYSICAL_TRUST_CONTEXT_IS_PROVIDER_OWNED_BUT_NOT_INSTITUTIONALLY_AUTHENTICATED",
    "POLICY_ENVELOPE_TIMESTAMP_POLICY_OID_NOT_AUTHORIZED_BY_AUTHENTICATED_DEPLOYMENT_POLICY",
    "TSA_CERTIFICATE_CHAINS_AND_CURRENT_REVOCATION_NOT_INDEPENDENTLY_VERIFIED",
    "TRANSPARENCY_LOG_AND_WITNESS_REGISTRY_ROOTS_NOT_INSTITUTIONALLY_AUTHENTICATED",
    "PHYSICAL_ARTIFACT_ORIGIN_AND_INSTITUTIONAL_DELEGATION_NOT_AUTHENTICATED",
    "INDEPENDENT_CUSTODY_AND_PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
    "RFC3161_NONCE_CHALLENGE_ISSUANCE_AND_SINGLE_USE_NOT_INDEPENDENTLY_AUTHENTICATED_OR_DEPLOYED",
)

# The lower-level verifier is intentionally caller-parameterized. In this
# provider composition those values are supplied from the exact provider
# snapshot/context, so its caller-input blockers are no longer accurate.
# Their underlying institutional-authentication limitations remain represented
# by PROVIDER_COMPOSITION_BLOCKERS and the retained revocation/witness blockers.
_PROVIDER_SUPERSEDED_BLOCKERS = frozenset({
    "TSA_ROOT_AND_LOG_ROOT_ARE_CALLER_SUPPLIED_NOT_OUT_OF_BAND_PROVISIONED",
    "WITNESS_REGISTRY_ROOT_IS_CALLER_SUPPLIED_NOT_OUT_OF_BAND_PROVISIONED",
    "ANTI_ROLLBACK_FLOORS_ARE_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_IS_CALLER_SUPPLIED_NOT_AUTHENTICATED",
    "INDEPENDENT_BOUNDARY_RECHECK_STILL_USES_CALLER_SUPPLIED_ROOT_AND_TIME",
    "POLICY_ENVELOPE_TSA_ROOT_NOT_OUT_OF_BAND_PROVISIONED",
    "POLICY_ENVELOPE_TIMESTAMP_EXPECTED_POLICY_OID_IS_CALLER_SUPPLIED",
    "POLICY_ENVELOPE_TIMESTAMP_CLOCK_NOT_AUTHENTICATED",
})


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
    physical_trust_context_sha256: str
    physical_trust_context_generation: int
    timestamp_nonce_challenge_id: str
    timestamp_nonce_challenge_sha256: str
    timestamp_nonce_challenge_generation: int
    trusted_time_earliest_utc: datetime
    trusted_time_latest_utc: datetime
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


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


def _read_physical_trust_context(
    provider: DeploymentTrustProvider,
    snapshot: DeploymentTrustSnapshot,
) -> tuple[PhysicalTrustContextV1, str]:
    read_context = getattr(provider, "read_physical_trust_context", None)
    if not callable(read_context):
        raise TrustProviderUnavailable("deployment provider lacks read_physical_trust_context")
    try:
        supplied = read_context(policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN)
    except Exception as exc:
        raise TrustProviderUnavailable("provider physical trust context could not be read") from exc
    if type(supplied) is not PhysicalTrustContextV1:
        raise TypeError("provider must return an exact PhysicalTrustContextV1")

    # Frozen dataclasses are not immutable against object.__setattr__. Copy every
    # primitive field before hashing or using any trust pin so a provider-side
    # mutation after read cannot change the anchors after digest verification.
    context = PhysicalTrustContextV1(
        policy_tsa_root_certificate_der=supplied.policy_tsa_root_certificate_der,
        policy_tsa_root_sha256=supplied.policy_tsa_root_sha256,
        policy_tsa_policy_oid=supplied.policy_tsa_policy_oid,
        policy_root_public_key_bytes=supplied.policy_root_public_key_bytes,
        policy_root_key_id=supplied.policy_root_key_id,
        minimum_policy_sequence=supplied.minimum_policy_sequence,
        custody_tsa_root_certificate_der=supplied.custody_tsa_root_certificate_der,
        custody_tsa_root_sha256=supplied.custody_tsa_root_sha256,
        log_public_key_bytes=supplied.log_public_key_bytes,
        log_id=supplied.log_id,
        log_key_id=supplied.log_key_id,
        registry_root_public_key_bytes=supplied.registry_root_public_key_bytes,
        registry_root_key_id=supplied.registry_root_key_id,
        registry_id=supplied.registry_id,
        minimum_registry_sequence=supplied.minimum_registry_sequence,
        minimum_log_tree_size=supplied.minimum_log_tree_size,
        context_generation=supplied.context_generation,
        nested_signature_bundle_tsa_root_certificate_der=(
            supplied.nested_signature_bundle_tsa_root_certificate_der
        ),
        nested_signature_bundle_tsa_root_sha256=(
            supplied.nested_signature_bundle_tsa_root_sha256
        ),
        nested_signature_bundle_tsa_policy_oid=(
            supplied.nested_signature_bundle_tsa_policy_oid
        ),
    )
    context_digest = physical_trust_context_sha256(context)
    if (
        snapshot.physical_trust_context_generation is None
        or snapshot.physical_trust_context_sha256 is None
    ):
        raise TrustStateRejected(
            "deployment snapshot does not bind a physical trust context generation and digest"
        )
    if (
        context.context_generation != snapshot.physical_trust_context_generation
        or context_digest != snapshot.physical_trust_context_sha256
    ):
        raise TrustStateRejected(
            "provider physical trust context does not match the snapshot's exact generation and digest"
        )
    if (
        context.policy_root_public_key_bytes != snapshot.root_public_key_bytes
        or context.policy_root_key_id != snapshot.root_key_id
        or context.minimum_policy_sequence != snapshot.minimum_policy_sequence
    ):
        raise TrustStateRejected(
            "physical trust context policy root/key ID/bootstrap floor differs from the deployment snapshot"
        )
    if context.context_generation < 1:
        raise TrustStateRejected("physical trust context generation must be positive")

    return context, context_digest


def _inspect_custody_ledger_witness_with_deployment_provider_v1_using_provider(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    custody_record_bytes: bytes,
    portfolio_bytes: bytes,
    custody_signature_bytes: bytes,
    custodian_key_id: str,
    timestamp_token_der: bytes,
    policy_timestamp_token_der: bytes,
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
) -> DeploymentEvidenceInspectionV1:
    """Verify a complete Classic evidence bundle against one provider context.

    Root pin, root key ID, sequence floor, verification time, policy/custody
    TSA roots, TSA policy OID, log key/IDs/tree floor and registry key/IDs/
    sequence floor are intentionally absent from the request API. They are
    derived from one deployment snapshot and its exactly bound provider-owned
    PhysicalTrustContextV1.

    The physical context must match the snapshot's context digest and
    generation, and its policy root/key ID/bootstrap floor must equal the
    deployment snapshot. The context digest/generation is included in the
    canonical trust-configuration digest that the provider must recompute
    atomically during compare-and-advance.

    The full custody/signature/RFC3161/ledger/witness composition runs before
    provider CAS. Any evidence failure therefore leaves provider state
    untouched. The same cached deployment snapshot is passed to the final
    independent provider boundary; no second snapshot read is permitted.

    Successful results remain BLOCKED_PROVENANCE. The provider implementation,
    physical context provisioning, TSA chain/revocation, institutional draw
    authority and independent custody are not authenticated by this library.
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
    physical_context, physical_context_digest = _read_physical_trust_context(
        provider,
        snapshot,
    )
    accepted_watermark = snapshot.accepted_external_evidence_watermark
    if accepted_watermark is None:
        raise TrustStateRejected(
            "deployment provider has no independently provisioned ledger/witness genesis watermark"
        )
    if (
        accepted_watermark.log_id != physical_context.log_id
        or accepted_watermark.log_key_id != physical_context.log_key_id
        or accepted_watermark.log_public_key_sha256 != hashlib.sha256(physical_context.log_public_key_bytes).hexdigest()
        or accepted_watermark.registry_id != physical_context.registry_id
        or accepted_watermark.registry_root_key_id != physical_context.registry_root_key_id
        or accepted_watermark.registry_root_public_key_sha256 != hashlib.sha256(physical_context.registry_root_public_key_bytes).hexdigest()
    ):
        raise TrustStateRejected(
            "persisted ledger/witness watermark identity differs from the provider-owned physical trust context"
        )
    trust_configuration_digest = _trust_configuration_sha256(snapshot)
    clock_sample_digest = _clock_sample_sha256(snapshot)
    earliest, latest = _time_window(snapshot)
    if latest > snapshot.clock_sample_valid_until_utc:
        raise ValueError("trusted-time uncertainty interval exceeds the provider clock sample lease")

    read_nonce_challenge = getattr(provider, "read_timestamp_nonce_challenge", None)
    if not callable(read_nonce_challenge):
        raise TrustProviderUnavailable("deployment provider lacks read_timestamp_nonce_challenge")
    try:
        supplied_nonce_challenge = read_nonce_challenge(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            expected_state_backend_id=snapshot.state_backend_id,
            expected_state_generation=snapshot.state_generation,
            expected_root_generation=snapshot.root_generation,
            expected_physical_trust_context_generation=physical_context.context_generation,
            expected_physical_trust_context_sha256=physical_context_digest,
        )
    except Exception as exc:
        raise TrustProviderUnavailable("provider timestamp nonce challenge could not be read") from exc
    nonce_challenge = copy_timestamp_nonce_challenge(supplied_nonce_challenge)
    if (
        nonce_challenge.policy_domain != CLASSIC_POLICY_DOMAIN
        or nonce_challenge.state_backend_id != snapshot.state_backend_id
        or nonce_challenge.state_generation != snapshot.state_generation
        or nonce_challenge.root_generation != snapshot.root_generation
        or nonce_challenge.physical_trust_context_generation != physical_context.context_generation
        or nonce_challenge.physical_trust_context_sha256 != physical_context_digest
    ):
        raise TrustStateRejected("timestamp nonce challenge is not bound to the exact provider snapshot and physical trust context")
    if (
        nonce_challenge.issued_at_utc > earliest
        or latest >= nonce_challenge.expires_at_utc
        or nonce_challenge.expires_at_utc > snapshot.clock_sample_valid_until_utc
    ):
        raise TrustStateRejected("timestamp nonce challenge is outside the complete trusted-time interval or clock lease")
    nonce_challenge_digest = timestamp_nonce_challenge_sha256(nonce_challenge)

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

    evidence = verify_custody_timestamp_ledger_witness_v1(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        custody_record_bytes,
        portfolio_bytes,
        custody_signature_bytes,
        custodian_key_id,
        timestamp_token_der,
        policy_timestamp_token_der,
        physical_context.policy_tsa_root_certificate_der,
        physical_context.policy_tsa_root_sha256,
        physical_context.policy_tsa_policy_oid,
        nonce_challenge.policy_timestamp_nonce,
        snapshot.root_public_key_bytes,
        snapshot.root_key_id,
        effective_floor,
        physical_context.custody_tsa_root_certificate_der,
        physical_context.custody_tsa_root_sha256,
        nonce_challenge.custody_timestamp_nonce,
        raw_manifest_bytes,
        artifact_bytes_by_sha256,
        signature_bytes_by_sha256,
        raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes,
        witness_observation_batches,
        pinned_log_public_key_bytes=physical_context.log_public_key_bytes,
        expected_log_id=physical_context.log_id,
        expected_log_key_id=physical_context.log_key_id,
        minimum_new_tree_size=physical_context.minimum_log_tree_size,
        pinned_registry_root_public_key_bytes=physical_context.registry_root_public_key_bytes,
        expected_registry_root_key_id=physical_context.registry_root_key_id,
        expected_registry_id=physical_context.registry_id,
        minimum_registry_sequence=physical_context.minimum_registry_sequence,
        # Use the earliest possible provider time for timestamp-token checks.
        # The midpoint alone could accept an accuracy interval extending into
        # the provider's own clock uncertainty window.
        verification_time=earliest,
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
        or evidence.custody_timestamp.custody_chain.verification_time_utc != earliest
    ):
        raise RuntimeError("complete evidence composition did not consume the provider-verified policy and time")

    registry_digests = {
        hashlib.sha256(batch.raw_registry_bytes).hexdigest()
        for batch in witness_observation_batches
    }
    if len(registry_digests) != 1 or len(evidence.witness_gossip.registry_sequences) != 1:
        raise TrustStateRejected(
            "verified witness batches do not expose one exact signed registry sequence and byte digest"
        )
    continuity = evidence.ledger.checkpoint_consistency
    external_evidence_advance = ExternalEvidenceAdvanceV1(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id=snapshot.state_backend_id,
        log_id=continuity.log_id,
        log_key_id=continuity.key_id,
        log_public_key_sha256=hashlib.sha256(physical_context.log_public_key_bytes).hexdigest(),
        old_tree_size=continuity.old_tree_size,
        old_root_sha256=continuity.old_root_sha256,
        old_checkpoint_sha256=continuity.old_checkpoint_sha256,
        new_tree_size=continuity.new_tree_size,
        new_root_sha256=continuity.new_root_sha256,
        new_checkpoint_sha256=continuity.new_checkpoint_sha256,
        registry_id=physical_context.registry_id,
        registry_root_key_id=physical_context.registry_root_key_id,
        registry_root_public_key_sha256=hashlib.sha256(physical_context.registry_root_public_key_bytes).hexdigest(),
        registry_sequence=evidence.witness_gossip.registry_sequences[0],
        registry_sha256=next(iter(registry_digests)),
        raw_manifest_bytes=raw_manifest_bytes,
        raw_ledger_entry_bytes=raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes=raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes=raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes=raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes=raw_consistency_proof_bytes,
        raw_registry_bytes=witness_observation_batches[0].raw_registry_bytes,
        raw_witness_statement_bytes=tuple(
            statement
            for batch in witness_observation_batches
            for statement in batch.raw_witness_statement_bytes
        ),
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        policy_envelope_sha256=policy_digest,
        raw_receipt_bytes=original_receipt_bytes,
        raw_policy_envelope_bytes=signed_policy_envelope_bytes,
        raw_custody_record_bytes=custody_record_bytes,
        raw_portfolio_bytes=portfolio_bytes,
        raw_custody_signature_bytes=custody_signature_bytes,
        custodian_key_id=custodian_key_id,
        raw_timestamp_token_der=timestamp_token_der,
        raw_policy_timestamp_token_der=policy_timestamp_token_der,
        raw_artifact_bytes_by_sha256=tuple(sorted(artifact_bytes_by_sha256.items())),
        raw_signature_bytes_by_sha256=tuple(sorted(signature_bytes_by_sha256.items())),
    )
    _validated_external_evidence_watermark(
        snapshot,
        _accepted_external_evidence_watermark_sha256(accepted_watermark),
        external_evidence_advance,
    )

    # The provider boundary re-verifies exact policy/receipt bytes and performs
    # one atomic CAS for policy, clock, nonce consumption and external evidence
    # watermarks against the same snapshot. The trust-configuration digest
    # includes the physical-context digest and generation checked above.
    deployment_trust = _inspect_receipt_with_deployment_trust_provider_snapshot(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        provider=provider,
        provider_snapshot=snapshot,
        timestamp_nonce_challenge_id=nonce_challenge.challenge_id,
        timestamp_nonce_challenge_sha256=nonce_challenge_digest,
        external_evidence_advance=external_evidence_advance,
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
        or deployment_trust.timestamp_nonce_challenge_id != nonce_challenge.challenge_id
        or deployment_trust.timestamp_nonce_challenge_sha256 != nonce_challenge_digest
    ):
        raise RuntimeError("deployment trust commit is not bound to the exact verified snapshot")

    blockers = tuple(dict.fromkeys(
        tuple(
            blocker for blocker in evidence.remaining_blockers
            if blocker not in _PROVIDER_SUPERSEDED_BLOCKERS
        )
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
        physical_trust_context_sha256=physical_context_digest,
        physical_trust_context_generation=physical_context.context_generation,
        timestamp_nonce_challenge_id=nonce_challenge.challenge_id,
        timestamp_nonce_challenge_sha256=nonce_challenge_digest,
        timestamp_nonce_challenge_generation=nonce_challenge.state_generation,
        trusted_time_earliest_utc=earliest,
        trusted_time_latest_utc=latest,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
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
    raw_manifest_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    raw_ledger_entry_bytes: bytes,
    raw_inclusion_proof_bytes: bytes,
    raw_old_checkpoint_bytes: bytes,
    raw_new_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    witness_observation_batches: tuple,
) -> DeploymentEvidenceInspectionV1:

    """Public fail-closed facade; provider resolution is deployment-owned."""
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
    return _inspect_custody_ledger_witness_with_deployment_provider_v1_using_provider(
        original_receipt_bytes=original_receipt_bytes,
        signed_policy_envelope_bytes=signed_policy_envelope_bytes,
        custody_record_bytes=custody_record_bytes,
        portfolio_bytes=portfolio_bytes,
        custody_signature_bytes=custody_signature_bytes,
        custodian_key_id=custodian_key_id,
        timestamp_token_der=timestamp_token_der,
        policy_timestamp_token_der=policy_timestamp_token_der,
        raw_manifest_bytes=raw_manifest_bytes,
        artifact_bytes_by_sha256=artifact_bytes_by_sha256,
        signature_bytes_by_sha256=signature_bytes_by_sha256,
        raw_ledger_entry_bytes=raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes=raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes=raw_old_checkpoint_bytes,
        raw_new_checkpoint_bytes=raw_new_checkpoint_bytes,
        raw_consistency_proof_bytes=raw_consistency_proof_bytes,
        witness_observation_batches=witness_observation_batches,
        provider=provider,
    )
