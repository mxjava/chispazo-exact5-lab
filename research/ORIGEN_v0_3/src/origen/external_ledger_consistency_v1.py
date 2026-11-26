"""Bounded RFC 6962 Merkle consistency-proof verification (research only).

This proves that a later tree is an append-only extension of an earlier tree
when both roots have already been authenticated independently. It does not
authenticate either tree head, persist a checkpoint, or provide a witness.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

_MAX_TREE_SIZE = (1 << 63) - 1
_MAX_PROOF_NODES = 64


def _node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


@dataclass(frozen=True, slots=True)
class VerifiedConsistency:
    """A mathematical relation between two supplied Merkle roots only."""

    old_tree_size: int
    new_tree_size: int
    old_root_hex: str
    new_root_hex: str


def verify_consistency_proof(
    *,
    old_tree_size: int,
    new_tree_size: int,
    old_root: bytes,
    new_root: bytes,
    proof: tuple[bytes, ...],
) -> VerifiedConsistency:
    """Verify an RFC 6962 consistency proof between two tree heads.

    The caller remains responsible for authenticating both signed tree heads
    and for persisting the accepted latest checkpoint outside this process.
    """
    if type(old_tree_size) is not int or type(new_tree_size) is not int:
        raise ValueError("tree sizes must be exact integers")
    if not 1 <= old_tree_size <= new_tree_size <= _MAX_TREE_SIZE:
        raise ValueError("tree sizes are outside supported bounds")
    if type(old_root) is not bytes or len(old_root) != 32:
        raise ValueError("old_root must be exactly 32 immutable bytes")
    if type(new_root) is not bytes or len(new_root) != 32:
        raise ValueError("new_root must be exactly 32 immutable bytes")
    if type(proof) is not tuple or len(proof) > _MAX_PROOF_NODES:
        raise ValueError("proof must be a bounded exact tuple")
    if any(type(item) is not bytes or len(item) != 32 for item in proof):
        raise ValueError("every proof node must be exactly 32 immutable bytes")

    if old_tree_size == new_tree_size:
        if proof or old_root != new_root:
            raise ValueError("equal-size tree heads require identical roots and empty proof")
        return VerifiedConsistency(
            old_tree_size, new_tree_size, old_root.hex(), new_root.hex()
        )

    fn = old_tree_size - 1
    sn = new_tree_size - 1
    while fn & 1:
        fn >>= 1
        sn >>= 1

    if fn == 0:
        first_hash = old_root
        second_hash = old_root
        proof_index = 0
    else:
        if not proof:
            raise ValueError("consistency proof is empty")
        first_hash = proof[0]
        second_hash = proof[0]
        proof_index = 1

    for node in proof[proof_index:]:
        if sn == 0:
            raise ValueError("consistency proof has excess nodes")
        if (fn & 1) or fn == sn:
            first_hash = _node(node, first_hash)
            second_hash = _node(node, second_hash)
            while fn and not (fn & 1):
                fn >>= 1
                sn >>= 1
        else:
            second_hash = _node(second_hash, node)
        fn >>= 1
        sn >>= 1

    if sn != 0 or first_hash != old_root or second_hash != new_root:
        raise ValueError("consistency proof does not connect the supplied roots")
    return VerifiedConsistency(
        old_tree_size, new_tree_size, old_root.hex(), new_root.hex()
    )
