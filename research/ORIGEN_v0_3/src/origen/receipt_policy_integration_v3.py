"""Research-only bridge from a V3 signed policy to receipt root attestation.

This composes cryptographic checks but deliberately cannot authenticate
institutional provenance: root pins, sequence floor and initial time remain
caller supplied, and verify_independent_provenance remains fail-closed.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from .independent_trust_adapter import ProvenanceStatus, verify_independent_provenance
from .physical_evidence_verifier_v2 import (
    CLASSIC_PHYSICAL_POLICY_DOMAIN,
    _utc_instant,
)
from .trust_policy_envelope_v3 import (
    VerifiedTrustPolicyV3,
    verify_signed_trust_policy_v3,
)
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    verify_receipt_attestation,
)

RECEIPT_ATTESTER_ROLE = "RECEIPT-ROOT-ATTESTER"
RECEIPT_ATTESTATION_ARTIFACT_TYPE = "TRUST-RECEIPT-ROOT-ATTESTATION"
RECEIPT_ROLE_STATUS = "SIGNED_POLICY_MATCH_ONLY_NOT_INSTITUTIONALLY_AUTHENTICATED"

RECEIPT_REMAINING_BLOCKERS = (
    "DEPLOYMENT_ROOT_ANCHOR_PROVISIONING_UNVERIFIED",
    "ANTI_ROLLBACK_FLOOR_NOT_BACKED_BY_EXTERNAL_MONOTONIC_STATE",
    "VERIFICATION_CLOCK_NOT_AUTHENTICATED",
    "SIGNED_POLICY_ENVELOPE_EXISTENCE_TIME_NOT_INDEPENDENTLY_AUTHENTICATED",
    "RECEIPT_ATTESTER_IDENTITY_AND_INSTITUTIONAL_DELEGATION_NOT_AUTHENTICATED",
    "RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED",
    "EXTERNAL_LEDGER_INCLUSION_AND_HEAD_NOT_VERIFIED",
    "NESTED_PHYSICAL_SIGNER_ROLES_AND_SIGNATURES_NOT_VERIFIED",
    "CUSTODY_RECEIPT_SIGNATURES_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED",
    "PHYSICAL_ARTIFACT_SEMANTICS_AND_INDEPENDENT_CUSTODY_NOT_VERIFIED",
    "PROSPECTIVE_EDGE_CRITERIA_NOT_MET",
)


@dataclass(frozen=True, slots=True)
class ReceiptPolicyInspectionV3:
    """Diagnostic result only; not a capability and never an eligibility decision."""

    receipt_sha256: str
    policy_envelope_sha256: str
    policy_domain: str
    policy_sequence: int
    policy_issued_at_utc: datetime
    policy_not_before_utc: datetime
    policy_expires_at_utc: datetime
    verification_time_utc: datetime
    verified_issuer_id: str
    verified_key_id: str
    signed_payload_sha256: str
    root_attestation_signature_verified: bool
    role_authorization_status: str
    provenance_status: ProvenanceStatus
    remaining_blockers: tuple[str, ...]


def verify_receipt_attestation_with_policy_v3(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> ReceiptPolicyInspectionV3:
    """Verify a receipt root signature and its signed V3 role authorization.

    The function requires the fixed CLASSIC provenance domain. It normalizes
    the caller-supplied datetime exactly once and passes that UTC instant to
    both policy and receipt verifiers. This prevents inconsistent interpretation
    by a stateful tzinfo; it does NOT authenticate the clock.

    A successful root signature plus role match is only a cryptographic match
    relative to caller-supplied trust inputs. The independent provenance gate
    is called on the original receipt bytes and must remain BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")

    verified_at = _utc_instant(verification_time, "verification_time")
    policy: VerifiedTrustPolicyV3 = verify_signed_trust_policy_v3(
        signed_policy_envelope_bytes,
        pinned_root_public_key_bytes=pinned_root_public_key_bytes,
        expected_root_key_id=expected_root_key_id,
        expected_policy_domain=CLASSIC_PHYSICAL_POLICY_DOMAIN,
        minimum_policy_sequence=minimum_policy_sequence,
        verification_time=verified_at,
    )
    if type(policy) is not VerifiedTrustPolicyV3:
        raise TypeError("policy verifier returned an unexpected result type")
    if policy.policy_domain != CLASSIC_PHYSICAL_POLICY_DOMAIN:
        raise ValueError("receipt V3 integration requires the fixed CLASSIC provenance domain")
    receipt: CryptographicallyVerifiedReceipt = verify_receipt_attestation(
        original_receipt_bytes,
        policy.policy,
        verification_time=verified_at,
    )
    if type(receipt) is not CryptographicallyVerifiedReceipt:
        raise TypeError("receipt verifier returned an unexpected result type")

    # The root-signed role authorization must already be effective when the
    # receipt attestation claims to have been signed; a policy issued later
    # cannot retroactively authorize an earlier signature.
    try:
        receipt_signed_at = datetime.fromisoformat(
            receipt.receipt.attestation.signed_at_utc.replace("Z", "+00:00")
        )
    except (AttributeError, ValueError) as exc:
        raise ValueError("receipt attestation signing time is not parseable") from exc
    if not (policy.not_before_utc <= receipt_signed_at < policy.expires_at_utc):
        raise ValueError(
            "receipt root attestation signing time is outside the signed V3 policy validity interval"
        )

    authorized = False
    if type(policy.key_authorizations) is not tuple:
        raise ValueError("verified policy authorizations must be an exact tuple")
    for item in policy.key_authorizations:
        if (
            type(item) is tuple
            and len(item) == 4
            and type(item[0]) is str
            and type(item[1]) is str
            and type(item[2]) is str
            and type(item[3]) is tuple
            and all(type(value) is str for value in item[3])
            and item[0] == receipt.verified_issuer_id
            and item[1] == receipt.verified_key_id
            and item[2] == RECEIPT_ATTESTER_ROLE
            and RECEIPT_ATTESTATION_ARTIFACT_TYPE in item[3]
        ):
            authorized = True
            break
    if not authorized:
        raise ValueError(
            "receipt root issuer/key is not authorized by the signed V3 policy "
            "for RECEIPT-ROOT-ATTESTER and TRUST-RECEIPT-ROOT-ATTESTATION"
        )

    provenance = verify_independent_provenance(
        original_receipt_bytes,
        signed_policy_envelope_bytes=signed_policy_envelope_bytes,
        verified_policy=policy,
        verified_receipt=receipt,
    )
    if type(provenance) is not ProvenanceStatus:
        raise TypeError("independent provenance gate returned an unexpected status type")
    if provenance is not ProvenanceStatus.BLOCKED_PROVENANCE:
        raise RuntimeError("independent provenance gate returned an unsupported non-blocked status")

    return ReceiptPolicyInspectionV3(
        receipt_sha256=hashlib.sha256(original_receipt_bytes).hexdigest(),
        policy_envelope_sha256=policy.envelope_sha256,
        policy_domain=policy.policy_domain,
        policy_sequence=policy.policy_sequence,
        policy_issued_at_utc=policy.issued_at_utc,
        policy_not_before_utc=policy.not_before_utc,
        policy_expires_at_utc=policy.expires_at_utc,
        verification_time_utc=verified_at,
        verified_issuer_id=receipt.verified_issuer_id,
        verified_key_id=receipt.verified_key_id,
        signed_payload_sha256=receipt.signed_payload_sha256,
        root_attestation_signature_verified=True,
        role_authorization_status=RECEIPT_ROLE_STATUS,
        provenance_status=provenance,
        remaining_blockers=RECEIPT_REMAINING_BLOCKERS,
    )
