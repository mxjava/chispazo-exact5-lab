"""Synthetic-only adversarial tests for RFC 6962 consistency proofs."""
from __future__ import annotations

import hashlib
import unittest

from origen.external_ledger_consistency_v1 import (
    verify_consistency_proof,
)


def leaf(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def split_point(n: int) -> int:
    return 1 << ((n - 1).bit_length() - 1)


def tree_hash(leaves: list[bytes]) -> bytes:
    if len(leaves) == 1:
        return leaf(leaves[0])
    k = split_point(len(leaves))
    return node(tree_hash(leaves[:k]), tree_hash(leaves[k:]))


def subproof(m: int, leaves: list[bytes], complete: bool) -> list[bytes]:
    n = len(leaves)
    if m == n:
        return [] if complete else [tree_hash(leaves)]
    k = split_point(n)
    if m <= k:
        return subproof(m, leaves[:k], complete) + [tree_hash(leaves[k:])]
    return subproof(m - k, leaves[k:], False) + [tree_hash(leaves[:k])]


def consistency_proof(m: int, leaves: list[bytes]) -> tuple[bytes, ...]:
    return tuple(subproof(m, leaves, True))


class TestExternalLedgerConsistency(unittest.TestCase):
    def test_all_old_sizes_against_all_later_sizes_through_40(self):
        leaves = [f"synthetic-{i}".encode() for i in range(40)]
        for new_size in range(2, len(leaves) + 1):
            for old_size in range(1, new_size):
                result = verify_consistency_proof(
                    old_tree_size=old_size,
                    new_tree_size=new_size,
                    old_root=tree_hash(leaves[:old_size]),
                    new_root=tree_hash(leaves[:new_size]),
                    proof=consistency_proof(old_size, leaves[:new_size]),
                )
                self.assertEqual(result.old_tree_size, old_size)
                self.assertEqual(result.new_tree_size, new_size)

    def test_equal_size_requires_same_root_and_empty_proof(self):
        root = tree_hash([b"only"])
        verify_consistency_proof(
            old_tree_size=1, new_tree_size=1,
            old_root=root, new_root=root, proof=(),
        )
        with self.assertRaisesRegex(ValueError, "identical roots"):
            verify_consistency_proof(
                old_tree_size=1, new_tree_size=1,
                old_root=root, new_root=b"x" * 32, proof=(),
            )

    def test_tampered_proof_is_rejected(self):
        leaves = [f"x{i}".encode() for i in range(9)]
        proof = list(consistency_proof(3, leaves))
        proof[0] = b"z" * 32
        with self.assertRaisesRegex(ValueError, "does not connect"):
            verify_consistency_proof(
                old_tree_size=3, new_tree_size=9,
                old_root=tree_hash(leaves[:3]), new_root=tree_hash(leaves),
                proof=tuple(proof),
            )

    def test_wrong_new_root_is_rejected(self):
        leaves = [f"x{i}".encode() for i in range(7)]
        with self.assertRaisesRegex(ValueError, "does not connect"):
            verify_consistency_proof(
                old_tree_size=3, new_tree_size=7,
                old_root=tree_hash(leaves[:3]), new_root=b"q" * 32,
                proof=consistency_proof(3, leaves),
            )

    def test_sizes_reject_bool_and_invalid_ranges(self):
        root = tree_hash([b"x"])
        with self.assertRaisesRegex(ValueError, "exact integers"):
            verify_consistency_proof(
                old_tree_size=True, new_tree_size=2,
                old_root=root, new_root=root, proof=(),
            )
        with self.assertRaisesRegex(ValueError, "supported bounds"):
            verify_consistency_proof(
                old_tree_size=2, new_tree_size=1,
                old_root=root, new_root=root, proof=(),
            )

    def test_proof_shape_and_bounds_are_strict(self):
        root = tree_hash([b"x"])
        with self.assertRaisesRegex(ValueError, "bounded exact tuple"):
            verify_consistency_proof(
                old_tree_size=1, new_tree_size=2,
                old_root=root, new_root=root, proof=(b"x" * 32,) * 65,
            )
        with self.assertRaisesRegex(ValueError, "exactly 32"):
            verify_consistency_proof(
                old_tree_size=1, new_tree_size=2,
                old_root=root, new_root=root, proof=(b"short",),
            )


if __name__ == "__main__":
    unittest.main()
