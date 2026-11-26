"""Synthetic composition tests; no test key or record is a trust anchor."""
from __future__ import annotations

import hashlib
import unittest

from origen.external_ledger_v1 import VerifiedLedgerInclusion
from origen.external_ledger_chain_v1 import verify_inclusion_chain_consistency


def leaf(data: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + data).digest()


def node(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


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


    def test_hostile_log_id_subclass_is_rejected_before_equality(self):
        class HostileString(str):
            def __eq__(self, other):
                raise AssertionError("untrusted equality hook executed")

        root = tree_hash([b"only"]).hex()
        old = VerifiedLedgerInclusion(HostileString("log-A"), 1, 0, root, "a" * 64)
        new = VerifiedLedgerInclusion("log-A", 1, 0, root, "b" * 64)
        with self.assertRaisesRegex(ValueError, "log_id must be a canonical exact string"):
            verify_inclusion_chain_consistency(
                old_inclusion=old, new_inclusion=new, consistency_proof_hex=(),
            )

    def test_boolean_tree_size_and_leaf_index_are_rejected(self):
        root = tree_hash([b"only"]).hex()
        bad_size = VerifiedLedgerInclusion("log-A", True, 0, root, "a" * 64)
        valid = VerifiedLedgerInclusion("log-A", 1, 0, root, "b" * 64)
        with self.assertRaisesRegex(ValueError, "tree_size must be"):
            verify_inclusion_chain_consistency(
                old_inclusion=bad_size, new_inclusion=valid, consistency_proof_hex=(),
            )
        bad_index = VerifiedLedgerInclusion("log-A", 1, False, root, "a" * 64)
        with self.assertRaisesRegex(ValueError, "leaf_index must"):
            verify_inclusion_chain_consistency(
                old_inclusion=bad_index, new_inclusion=valid, consistency_proof_hex=(),
            )

    def test_malformed_root_and_signed_head_digest_are_rejected(self):
        root = tree_hash([b"only"]).hex()
        valid = VerifiedLedgerInclusion("log-A", 1, 0, root, "b" * 64)
        bad_root = VerifiedLedgerInclusion("log-A", 1, 0, "A" * 64, "a" * 64)
        with self.assertRaisesRegex(ValueError, "root_hash must"):
            verify_inclusion_chain_consistency(
                old_inclusion=bad_root, new_inclusion=valid, consistency_proof_hex=(),
            )
        bad_sth = VerifiedLedgerInclusion("log-A", 1, 0, root, "not-a-digest")
        with self.assertRaisesRegex(ValueError, "signed_tree_head_sha256 must"):
            verify_inclusion_chain_consistency(
                old_inclusion=bad_sth, new_inclusion=valid, consistency_proof_hex=(),
            )

    def test_new_tree_cannot_be_smaller_than_previous_checkpoint(self):
        items = [f"chain-{i}".encode() for i in range(8)]
        old = VerifiedLedgerInclusion("log-A", 8, 0, tree_hash(items).hex(), "a" * 64)
        new = VerifiedLedgerInclusion("log-A", 5, 0, tree_hash(items[:5]).hex(), "b" * 64)
        with self.assertRaisesRegex(ValueError, "supported bounds"):
            verify_inclusion_chain_consistency(
                old_inclusion=old, new_inclusion=new, consistency_proof_hex=(),
            )

    def test_consistency_proof_container_must_be_exact_tuple(self):
        root = tree_hash([b"only"]).hex()
        record = VerifiedLedgerInclusion("log-A", 1, 0, root, "a" * 64)
        with self.assertRaisesRegex(ValueError, "bounded exact tuple"):
            verify_inclusion_chain_consistency(
                old_inclusion=record, new_inclusion=record,
                consistency_proof_hex=[],
            )


if __name__ == "__main__":
    unittest.main()
