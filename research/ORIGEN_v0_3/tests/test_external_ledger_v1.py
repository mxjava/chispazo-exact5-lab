"""Synthetic-only adversarial tests for the RFC 6962 ledger verifier."""
from __future__ import annotations

import base64
import hashlib
import json
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.external_ledger_v1 import (
    _hash_leaf,
    _hash_node,
    verify_external_ledger_inclusion,
)

LOG_ID = "synthetic-log-only"
DOMAIN = b"ORIGEN_EXTERNAL_LEDGER_STH_V1\n"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def public_bytes(key):
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def split_point(n):
    return 1 << ((n - 1).bit_length() - 1)


def tree_hash(leaves):
    if len(leaves) == 1:
        return _hash_leaf(leaves[0])
    k = split_point(len(leaves))
    return _hash_node(tree_hash(leaves[:k]), tree_hash(leaves[k:]))


def inclusion_path(leaves, index):
    if len(leaves) == 1:
        return []
    k = split_point(len(leaves))
    if index < k:
        return inclusion_path(leaves[:k], index) + [tree_hash(leaves[k:])]
    return inclusion_path(leaves[k:], index - k) + [tree_hash(leaves[:k])]


def signed_head(private_key, tree_size, root_hash, log_id=LOG_ID):
    unsigned = {
        "schema": "ORIGEN_STH_V1",
        "log_id": log_id,
        "tree_size": tree_size,
        "root_hash": root_hash.hex(),
    }
    signature = private_key.sign(DOMAIN + canonical(unsigned))
    return canonical({
        **unsigned,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    })


class TestExternalLedgerInclusion(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pin = public_bytes(self.key)

    def verify(self, leaves, index, **overrides):
        root = tree_hash(leaves)
        head = signed_head(self.key, len(leaves), root)
        args = {
            "leaf_bytes": leaves[index],
            "log_id": LOG_ID,
            "tree_size": len(leaves),
            "leaf_index": index,
            "audit_path_hex": tuple(x.hex() for x in inclusion_path(leaves, index)),
            "signed_tree_head": head,
            "pinned_log_public_key_bytes": self.pin,
            "expected_log_id": LOG_ID,
            "minimum_tree_size": 1,
        }
        args.update(overrides)
        return verify_external_ledger_inclusion(**args)

    def test_all_leaves_in_non_power_of_two_trees_verify(self):
        for size in range(1, 10):
            leaves = [f"synthetic-leaf-{size}-{i}".encode("ascii") for i in range(size)]
            for index in range(size):
                result = self.verify(leaves, index)
                self.assertEqual(result.tree_size, size)
                self.assertEqual(result.leaf_index, index)
                self.assertEqual(result.root_hash, tree_hash(leaves).hex())

    def test_tampered_leaf_is_rejected(self):
        leaves = [b"alpha", b"beta", b"gamma"]
        with self.assertRaisesRegex(ValueError, "proof root"):
            self.verify(leaves, 1, leaf_bytes=b"attacker-substitution")

    def test_tampered_audit_path_is_rejected(self):
        leaves = [b"alpha", b"beta", b"gamma"]
        path = list(inclusion_path(leaves, 1))
        path[0] = b"X" * 32
        with self.assertRaisesRegex(ValueError, "proof root"):
            self.verify(leaves, 1, audit_path_hex=tuple(x.hex() for x in path))

    def test_wrong_external_log_key_is_rejected(self):
        leaves = [b"alpha"]
        wrong = public_bytes(Ed25519PrivateKey.generate())
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            self.verify(leaves, 0, pinned_log_public_key_bytes=wrong)

    def test_wrong_log_identity_is_rejected(self):
        leaves = [b"alpha"]
        with self.assertRaisesRegex(ValueError, "identity"):
            self.verify(leaves, 0, expected_log_id="different-log")


    def test_hostile_expected_log_id_is_rejected_before_comparison(self):
        leaves = [b"alpha"]

        class HostileIdentity:
            def __eq__(self, other):
                raise AssertionError("untrusted equality must not execute")

        with self.assertRaisesRegex(ValueError, "expected_log_id"):
            self.verify(leaves, 0, expected_log_id=HostileIdentity())

    def test_tree_size_rollback_is_rejected(self):
        leaves = [b"alpha", b"beta"]
        with self.assertRaisesRegex(ValueError, "below externally pinned minimum"):
            self.verify(leaves, 0, minimum_tree_size=3)

    def test_boolean_tree_size_and_index_are_not_integers(self):
        leaves = [b"alpha"]
        with self.assertRaisesRegex(ValueError, "exact integers"):
            self.verify(leaves, 0, tree_size=True)
        with self.assertRaisesRegex(ValueError, "exact integers"):
            self.verify(leaves, 0, leaf_index=False)

    def test_overlong_path_is_rejected(self):
        leaves = [b"alpha"]
        with self.assertRaisesRegex(ValueError, "bounded exact tuple"):
            self.verify(leaves, 0, audit_path_hex=("0" * 64,) * 65)


    def test_duplicate_signed_tree_head_json_keys_are_rejected(self):
        leaves = [b"alpha"]
        root = tree_hash(leaves)
        signature = self.key.sign(DOMAIN + canonical({
            "schema": "ORIGEN_STH_V1",
            "log_id": LOG_ID,
            "tree_size": 1,
            "root_hash": root.hex(),
        }))
        sig = base64.b64encode(signature).decode("ascii")
        raw = (
            b'{"schema":"ORIGEN_STH_V1","schema":"ORIGEN_STH_V1",'
            + b'"log_id":"synthetic-log-only","tree_size":1,"root_hash":"'
            + root.hex().encode("ascii")
            + b'","signature_b64":"' + sig.encode("ascii") + b'"}'
        )
        with self.assertRaisesRegex(ValueError, "duplicate JSON keys"):
            self.verify(leaves, 0, signed_tree_head=raw)

    def test_oversized_leaf_is_rejected_before_hashing(self):
        leaves = [b"alpha"]
        with self.assertRaisesRegex(ValueError, "size limit"):
            self.verify(leaves, 0, leaf_bytes=b"x" * (1_048_576 + 1))

    def test_signed_head_tampering_is_rejected(self):
        leaves = [b"alpha"]
        root = tree_hash(leaves)
        head = json.loads(signed_head(self.key, 1, root))
        head["tree_size"] = 2
        with self.assertRaisesRegex(ValueError, "tree size mismatch"):
            self.verify(leaves, 0, signed_tree_head=canonical(head))


if __name__ == "__main__":
    unittest.main()
