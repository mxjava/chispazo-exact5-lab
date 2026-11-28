"""Provider-bound V2 ledger transition preflight.

This adapter obtains trust inputs from one provider snapshot, its physical
trust context and its one-use three-nonce challenge. It performs no CAS and
never upgrades provenance: successful results remain BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    DeploymentTrustProvider,
    TrustProviderUnavailable,
    TrustStateRejected,
    _accepted_external_evidence_watermark_sha256,
    _snapshot_copy,
    _time_window,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_trust_context_v1 import (
    PhysicalTrustContextV1,
    physical_trust_context_sha256,
)
from .timestamp_nonce_challenge_v1 import (
    TimestampNonceChallengeV1,
    copy_timestamp_nonce_challenge,
    timestamp_nonce_challenge_sha256,
)
from .transparency_ledger_bundle_transition_v2 import (
    TransparencyLedgerBundleTransitionInspectionV2,
    verify_transparency_ledger_bundle_transition_v2,
)


CLASSIC_PHYSICAL_POLICY_DOMAIN = "origen.chispazo.classic.physical"


@dataclass(frozen=True, slots=True)
class ProviderBoundLedgerTransitionInspectionV2:
    transition: TransparencyLedgerBundleTransitionInspectionV2
    provider_state_generation: int
    provider_root_generation: int
    accepted_watermark_sha256: str
    physical_trust_context_generation: int
    physical_trust_context_sha256: str
    timestamp_nonce_challenge_id: str
    timestamp_nonce_challenge_sha256: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def _copy_physical_context(value: object) -> PhysicalTrustContextV1:
    if type(value) is not PhysicalTrustContextV1:
        raise TypeError("provider must return an exact PhysicalTrustContextV1")
    return PhysicalTrustContextV1(
        policy_tsa_root_certificate_der=value.policy_tsa_root_certificate_der,
        policy_tsa_root_sha256=value.policy_tsa_root_sha256,
        policy_tsa_policy_oid=value.policy_tsa_policy_oid,
        policy_root_public_key_bytes=value.policy_root_public_key_bytes,
        policy_root_key_id=value.policy_root_key_id,
        minimum_policy_sequence=value.minimum_policy_sequence,
        custody_tsa_root_certificate_der=value.custody_tsa_root_certificate_der,
        custody_tsa_root_sha256=value.custody_tsa_root_sha256,
        log_public_key_bytes=value.log_public_key_bytes,
        log_id=value.log_id,
        log_key_id=value.log_key_id,
        registry_root_public_key_bytes=value.registry_root_public_key_bytes,
        registry_root_key_id=value.registry_root_key_id,
        registry_id=value.registry_id,
        minimum_registry_sequence=value.minimum_registry_sequence,
        minimum_log_tree_size=value.minimum_log_tree_size,
        context_generation=value.context_generation,
        nested_signature_bundle_tsa_root_certificate_der=(
            value.nested_signature_bundle_tsa_root_certificate_der
        ),
        nested_signature_bundle_tsa_root_sha256=(
            value.nested_signature_bundle_tsa_root_sha256
        ),
        nested_signature_bundle_tsa_policy_oid=(
            value.nested_signature_bundle_tsa_policy_oid
        ),
    )


def inspect_provider_bound_transparency_ledger_bundle_transition_v2(
    raw_manifest_bytes: bytes,
    raw_ledger_entry_bytes: bytes,
    raw_inclusion_proof_bytes: bytes,
    raw_old_checkpoint_bytes: bytes,
    raw_signed_checkpoint_bytes: bytes,
    raw_consistency_proof_bytes: bytes,
    raw_timestamp_bundle_bytes: bytes,
    timestamp_token_der: bytes,
    signed_policy_envelope_bytes: bytes,
    artifact_bytes_by_sha256: dict[str, bytes],
    signature_bytes_by_sha256: dict[str, bytes],
    *,
    provider: DeploymentTrustProvider,
) -> ProviderBoundLedgerTransitionInspectionV2:
    """Verify V2 transition against one provider-owned snapshot/context/challenge.

    All pins, floors, old-watermark values, nonce and verification time are
    derived from provider reads; none are accepted as independent request
    arguments. The provider must still repeat every cryptographic check and
    consume the challenge atomically inside its own linearizable CAS.
    """
    read_snapshot = getattr(provider, "read_snapshot", None)
    if not callable(read_snapshot):
        raise TypeError("provider must implement read_snapshot")
    try:
        supplied_snapshot = read_snapshot(policy_domain=CLASSIC_POLICY_DOMAIN)
    except Exception as exc:
        raise TrustProviderUnavailable("deployment trust snapshot could not be read") from exc
    snapshot = _snapshot_copy(supplied_snapshot)

    if snapshot.accepted_external_evidence_watermark is None:
        raise TrustStateRejected(
            "V2 ledger transition requires an independently provisioned accepted watermark"
        )
    if (
        snapshot.physical_trust_context_generation is None
        or snapshot.physical_trust_context_sha256 is None
    ):
        raise TrustStateRejected(
            "V2 ledger transition requires a snapshot-bound physical trust context"
        )

    read_context = getattr(provider, "read_physical_trust_context", None)
    if not callable(read_context):
        raise TrustProviderUnavailable(
            "deployment provider lacks read_physical_trust_context"
        )
    try:
        supplied_context = read_context(policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN)
    except Exception as exc:
        raise TrustProviderUnavailable(
            "provider physical trust context could not be read"
        ) from exc
    context = _copy_physical_context(supplied_context)
    context_digest = physical_trust_context_sha256(context)
    if (
        context.context_generation != snapshot.physical_trust_context_generation
        or context_digest != snapshot.physical_trust_context_sha256
    ):
        raise TrustStateRejected(
            "provider physical trust context does not match the exact snapshot generation and digest"
        )
    if (
        context.policy_root_public_key_bytes != snapshot.root_public_key_bytes
        or context.policy_root_key_id != snapshot.root_key_id
        or context.minimum_policy_sequence != snapshot.minimum_policy_sequence
    ):
        raise TrustStateRejected(
            "physical trust context policy root/key ID/bootstrap floor differs from the deployment snapshot"
        )

    watermark = snapshot.accepted_external_evidence_watermark
    if (
        watermark.policy_domain != snapshot.policy_domain
        or watermark.state_backend_id != snapshot.state_backend_id
        or watermark.log_id != context.log_id
        or watermark.log_key_id != context.log_key_id
        or watermark.log_public_key_sha256
        != hashlib.sha256(context.log_public_key_bytes).hexdigest()
        or watermark.registry_id != context.registry_id
        or watermark.registry_root_key_id != context.registry_root_key_id
        or watermark.registry_root_public_key_sha256
        != hashlib.sha256(context.registry_root_public_key_bytes).hexdigest()
    ):
        raise TrustStateRejected(
            "accepted ledger/witness watermark identity differs from the provider-owned physical trust context"
        )

    if (
        context.nested_signature_bundle_tsa_root_certificate_der is None
        or context.nested_signature_bundle_tsa_root_sha256 is None
        or context.nested_signature_bundle_tsa_policy_oid is None
    ):
        raise TrustStateRejected(
            "V2 ledger transition requires the provider-owned nested-signature bundle TSA pin"
        )

    earliest, latest = _time_window(snapshot)
    if latest > snapshot.clock_sample_valid_until_utc:
        raise TrustStateRejected(
            "trusted-time uncertainty interval exceeds the provider clock sample lease"
        )

    read_challenge = getattr(provider, "read_timestamp_nonce_challenge", None)
    if not callable(read_challenge):
        raise TrustProviderUnavailable(
            "deployment provider lacks read_timestamp_nonce_challenge"
        )
    try:
        supplied_challenge = read_challenge(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            expected_state_backend_id=snapshot.state_backend_id,
            expected_state_generation=snapshot.state_generation,
            expected_root_generation=snapshot.root_generation,
            expected_physical_trust_context_generation=context.context_generation,
            expected_physical_trust_context_sha256=context_digest,
        )
    except Exception as exc:
        raise TrustProviderUnavailable(
            "provider timestamp nonce challenge could not be read"
        ) from exc
    challenge: TimestampNonceChallengeV1 = copy_timestamp_nonce_challenge(
        supplied_challenge
    )
    if (
        challenge.policy_domain != CLASSIC_POLICY_DOMAIN
        or challenge.state_backend_id != snapshot.state_backend_id
        or challenge.state_generation != snapshot.state_generation
        or challenge.root_generation != snapshot.root_generation
        or challenge.physical_trust_context_generation != context.context_generation
        or challenge.physical_trust_context_sha256 != context_digest
    ):
        raise TrustStateRejected(
            "timestamp nonce challenge is not bound to the exact provider snapshot and physical trust context"
        )
    if challenge.nested_signature_bundle_timestamp_nonce is None:
        raise TrustStateRejected(
            "V2 ledger transition requires the provider-issued third timestamp nonce"
        )
    if (
        challenge.issued_at_utc > earliest
        or latest >= challenge.expires_at_utc
        or challenge.expires_at_utc > snapshot.clock_sample_valid_until_utc
    ):
        raise TrustStateRejected(
            "timestamp nonce challenge does not cover the complete provider time interval and clock lease"
        )

    transition = verify_transparency_ledger_bundle_transition_v2(
        raw_manifest_bytes,
        raw_ledger_entry_bytes,
        raw_inclusion_proof_bytes,
        raw_old_checkpoint_bytes,
        raw_signed_checkpoint_bytes,
        raw_consistency_proof_bytes,
        raw_timestamp_bundle_bytes,
        timestamp_token_der,
        signed_policy_envelope_bytes,
        artifact_bytes_by_sha256,
        signature_bytes_by_sha256,
        pinned_log_public_key_bytes=context.log_public_key_bytes,
        expected_log_id=context.log_id,
        expected_log_key_id=context.log_key_id,
        minimum_tree_size=context.minimum_log_tree_size,
        expected_old_tree_size=watermark.ledger_tree_size,
        expected_old_root_sha256=watermark.ledger_root_sha256,
        expected_old_checkpoint_sha256=watermark.ledger_checkpoint_sha256,
        pinned_root_public_key_bytes=snapshot.root_public_key_bytes,
        expected_root_key_id=snapshot.root_key_id,
        minimum_policy_sequence=max(
            snapshot.minimum_policy_sequence,
            snapshot.accepted_policy_sequence,
        ),
        pinned_tsa_root_certificate_der=(
            context.nested_signature_bundle_tsa_root_certificate_der
        ),
        expected_tsa_root_sha256=context.nested_signature_bundle_tsa_root_sha256,
        expected_tsa_policy_oid=context.nested_signature_bundle_tsa_policy_oid,
        expected_nonce=challenge.nested_signature_bundle_timestamp_nonce,
        verification_time=earliest,
    )
    if (
        transition.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE
        or transition.checkpoint_consistency.old_tree_size != watermark.ledger_tree_size
        or transition.checkpoint_consistency.old_root_sha256 != watermark.ledger_root_sha256
        or transition.checkpoint_consistency.old_checkpoint_sha256
        != watermark.ledger_checkpoint_sha256
    ):
        raise RuntimeError(
            "V2 transition verifier did not preserve the exact provider watermark and blocked provenance"
        )

    challenge_digest = timestamp_nonce_challenge_sha256(challenge)
    blockers = tuple(dict.fromkeys(
        (*transition.remaining_blockers,
         "PROVIDER_CAS_NOT_PERFORMED",
         "INSTITUTIONAL_PROVIDER_IMPLEMENTATION_NOT_AUTHENTICATED")
    ))
    return ProviderBoundLedgerTransitionInspectionV2(
        transition=transition,
        provider_state_generation=snapshot.state_generation,
        provider_root_generation=snapshot.root_generation,
        accepted_watermark_sha256=(
            _accepted_external_evidence_watermark_sha256(watermark)
        ),
        physical_trust_context_generation=context.context_generation,
        physical_trust_context_sha256=context_digest,
        timestamp_nonce_challenge_id=challenge.challenge_id,
        timestamp_nonce_challenge_sha256=challenge_digest,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
