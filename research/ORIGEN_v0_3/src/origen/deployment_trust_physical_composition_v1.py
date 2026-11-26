"""Research-only orchestration of physical evidence and provider-backed trust.

One validated deployment-provider snapshot supplies the exact verification
instant to both the physical verifier and the deployment-policy verifier. The
provider's atomic compare-and-advance occurs only after every nested physical
signature, RFC 3161 token, ledger proof and witness batch succeeds. This avoids
consuming monotonic policy state for a physical bundle that fails verification.

Physical trust anchors and anti-rollback floors are obtained from a separate
provider method, never from evidence-submitter keyword arguments. The provider
implementation and its institutional provisioning remain independently
unverified; this composition therefore remains research-only.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from .deployment_trust_provider_v1 import (
    DeploymentTrustInspection,
    DeploymentTrustProvider,
    DeploymentTrustSnapshot,
    _snapshot_copy,
    inspect_receipt_with_deployment_trust_provider,
)
from .independent_trust_adapter import ProvenanceStatus
from .physical_trust_context_v1 import PhysicalTrustContextV1
from .custody_ledger_witness_integration_v1 import (
    CustodyLedgerWitnessInspectionV1,
    verify_custody_timestamp_ledger_witness_v1,
)


@dataclass(frozen=True, slots=True)
class DeploymentBoundPhysicalInspectionV1:
    """Diagnostic join; never an authenticated provenance or eligibility token."""

    physical_inspection: CustodyLedgerWitnessInspectionV1
    deployment_trust_inspection: DeploymentTrustInspection
    receipt_sha256: str
    policy_envelope_sha256: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def verify_custody_timestamp_ledger_witness_with_deployment_trust_provider_v1(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    provider: DeploymentTrustProvider,
    physical_verification_kwargs: dict,
) -> DeploymentBoundPhysicalInspectionV1:
    """Verify the physical bundle, then verify/advance deployment trust.

    `physical_verification_kwargs` contains only evidence bytes, request
    nonces and verification thresholds. All TSA, policy-root, log and
    witness-registry anchors/floors are obtained from the provider's separately
    provisioned PhysicalTrustContextV1. Supplying any trust pin in caller
    kwargs is rejected. The provider snapshot supplies the exact verification
    instant to the physical verifier and is reused by deployment verification.

    The provider must implement read_physical_trust_context in addition to
    read_snapshot. A missing context fails closed before physical verification.
    The provider implementation and institutional provisioning are not
    authenticated by this interface; every successful result remains
    BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes or not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must be non-empty exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes or not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must be non-empty exact bytes")
    if type(physical_verification_kwargs) is not dict:
        raise TypeError("physical_verification_kwargs must be an exact dict")
    if "verification_time" in physical_verification_kwargs:
        supplied_time = physical_verification_kwargs["verification_time"]
        if type(supplied_time) is not datetime or supplied_time.tzinfo is None:
            raise ValueError("caller verification_time, when supplied, must be an aware datetime")
    provider_owned_fields = {
        "pinned_policy_tsa_root_certificate_der",
        "expected_policy_tsa_root_sha256",
        "expected_policy_tsa_policy_oid",
        "pinned_root_public_key_bytes",
        "expected_root_key_id",
        "minimum_policy_sequence",
        "pinned_tsa_root_certificate_der",
        "expected_tsa_root_sha256",
        "pinned_log_public_key_bytes",
        "expected_log_id",
        "expected_log_key_id",
        "pinned_registry_root_public_key_bytes",
        "expected_registry_root_key_id",
        "expected_registry_id",
        "minimum_registry_sequence",
    }
    forbidden = provider_owned_fields.intersection(physical_verification_kwargs)
    if forbidden:
        raise ValueError(
            "caller must not supply physical trust anchors or floors: "
            + ", ".join(sorted(forbidden))
        )
    if any(
        key in physical_verification_kwargs
        for key in ("original_receipt_bytes", "signed_policy_envelope_bytes", "provider")
    ):
        raise ValueError("physical verification kwargs must not override shared trust inputs")

    # Read and validate one provider snapshot. The same trusted instant is
    # injected into physical verification and the exact snapshot is reused by
    # deployment verification. Its final CAS rejects stale/fabricated state.
    read_snapshot = getattr(provider, "read_snapshot", None)
    if not callable(read_snapshot):
        raise TypeError("provider must implement read_snapshot")
    try:
        supplied_snapshot = read_snapshot(
            policy_domain="origen.chispazo.classic.provenance"
        )
    except Exception as exc:
        raise RuntimeError("deployment trust snapshot could not be read") from exc
    snapshot: DeploymentTrustSnapshot = _snapshot_copy(supplied_snapshot)

    read_physical_context = getattr(provider, "read_physical_trust_context", None)
    if not callable(read_physical_context):
        raise RuntimeError("provider lacks independently provisioned physical trust context")
    try:
        supplied_physical_context = read_physical_context(
            policy_domain="origen.chispazo.classic.physical"
        )
    except Exception as exc:
        raise RuntimeError("physical trust context could not be read") from exc
    if type(supplied_physical_context) is not PhysicalTrustContextV1:
        raise TypeError("provider returned an unexpected physical trust context type")
    context = supplied_physical_context

    # Snapshot the keyword mapping so caller mutation cannot change the
    # argument set between the physical and deployment verification stages.
    physical_kwargs = dict(physical_verification_kwargs)
    physical_kwargs.update({
        "pinned_policy_tsa_root_certificate_der": context.policy_tsa_root_certificate_der,
        "expected_policy_tsa_root_sha256": context.policy_tsa_root_sha256,
        "expected_policy_tsa_policy_oid": context.policy_tsa_policy_oid,
        "pinned_root_public_key_bytes": context.policy_root_public_key_bytes,
        "expected_root_key_id": context.policy_root_key_id,
        "minimum_policy_sequence": context.minimum_policy_sequence,
        "pinned_tsa_root_certificate_der": context.custody_tsa_root_certificate_der,
        "expected_tsa_root_sha256": context.custody_tsa_root_sha256,
        "pinned_log_public_key_bytes": context.log_public_key_bytes,
        "expected_log_id": context.log_id,
        "expected_log_key_id": context.log_key_id,
        "pinned_registry_root_public_key_bytes": context.registry_root_public_key_bytes,
        "expected_registry_root_key_id": context.registry_root_key_id,
        "expected_registry_id": context.registry_id,
        "minimum_registry_sequence": context.minimum_registry_sequence,
        "verification_time": snapshot.trusted_time_utc,
    })
    physical = verify_custody_timestamp_ledger_witness_v1(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        **physical_kwargs,
    )
    if type(physical) is not CustodyLedgerWitnessInspectionV1:
        raise TypeError("physical composition returned an unexpected result type")
    if physical.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("physical composition did not preserve BLOCKED_PROVENANCE")

    deployment = inspect_receipt_with_deployment_trust_provider(
        original_receipt_bytes,
        signed_policy_envelope_bytes,
        provider=provider,
        provider_snapshot=snapshot,
    )
    if type(deployment) is not DeploymentTrustInspection:
        raise TypeError("deployment trust verifier returned an unexpected result type")
    if deployment.provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("deployment trust verifier did not preserve BLOCKED_PROVENANCE")

    receipt_digest = hashlib.sha256(original_receipt_bytes).hexdigest()
    policy_digest = hashlib.sha256(signed_policy_envelope_bytes).hexdigest()
    if (
        deployment.receipt_sha256 != receipt_digest
        or deployment.policy_envelope_sha256 != policy_digest
    ):
        raise RuntimeError("deployment trust result does not bind the exact physical-composition bytes")

    blockers = tuple(dict.fromkeys(
        tuple(physical.remaining_blockers)
        + (
            "TSA_ROOT_AND_REVOCATION_NOT_AUTHENTICATED_BY_DEPLOYMENT_PROVIDER",
            "TRANSPARENCY_LOG_ROOT_AND_WITNESS_REGISTRY_NOT_OUT_OF_BAND_PROVISIONED",
            "PHYSICAL_ORIGIN_AND_INDEPENDENT_CUSTODY_NOT_INSTITUTIONALLY_AUTHENTICATED",
            "PRODUCTION_AND_EDGE_ELIGIBILITY_REMAIN_BLOCKED",
        )
    ))
    return DeploymentBoundPhysicalInspectionV1(
        physical_inspection=physical,
        deployment_trust_inspection=deployment,
        receipt_sha256=receipt_digest,
        policy_envelope_sha256=policy_digest,
        provenance_status=ProvenanceStatus.BLOCKED_PROVENANCE,
        remaining_blockers=blockers,
    )
