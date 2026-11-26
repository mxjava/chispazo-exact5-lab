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

_HEX64 = re.compile(r"[0-9a-f]{64}\\Z")


@dataclass(frozen=True, slots=True)
class VerifiedLedgerChain:
    log_id: str
    old_tree_size: int
    new_tree_size: int
    old_root_hex: str
    new_root_hex: str
    consistency_verified: bool


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
    if type(old_inclusion) is not VerifiedLedgerInclusion or type(new_inclusion) is not VerifiedLedgerInclusion:
        raise TypeError("inclusions must be exact VerifiedLedgerInclusion records")
    if old_inclusion.log_id != new_inclusion.log_id:
        raise ValueError("ledger inclusions belong to different log identities")
    if type(consistency_proof_hex) is not tuple or len(consistency_proof_hex) > 64:
        raise ValueError("consistency_proof_hex must be a bounded exact tuple")
    nodes = []
    for index, item in enumerate(consistency_proof_hex):
        if type(item) is not str or not _HEX64.fullmatch(item):
            raise ValueError(f"consistency_proof_hex[{index}] must be lowercase SHA-256 hex")
        nodes.append(bytes.fromhex(item))
    try:
        old_root = bytes.fromhex(old_inclusion.root_hash)
        new_root = bytes.fromhex(new_inclusion.root_hash)
    except (TypeError, ValueError) as exc:
        raise ValueError("inclusion roots must be lowercase SHA-256 hex") from exc
    if not _HEX64.fullmatch(old_inclusion.root_hash) or not _HEX64.fullmatch(new_inclusion.root_hash):
        raise ValueError("inclusion roots must be lowercase SHA-256 hex")

    verified = verify_consistency_proof(
        old_tree_size=old_inclusion.tree_size,
        new_tree_size=new_inclusion.tree_size,
        old_root=old_root,
        new_root=new_root,
        proof=tuple(nodes),
    )
    return VerifiedLedgerChain(
        log_id=old_inclusion.log_id,
        old_tree_size=verified.old_tree_size,
        new_tree_size=verified.new_tree_size,
        old_root_hex=verified.old_root_hex,
        new_root_hex=verified.new_root_hex,
        consistency_verified=True,
    )
