"""Research-only V2 composition of domain-bound policy and receipt signatures.

Even a valid domain-bound policy and receipt signature do not authenticate the
deployment pins or physical provenance. The independent adapter remains the
final fail-closed boundary and is expected to return BLOCKED_PROVENANCE.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from .independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from .trust_policy_envelope_v2 import (
    VerifiedTrustPolicyV2,
    verify_signed_trust_policy_v2,
)
from .trust_verifier_v1 import verify_receipt_attestation


@dataclass(frozen=True, slots=True)
class RootAttestationInspectionV2:
    policy_domain: str
    policy_signature_verified_against_supplied_anchor: bool
    receipt_signature_verified_under_policy: bool
    policy_sequence: int
    policy_root_key_id: str
    policy_envelope_sha256: str
    receipt_sha256: str
    signed_payload_sha256: str
    verified_issuer_id: str
    verified_key_id: str
    verification_time_utc: datetime
    deployment_anchor_source: str
    anti_rollback_source: str
    provenance_status: ProvenanceStatus


def inspect_signed_root_attestation_chain_v2(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    expected_policy_domain: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> RootAttestationInspectionV2:
    """Verify V2 policy and receipt signatures while retaining the kill switch.

    The root key, root key ID, expected policy domain, sequence floor and clock
    are caller-supplied deployment inputs. Their provisioning is not proven
    here. Original policy and receipt bytes are re-verified; pre-built policy
    objects and caller-supplied booleans are not accepted.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")

    verified_policy: VerifiedTrustPolicyV2 = verify_signed_trust_policy_v2(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=expected_policy_domain,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verification_time,
    )
    verified_receipt = verify_receipt_attestation(
        original_receipt_bytes,
        verified_policy.policy,
        verification_time=verification_time,
    )
    provenance_status = verify_independent_provenance(original_receipt_bytes)
    if provenance_status is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("unexpected provenance status; fail-closed invariant violated")

    return RootAttestationInspectionV2(
        policy_domain=verified_policy.policy_domain,
        policy_signature_verified_against_supplied_anchor=True,
        receipt_signature_verified_under_policy=True,
        policy_sequence=verified_policy.policy_sequence,
        policy_root_key_id=verified_policy.root_key_id,
        policy_envelope_sha256=verified_policy.envelope_sha256,
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        signed_payload_sha256=verified_receipt.signed_payload_sha256,
        verified_issuer_id=verified_receipt.verified_issuer_id,
        verified_key_id=verified_receipt.verified_key_id,
        verification_time_utc=verified_receipt.verified_at_utc,
        deployment_anchor_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        anti_rollback_source="CALLER_SUPPLIED_UNAUTHENTICATED",
        provenance_status=provenance_status,
    )
