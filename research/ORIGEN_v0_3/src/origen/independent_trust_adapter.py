"""Fail-closed boundary for the not-yet-provisioned independent trust adapter.

No institutional trust roots, controlled artifact store, trusted-time service,
or independent ledger have been provisioned and independently reviewed for
this repository. The adapter therefore has only BLOCKED_PROVENANCE.

The optional V3 context is an in-process consistency handoff, not an
unforgeable capability or an independent trust anchor. It binds the exact
receipt and policy bytes to the exact verifier result objects produced by the
V3 receipt bridge, checks their issuer/key/role/time relationships, and then
still returns BLOCKED_PROVENANCE. Python callers with arbitrary code execution
can fabricate objects; production decisions must never rely on these object
types alone.

Do not replace this gate with caller-supplied booleans, callbacks, key maps,
or reference sets. A future backend must independently provision its roots,
clock and monotonic state, and re-verify original bytes at this boundary.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from enum import Enum

from .trust_policy_envelope_v1 import MAX_POLICY_BYTES
from .trust_policy_envelope_v3 import VerifiedTrustPolicyV3
from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES, UnverifiedTrustReceipt
from .trust_verifier_v1 import (
    CryptographicallyVerifiedReceipt,
    TrustPolicy,
    TrustedIssuerKey,
)

RECEIPT_ATTESTER_ROLE = "RECEIPT-ROOT-ATTESTER"
RECEIPT_ATTESTATION_ARTIFACT_TYPE = "TRUST-RECEIPT-ROOT-ATTESTATION"
CLASSIC_POLICY_DOMAIN = "origen.chispazo.classic.provenance"
_SHA256 = re.compile(r"[0-9a-f]{64}\\Z")


class ProvenanceStatus(str, Enum):
    """Only status this unprovisioned adapter is capable of returning."""

    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"


INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED = (
    "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED"
)


def _require_utc_datetime(value: object, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError(f"{field} must be an exact UTC datetime from a verifier result")
    return value


def _validate_v3_context(
    original_receipt_bytes: bytes,
    signed_policy_envelope_bytes: bytes,
    verified_policy: VerifiedTrustPolicyV3,
    verified_receipt: CryptographicallyVerifiedReceipt,
) -> None:
    """Cross-bind verifier outputs to the exact bytes supplied at this boundary.

    This is deliberately a consistency check only. The result objects are not
    cryptographic capabilities, and this function never changes provenance
    status from BLOCKED_PROVENANCE.
    """
    if type(signed_policy_envelope_bytes) is not bytes:
        raise TypeError("signed_policy_envelope_bytes must be exact bytes")
    if not 1 <= len(signed_policy_envelope_bytes) <= MAX_POLICY_BYTES:
        raise ValueError(
            f"signed_policy_envelope_bytes must contain 1..{MAX_POLICY_BYTES} bytes"
        )
    if type(verified_policy) is not VerifiedTrustPolicyV3:
        raise TypeError("verified_policy must be an exact VerifiedTrustPolicyV3")
    if type(verified_receipt) is not CryptographicallyVerifiedReceipt:
        raise TypeError(
            "verified_receipt must be an exact CryptographicallyVerifiedReceipt"
        )

    receipt = verified_receipt.receipt
    if type(receipt) is not UnverifiedTrustReceipt:
        raise TypeError("verified receipt must contain an exact parsed receipt")
    if receipt.raw_sha256 != hashlib.sha256(original_receipt_bytes).hexdigest():
        raise ValueError("verified receipt does not bind the exact original receipt bytes")
    if not _SHA256.fullmatch(verified_receipt.signed_payload_sha256):
        raise ValueError("verified receipt payload digest is malformed")
    if hashlib.sha256(signed_policy_envelope_bytes).hexdigest() != verified_policy.envelope_sha256:
        raise ValueError("verified policy does not bind the exact signed policy envelope bytes")

    policy = verified_policy.policy
    if type(policy) is not TrustPolicy:
        raise TypeError("verified policy must contain an exact TrustPolicy")
    if type(policy.issuer_keys) is not tuple:
        raise TypeError("verified policy issuer keys must be an exact tuple")
    if verified_policy.policy_domain != CLASSIC_POLICY_DOMAIN:
        raise ValueError("independent provenance V3 context requires the CLASSIC policy domain")
    if policy.policy_version != receipt.policy_version:
        raise ValueError("verified policy version does not match the exact receipt")

    issuer_id = verified_receipt.verified_issuer_id
    key_id = verified_receipt.verified_key_id
    if (
        receipt.attestation.issuer_id != issuer_id
        or receipt.attestation.key_id != key_id
    ):
        raise ValueError("verified receipt identity does not match its signed attestation")

    matches = [
        key for key in policy.issuer_keys
        if type(key) is TrustedIssuerKey
        and key.issuer_id == issuer_id
        and key.key_id == key_id
    ]
    if len(matches) != 1:
        raise ValueError("verified policy does not contain exactly one matching receipt issuer key")
    key = matches[0]
    if key.revoked:
        raise ValueError("verified receipt issuer key is revoked in the verified policy")

    try:
        signed_at = datetime.fromisoformat(
            receipt.attestation.signed_at_utc.replace("Z", "+00:00")
        )
    except (AttributeError, ValueError) as exc:
        raise ValueError("receipt attestation signing time is not parseable") from exc
    verified_at = _require_utc_datetime(
        verified_receipt.verified_at_utc, "verified_receipt.verified_at_utc"
    )
    policy_issued = _require_utc_datetime(
        verified_policy.issued_at_utc, "verified_policy.issued_at_utc"
    )
    policy_not_before = _require_utc_datetime(
        verified_policy.not_before_utc, "verified_policy.not_before_utc"
    )
    policy_expires = _require_utc_datetime(
        verified_policy.expires_at_utc, "verified_policy.expires_at_utc"
    )
    key_from = _require_utc_datetime(key.valid_from_utc, "issuer key valid_from_utc")
    key_until = _require_utc_datetime(key.valid_until_utc, "issuer key valid_until_utc")

    if not (policy_issued <= policy_not_before <= signed_at < policy_expires):
        raise ValueError("receipt signing time is outside the verified policy effective interval")
    if not (policy_not_before <= verified_at < policy_expires):
        raise ValueError("receipt verification time is outside the verified policy effective interval")
    if not (key_from <= signed_at <= key_until and key_from <= verified_at <= key_until):
        raise ValueError("receipt issuer key validity does not cover signing and verification times")

    if type(verified_policy.key_authorizations) is not tuple:
        raise TypeError("verified policy key authorizations must be an exact tuple")
    authorizations = [
        item for item in verified_policy.key_authorizations
        if (
            type(item) is tuple
            and len(item) == 4
            and item[0] == issuer_id
            and item[1] == key_id
            and item[2] == RECEIPT_ATTESTER_ROLE
            and type(item[3]) is tuple
            and RECEIPT_ATTESTATION_ARTIFACT_TYPE in item[3]
        )
    ]
    if len(authorizations) != 1:
        raise ValueError(
            "verified policy does not contain exactly one receipt-attester role/artifact authorization"
        )


def verify_independent_provenance(
    original_receipt_bytes: bytes,
    *,
    signed_policy_envelope_bytes: bytes | None = None,
    verified_policy: VerifiedTrustPolicyV3 | None = None,
    verified_receipt: CryptographicallyVerifiedReceipt | None = None,
) -> ProvenanceStatus:
    """Fail closed until independently provisioned trust infrastructure exists.

    Legacy calls with only original receipt bytes remain accepted and blocked.
    The V3 integration supplies the exact policy envelope plus the policy and
    receipt verifier results. When any V3 context field is supplied, all three
    are mandatory and cross-bound before the backend gate is reached.

    The V3 objects are an in-process diagnostic handoff, not unforgeable
    capabilities. Even a fully consistent handoff returns BLOCKED_PROVENANCE.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(
            f"original_receipt_bytes must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        )

    context_values = (
        signed_policy_envelope_bytes,
        verified_policy,
        verified_receipt,
    )
    if any(value is not None for value in context_values):
        if any(value is None for value in context_values):
            raise ValueError(
                "V3 provenance context requires signed policy bytes, verified policy, and verified receipt together"
            )
        _validate_v3_context(
            original_receipt_bytes,
            signed_policy_envelope_bytes,
            verified_policy,
            verified_receipt,
        )

    return ProvenanceStatus.BLOCKED_PROVENANCE
