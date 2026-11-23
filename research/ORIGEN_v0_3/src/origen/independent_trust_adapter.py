"""Fail-closed boundary for the not-yet-provisioned independent trust adapter.

This module deliberately does not authenticate evidence. No institutional trust
roots, controlled artifact store, trusted-time service, or independent ledger
have been provisioned and independently reviewed for this repository. Until
those dependencies exist, every request returns BLOCKED_PROVENANCE.

Do not replace this gate with caller-supplied booleans, callbacks, key maps, or
reference sets. A future implementation must be separately reviewed and must
bind original artifact bytes to independently controlled trust roots.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProvenanceDecision:
    """Non-authenticating fail-closed result; never an eligibility credential."""

    status: str
    authenticated: bool
    failure_codes: tuple[str, ...]


def verify_independent_provenance(original_receipt_bytes: bytes) -> ProvenanceDecision:
    """Fail closed until independent trust infrastructure is actually deployed.

    The bytes argument is accepted only to make the trust boundary explicit.
    This function does not parse claims, trust digests, inspect caller-provided
    references, or invoke a caller-controlled verifier. It cannot return an
    authenticated decision in this implementation.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    return ProvenanceDecision(
        status="BLOCKED_PROVENANCE",
        authenticated=False,
        failure_codes=("INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED",),
    )
