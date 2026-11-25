"""Fail-closed boundary for the not-yet-provisioned independent trust adapter.

No institutional trust roots, controlled artifact store, trusted-time service,
or independent ledger have been provisioned and independently reviewed for
this repository. The research-only trust_chain_v1 module can compose a signed
policy envelope with a root-attested receipt, but that verifies only two
cryptographic links relative to caller-supplied inputs. It does not establish
authentic provisioning or verify nested evidence, trusted time, ledger inclusion,
or custody. This adapter deliberately does not consume that result.

Until the complete independent backend exists, every request returns the
single non-authenticating BLOCKED_PROVENANCE enum value.

Do not replace this gate with caller-supplied booleans, callbacks, key maps,
verified-policy objects, verification-result objects, or reference sets. A
future implementation must be separately reviewed and bind original artifact
bytes to independently controlled trust roots.
"""
from __future__ import annotations

from enum import Enum

from .trust_receipt_v1 import MAX_TRUST_RECEIPT_BYTES


class ProvenanceStatus(str, Enum):
    """Only status this unprovisioned adapter is capable of returning."""

    BLOCKED_PROVENANCE = "BLOCKED_PROVENANCE"


INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED = (
    "INDEPENDENT_TRUST_BACKEND_NOT_PROVISIONED"
)


def verify_independent_provenance(original_receipt_bytes: bytes) -> ProvenanceStatus:
    """Fail closed until independent trust infrastructure is deployed.

    The input limit is shared with the strict receipt parser so oversized
    documents cannot cross this public boundary if a backend is provisioned
    later. This function still does not parse claims, trust digests, inspect
    caller-provided references, or invoke caller-controlled verifiers.

    Its return type has no AUTHENTICATED member, so this module cannot issue
    an authenticated status.
    """
    if type(original_receipt_bytes) is not bytes:
        raise TypeError("original_receipt_bytes must be exact bytes")
    if not original_receipt_bytes:
        raise ValueError("original_receipt_bytes must not be empty")
    if len(original_receipt_bytes) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(
            f"original_receipt_bytes must not exceed {MAX_TRUST_RECEIPT_BYTES} bytes"
        )
    return ProvenanceStatus.BLOCKED_PROVENANCE
