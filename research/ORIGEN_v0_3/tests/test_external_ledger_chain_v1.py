"""Synthetic composition tests; no test key or record is a trust anchor."""
from __future__ import annotations

import hashlib
import unittest

from origen.external_ledger_v1 import VerifiedLedgerInclusion
from origen.external_ledger_chain_v1 import verify_inclusion_chain_consistency


def leaf(data: bytes) -> bytes:
    return hashlib.sha256(b"\\x00" + data).digest()


def node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\\x01" + left + right).digest()


def split_point(n: int) -> int:
    return 1 << ((n - 1).bit_length() - 1)


def tree_hash(items: list[bytes]) -> bytes:
    if len(items) == 1:
        return leaf(items[0])
    k = split_point(len(items))
    return node(tree_hash(items[:k]), tree_hash(items[k:]))


def subproof(m: int, items: list[bytes], complete: bool) -> list[bytes]:
    n = len(items)
    if m == n:
        return [] if complete else [tree_hash(items)]
    k = split_point(n)
    if m <= k:
        return subproof(m, items[:k], complete) + [tree_hash(items[k:])]
    return subproof(m-k, items[k:], False) + [tree_hash(items[:k])]


def proof(m: int, items: list[bytes]) -> tuple[str, ...]:
    return tuple(x.hex() for x in subproof(m, items, True))


class TestExternalLedgerChain(unittest.TestCase):
    def test_composes_two_inclusion_results_with_consistency(self):
        items = [f"chain-{i}".encode() for i in range(13)]
        old = VerifiedLedgerInclusion("log-A", 5, 0, tree_hash(items[:5]).hex(), "a"*64)
        new = VerifiedLedgerInclusion("log-A", 13, 0, tree_hash(items).hex(), "b"*64)
        result = verify_inclusion_chain_consistency(
            old_inclusion=old, new_inclusion=new,
            consistency_proof_hex=proof(5, items),
        )
        self.assertTrue(result.consistency_verified)
        self.assertEqual((result.old_tree_size, result.new_tree_size), (5, 13))

    def test_different_logs_are_rejected(self):
        root = tree_hash([b"one"]).hex()
        old = VerifiedLedgerInclusion("log-A", 1, 0, root, "a"*64)
        new = VerifiedLedgerInclusion("log-B", 1, 0, root, "b"*64)
        with self.assertRaisesRegex(ValueError, "different log"):
            verify_inclusion_chain_consistency(
                old_inclusion=old, new_inclusion=new,
                consistency_proof_hex=(),
            )

    def test_root_tampering_is_rejected(self):
        items = [f"chain-{i}".encode() for i in range(6)]
        old = VerifiedLedgerInclusion("log-A", 2, 0, tree_hash(items[:2]).hex(), "a"*64)
        new = VerifiedLedgerInclusion("log-A", 6, 0, "c"*64, "b"*64)
        with self.assertRaisesRegex(ValueError, "does not connect"):
            verify_inclusion_chain_consistency(
                old_inclusion=old, new_inclusion=new,
                consistency_proof_hex=proof(2, items),
            )

    def test_malformed_inclusion_records_fail_closed(self):
        with self.assertRaisesRegex(TypeError, "exact VerifiedLedgerInclusion"):
            verify_inclusion_chain_consistency(
                old_inclusion=object(),
                new_inclusion=object(),
                consistency_proof_hex=(),
            )


if __name__ == "__main__":
    unittest.main()
