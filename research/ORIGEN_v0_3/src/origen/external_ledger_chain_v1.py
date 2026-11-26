"""Research-only composition of verified ledger inclusions and consistency.

This helper consumes result records from the signed inclusion verifier and
checks append-only consistency between their roots. The records are ordinary
Python data and are forgeable; this is NOT an authorization boundary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .external_ledger_v1 import VerifiedLedgerInclusion
from .external_ledger_consistency_v1 import verify_consistency_proof

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_LOG_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_MAX_TREE_SIZE = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class VerifiedLedgerChain:
    log_id: str
    old_tree_size: int
    new_tree_size: int
    old_root_hex: str
    new_root_hex: str
    consistency_verified: bool


def _validate_inclusion_record(value: object, label: str) -> VerifiedLedgerInclusion:
    if type(value) is not VerifiedLedgerInclusion:
        raise TypeError(f"{label} must be an exact VerifiedLedgerInclusion record")
    if type(value.log_id) is not str or not _LOG_ID.fullmatch(value.log_id):
        raise ValueError(f"{label}.log_id must be a canonical exact string")
    if type(value.tree_size) is not int or not 1 <= value.tree_size <= _MAX_TREE_SIZE:
        raise ValueError(f"{label}.tree_size must be a positive signed-64-bit exact integer")
    if type(value.leaf_index) is not int or not 0 <= value.leaf_index < value.tree_size:
        raise ValueError(f"{label}.leaf_index must identify a leaf inside its exact tree size")
    if type(value.root_hash) is not str or not _HEX64.fullmatch(value.root_hash):
        raise ValueError(f"{label}.root_hash must be lowercase SHA-256 hex")
    if type(value.signed_tree_head_sha256) is not str or not _HEX64.fullmatch(value.signed_tree_head_sha256):
        raise ValueError(f"{label}.signed_tree_head_sha256 must be lowercase SHA-256 hex")
    return value


def verify_inclusion_chain_consistency(
    *,
    old_inclusion: VerifiedLedgerInclusion,
    new_inclusion: VerifiedLedgerInclusion,
    consistency_proof_hex: tuple[str, ...],
) -> VerifiedLedgerChain:
    """Check two inclusion-result roots are append-only consistent.

    Both inclusion records must have been obtained from independently verified
    signed tree heads in the same process/control flow. Because these dataclasses
    are forgeable, callers MUST NOT treat this function alone as proof of
    authenticity, custody, persistent anti-rollback, or authorization.
    """
    old = _validate_inclusion_record(old_inclusion, "old_inclusion")
    new = _validate_inclusion_record(new_inclusion, "new_inclusion")
    if old.log_id != new.log_id:
        raise ValueError("ledger inclusions belong to different log identities")
    if type(consistency_proof_hex) is not tuple or len(consistency_proof_hex) > 64:
        raise ValueError("consistency_proof_hex must be a bounded exact tuple")
    nodes = []
    for index, item in enumerate(consistency_proof_hex):
        if type(item) is not str or not _HEX64.fullmatch(item):
            raise ValueError(f"consistency_proof_hex[{index}] must be lowercase SHA-256 hex")
        nodes.append(bytes.fromhex(item))

    verified = verify_consistency_proof(
        old_tree_size=old.tree_size,
        new_tree_size=new.tree_size,
        old_root=bytes.fromhex(old.root_hash),
        new_root=bytes.fromhex(new.root_hash),
        proof=tuple(nodes),
    )
    return VerifiedLedgerChain(
        log_id=old.log_id,
        old_tree_size=verified.old_tree_size,
        new_tree_size=verified.new_tree_size,
        old_root_hex=verified.old_root_hex,
        new_root_hex=verified.new_root_hex,
        consistency_verified=True,
    )
