"""Research-only orchestration of physical evidence and provider-backed trust.

The physical bundle is verified first. Only after every nested signature,
RFC 3161 token, ledger proof and witness batch succeeds does the deployment
provider verify the exact same receipt/policy bytes and atomically advance its
policy/time state. This ordering avoids consuming monotonic policy state for a
physical bundle that fails its own verification.

This is not a production capability: TSA, log and witness-registry pins still
enter through the physical verifier keyword arguments and must be replaced by
independently provisioned trust services before any authentication claim.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from .deployment_trust_provider_v1 import (
    DeploymentTrustInspection,
    DeploymentTrustProvider,
    inspect_receipt_with_deployment_trust_provider,
)
from .independent_trust_adapter import ProvenanceStatus
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

    `physical_verification_kwargs` must contain the named arguments required
    by `verify_custody_timestamp_ledger_witness_v1`, including
    `verification_time`. The exact receipt and policy bytes are supplied
    only once and forwarded unchanged to both verification paths.

    The provider transaction is deliberately last: failed physical evidence
    cannot advance policy sequence or trusted-time state. The physical
    verification instant must equal the midpoint of the provider's signed
    uncertainty interval, so both paths evaluate the same instant.

    Caller-supplied TSA/log/witness pins remain unauthenticated research
    inputs. Every successful result remains BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes or not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must be non-empty exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes or not signed_policy_envelope_bytes:
        raise ValueError("signed_policy_envelope_bytes must be non-empty exact bytes")
    if type(physical_verification_kwargs) is not dict:
        raise TypeError("physical_verification_kwargs must be an exact dict")
    if "verification_time" not in physical_verification_kwargs:
        raise ValueError("physical_verification_kwargs must include verification_time")
    supplied_time = physical_verification_kwargs["verification_time"]
    if type(supplied_time) is not datetime or supplied_time.tzinfo is None:
        raise ValueError("physical verification_time must be an aware datetime")
    if any(
        key in physical_verification_kwargs
        for key in ("original_receipt_bytes", "signed_policy_envelope_bytes", "provider")
    ):
        raise ValueError("physical verification kwargs must not override shared trust inputs")

    # Snapshot the keyword mapping so caller mutation cannot change the
    # argument set between the physical and deployment verification stages.
    physical_kwargs = dict(physical_verification_kwargs)
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
            "PHYSICAL_VERIFIER_CLOCK_IS_CALLER_SUPPLIED_NOT_PROVIDER_SNAPSHOT",
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
