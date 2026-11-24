"""Low-level Ed25519 primitive for the future independent trust verifier.

This module verifies a signature over exact bytes against an explicitly supplied
raw public key. It does NOT establish that the key belongs to an institution,
is authorized, unrevoked, independent, or trusted. Never use this primitive
alone to authenticate provenance or to promote eligibility.
"""
from __future__ import annotations

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


def verify_ed25519_signature_bytes(
    public_key_raw: bytes,
    message: bytes,
    signature: bytes,
) -> bool:
    """Return True only for a valid Ed25519 signature over the exact message.

    Malformed key/signature lengths and invalid signatures fail closed. Inputs
    must be exact immutable bytes to avoid accepting mutable/view-backed data.
    Key trust, role authorization, revocation, timestamping and custody are
    intentionally outside this primitive.
    """
    if type(public_key_raw) is not bytes:
        raise TypeError("public_key_raw must be exact bytes")
    if type(message) is not bytes:
        raise TypeError("message must be exact bytes")
    if type(signature) is not bytes:
        raise TypeError("signature must be exact bytes")
    if len(public_key_raw) != 32 or len(signature) != 64:
        return False
    try:
        key = Ed25519PublicKey.from_public_bytes(public_key_raw)
        key.verify(signature, message)
    except (InvalidSignature, ValueError):
        return False
    return True
