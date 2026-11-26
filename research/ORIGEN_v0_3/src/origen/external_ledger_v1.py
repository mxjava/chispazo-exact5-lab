"""Research-only RFC 6962-style external ledger proof verifier.

This verifies a signed tree head and a Merkle inclusion proof against a
deployment-pinned Ed25519 log key. It does NOT persist anti-rollback state,
authenticate the log operator, prove log completeness, or establish custody.
All trust inputs must eventually come from a separately provisioned deployment
boundary. Synthetic test keys are never deployment trust anchors.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_TREE_SIZE = (1 << 63) - 1
_MAX_PROOF_NODES = 64
_STH_DOMAIN = b"ORIGEN_EXTERNAL_LEDGER_STH_V1\n"


@dataclass(frozen=True, slots=True)
class VerifiedLedgerInclusion:
    """A verified inclusion fact, not a persistent or unforgeable capability."""

    log_id: str
    tree_size: int
    leaf_index: int
    root_hash: str
    signed_tree_head_sha256: str


def _canonical_json(value: dict) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _hash_leaf(leaf_bytes: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + leaf_bytes).digest()


def _hash_node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _verify_inclusion_path(
    leaf_hash: bytes, leaf_index: int, tree_size: int, audit_path: tuple[bytes, ...]
) -> bytes:
    """Verify an RFC 6962 inclusion path and return its calculated root."""
    if type(leaf_hash) is not bytes or len(leaf_hash) != 32:
        raise ValueError("leaf_hash must be exactly 32 bytes")
    if type(leaf_index) is not int or type(tree_size) is not int:
        raise ValueError("leaf_index and tree_size must be exact integers")
    if tree_size < 1 or tree_size > _MAX_TREE_SIZE:
        raise ValueError("tree_size is outside supported bounds")
    if leaf_index < 0 or leaf_index >= tree_size:
        raise ValueError("leaf_index must identify a leaf inside the tree")
    if type(audit_path) is not tuple or len(audit_path) > _MAX_PROOF_NODES:
        raise ValueError("audit_path must be a bounded exact tuple")
    if any(type(node) is not bytes or len(node) != 32 for node in audit_path):
        raise ValueError("every audit path node must be exactly 32 immutable bytes")

    fn = leaf_index
    sn = tree_size - 1
    root = leaf_hash
    for sibling in audit_path:
        if fn & 1 or fn == sn:
            root = _hash_node(sibling, root)
            while fn and not (fn & 1):
                fn >>= 1
                sn >>= 1
        else:
            root = _hash_node(root, sibling)
        fn >>= 1
        sn >>= 1
    if sn != 0:
        raise ValueError("audit path length is inconsistent with tree size")
    return root


def verify_external_ledger_inclusion(
    *,
    leaf_bytes: bytes,
    log_id: str,
    tree_size: int,
    leaf_index: int,
    audit_path_hex: tuple[str, ...],
    signed_tree_head: bytes,
    pinned_log_public_key_bytes: bytes,
    expected_log_id: str,
    minimum_tree_size: int,
) -> VerifiedLedgerInclusion:
    """Verify exact leaf inclusion under an externally pinned log key.

    The caller must obtain the public key, expected log ID and minimum tree
    size from an independent deployment trust store. Passing caller-controlled
    values is suitable only for isolated tests and MUST NOT authorize provenance.
    """
    if type(leaf_bytes) is not bytes or not leaf_bytes:
        raise ValueError("leaf_bytes must be non-empty exact bytes")
    if type(log_id) is not str or not log_id or log_id != expected_log_id:
        raise ValueError("ledger log identity does not match external pin")
    if type(expected_log_id) is not str or not expected_log_id:
        raise ValueError("expected_log_id must be a non-empty exact string")
    if type(minimum_tree_size) is not int or not 1 <= minimum_tree_size <= _MAX_TREE_SIZE:
        raise ValueError("minimum_tree_size must be a positive exact integer")
    if type(tree_size) is not int or tree_size < minimum_tree_size:
        raise ValueError("ledger tree size is below externally pinned minimum")
    if type(pinned_log_public_key_bytes) is not bytes or len(pinned_log_public_key_bytes) != 32:
        raise ValueError("pinned log public key must be exactly 32 immutable bytes")
    if type(signed_tree_head) is not bytes or not signed_tree_head:
        raise ValueError("signed_tree_head must be non-empty exact bytes")
    if type(audit_path_hex) is not tuple or len(audit_path_hex) > _MAX_PROOF_NODES:
        raise ValueError("audit_path_hex must be a bounded exact tuple")

    try:
        document = json.loads(signed_tree_head.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("signed tree head is not valid UTF-8 JSON") from exc
    if type(document) is not dict or set(document) != {
        "schema", "log_id", "tree_size", "root_hash", "signature_b64"
    }:
        raise ValueError("signed tree head fields do not match exact schema")
    if type(document["schema"]) is not str or document["schema"] != "ORIGEN_STH_V1":
        raise ValueError("unsupported signed tree head schema")
    if type(document["log_id"]) is not str or document["log_id"] != expected_log_id:
        raise ValueError("signed tree head log identity mismatch")
    if type(document["tree_size"]) is not int or document["tree_size"] != tree_size:
        raise ValueError("signed tree head tree size mismatch")
    root_hex = document["root_hash"]
    if type(root_hex) is not str or not _HEX64.fullmatch(root_hex):
        raise ValueError("signed tree head root_hash must be lowercase SHA-256 hex")
    signature_b64 = document["signature_b64"]
    if type(signature_b64) is not str:
        raise ValueError("signed tree head signature must be a string")
    import base64
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise ValueError("signed tree head signature is invalid base64") from exc
    if len(signature) != 64:
        raise ValueError("Ed25519 signed tree head signature must be 64 bytes")

    unsigned = {key: value for key, value in document.items() if key != "signature_b64"}
    payload = _STH_DOMAIN + _canonical_json(unsigned)
    try:
        Ed25519PublicKey.from_public_bytes(pinned_log_public_key_bytes).verify(
            signature, payload
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("signed tree head signature verification failed") from exc

    path = []
    for index, item in enumerate(audit_path_hex):
        if type(item) is not str or not _HEX64.fullmatch(item):
            raise ValueError(f"audit_path_hex[{index}] must be lowercase SHA-256 hex")
        path.append(bytes.fromhex(item))
    calculated_root = _verify_inclusion_path(
        _hash_leaf(leaf_bytes), leaf_index, tree_size, tuple(path)
    )
    if calculated_root.hex() != root_hex:
        raise ValueError("ledger inclusion proof root does not match signed tree head")

    return VerifiedLedgerInclusion(
        log_id=log_id,
        tree_size=tree_size,
        leaf_index=leaf_index,
        root_hash=root_hex,
        signed_tree_head_sha256=hashlib.sha256(signed_tree_head).hexdigest(),
    )
