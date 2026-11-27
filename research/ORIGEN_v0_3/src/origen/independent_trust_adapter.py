"""Fail-closed composition of signed trust policy and receipt attestation.

This adapter can verify a policy envelope upstream and then verify the receipt's
root Ed25519 attestation against that policy. That is only one cryptographic
layer. It does not authenticate policy-anchor provisioning, trusted time,
nested signer/custodian signatures, RFC 3161 tokens, ledger inclusion, artifact
bytes, physical evidence, or independent custody. It therefore ALWAYS returns
BLOCKED_PROVENANCE, even when the root receipt signature verifies.

No institutional trust roots, protected anti-rollback store, trusted-time
service, controlled artifact store, or independent ledger have been provisioned
and independently reviewed for this repository. Do not replace this gate with
caller-supplied booleans, callbacks, key maps, or reference sets.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from .trust_policy_envelope_v1 import VerifiedTrustPolicy
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES
from .trust_verifier_v1 import verify_receipt_attestation


class ProvenanceStatus(str, Enum):
    """Only status this unprovisioned adapter is capable of returning."""

    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"


INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED = (
    "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED"
)


def verify_independent_provenance(
    original_receipt_bytes: bytes,
    *,
    verified_trust_policy: VerifiedTrustPolicy | None = None,
    verification_time: datetime | None = None,
) -> ProvenanceStatus:
    """Verify one root-attestation layer when supplied a verified policy, then block.

    verified_trust_policy must be the result of verify_signed_trust_policy
    after the deployment has supplied its pinned root key, root key ID, minimum
    anti-rollback sequence, and verification clock. Those inputs remain
    caller/deployment supplied and are NOT authenticated by this adapter.

    verification_time is also caller supplied, not trusted time. The policy's
    issue/not-before/expiry interval is rechecked at this instant before the
    receipt attestation is accepted as a cryptographic sub-result.

    A valid policy and receipt signature are necessary but insufficient for
    provenance. This function deliberately has no AUTHENTICATED result and
    always returns BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(
            f"original_receipt_bytes must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        )

    if verified_trust_policy is None and verification_time is None:
        return ProvenanceStatus.BLOCKED_PROVENANCE
    if verified_trust_policy is None or verification_time is None:
        raise ValueError(
            "verified_trust_policy and verification_time must be supplied together"
        )
    if type(verified_trust_policy) is not VerifiedTrustPolicy:
        raise TypeError(
            "verified_trust_policy must be an exact VerifiedTrustPolicy "
            "from verify_signed_trust_policy"
        )

    verified_receipt = verify_receipt_attestation(
        original_receipt_bytes,
        verified_trust_policy.policy,
        verification_time=verification_time,
    )
    verified_at = verified_receipt.verified_at_utc
    if not (
        verified_trust_policy.issued_at_utc
        <= verified_at
        and verified_trust_policy.not_before_utc
        <= verified_at
        < verified_trust_policy.expires_at_utc
    ):
        raise ValueError(
            "verified trust policy is not valid at receipt verification time"
        )

    # A later verification time must not retroactively authorize a receipt
    # signed before the policy's effective interval began.
    signed_at = datetime.fromisoformat(
        verified_receipt.receipt.attestation.signed_at_utc.replace("Z", "+00:00")
    )
    if not (
        verified_trust_policy.not_before_utc
        <= signed_at
        < verified_trust_policy.expires_at_utc
    ):
        raise ValueError(
            "verified trust policy was not effective at receipt signing time"
        )

    # The root signature is only one layer. No status upgrade is permitted until
    # independent provisioning, trusted time, nested signatures, TSA, ledger,
    # artifact-byte verification, and custody checks are implemented and audited.
    return ProvenanceStatus.BLOCKED_PROVENANCE
