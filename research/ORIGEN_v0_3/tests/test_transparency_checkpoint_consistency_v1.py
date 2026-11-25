from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.transparency_ledger_verifier_v1 import CHECKPOINT_DOMAIN, CHECKPOINT_SCHEMA
from test_transparency_ledger_verifier_v1 import build_fixture

from origen.transparency_checkpoint_consistency_v1 import (
    CONSISTENCY_PROOF_SCHEMA,
    _verify_consistency,
    verify_checkpoint_consistency,
    verify_ledger_inclusion_with_checkpoint_continuity,
)

LOG_ID = "SYNTHETIC-TRANSPARENCY-LOG"
KEY_ID = "SYNTHETIC-LOG-KEY-1"
NOW = datetime(2026, 11, 24, 20, 0, tzinfo=timezone.utc)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def public_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def leaf_hash(value: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + value).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def tree_hash(leaves: list[bytes]) -> bytes:
    if len(leaves) == 1:
        return leaf_hash(leaves[0])
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    return node_hash(tree_hash(leaves[:split]), tree_hash(leaves[split:]))


def consistency_path(old_size: int, leaves: list[bytes], include_old: bool = True) -> list[bytes]:
    if old_size == len(leaves):
        return [] if include_old else [tree_hash(leaves)]
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    if old_size <= split:
        return (
            consistency_path(old_size, leaves[:split], include_old)
            + [tree_hash(leaves[split:])]
        )
    return (
        consistency_path(old_size - split, leaves[split:], False)
        + [tree_hash(leaves[:split])]
    )


def signed_checkpoint(
    private_key: Ed25519PrivateKey,
    leaves: list[bytes],
    *,
    issued_at: str,
    tree_size_override: object | None = None,
    root_override: bytes | None = None,
) -> tuple[dict, bytes]:
    unsigned = {
        "schema_version": CHECKPOINT_SCHEMA,
        "log_id": LOG_ID,
        "key_id": KEY_ID,
        "tree_size": len(leaves) if tree_size_override is None else tree_size_override,
        "root_hash": (tree_hash(leaves) if root_override is None else root_override).hex(),
        "issued_at_utc": issued_at,
    }
    signature = private_key.sign(CHECKPOINT_DOMAIN + canonical(unsigned))
    checkpoint = dict(unsigned)
    checkpoint["signature_b64"] = base64.b64encode(signature).decode("ascii")
    return checkpoint, canonical(checkpoint)


def build_pair(
    old_size: int,
    new_size: int,
    *,
    old_issued_at: str = "2026-11-24T19:00:00Z",
    new_issued_at: str = "2026-11-24T19:01:00Z",
):
    private_key = Ed25519PrivateKey.from_private_bytes(b"\x2a" * 32)
    leaves = [f"leaf-{index}".encode("ascii") for index in range(max(old_size, new_size))]
    old_leaves = leaves[:old_size]
    new_leaves = leaves[:new_size]
    old_checkpoint, old_bytes = signed_checkpoint(
        private_key, old_leaves, issued_at=old_issued_at
    )
    new_checkpoint, new_bytes = signed_checkpoint(
        private_key, new_leaves, issued_at=new_issued_at
    )
    path = (
        consistency_path(old_size, new_leaves, True)
        if 0 < old_size <= new_size
        else []
    )
    proof = {
        "schema_version": CONSISTENCY_PROOF_SCHEMA,
        "log_id": LOG_ID,
        "old_checkpoint_sha256": sha(old_bytes),
        "new_checkpoint_sha256": sha(new_bytes),
        "old_tree_size": old_size,
        "new_tree_size": new_size,
        "consistency_path_b64": [
            base64.b64encode(node).decode("ascii") for node in path
        ],
    }
    return {
        "private_key": private_key,
        "public_key": public_bytes(private_key),
        "old_checkpoint": old_checkpoint,
        "new_checkpoint": new_checkpoint,
        "old_bytes": old_bytes,
        "new_bytes": new_bytes,
        "proof": proof,
        "proof_bytes": canonical(proof),
    }


def inspect(data, **overrides):
    kwargs = {
        "pinned_log_public_key_bytes": data["public_key"],
        "expected_log_id": LOG_ID,
        "expected_key_id": KEY_ID,
        "minimum_new_tree_size": max(1, data["proof"]["new_tree_size"]),
        "verification_time": NOW,
    }
    kwargs.update(overrides)
    return verify_checkpoint_consistency(
        data["old_bytes"],
        data["new_bytes"],
        data["proof_bytes"],
        **kwargs,
    )


class CheckpointConsistencyV1Tests(unittest.TestCase):
    def test_rfc6962_consistency_proofs_verify_all_size_pairs_through_32(self):
        for new_size in range(1, 33):
            for old_size in range(1, new_size + 1):
                with self.subTest(old_size=old_size, new_size=new_size):
                    data = build_pair(old_size, new_size)
                    result = inspect(data)
                    self.assertTrue(result.checkpoint_signatures_verified)
                    self.assertTrue(result.consistency_verified)
                    self.assertEqual(result.old_tree_size, old_size)
                    self.assertEqual(result.new_tree_size, new_size)
                    self.assertIs(
                        result.provenance_status,
                        ProvenanceStatus.BLOCKED_PROVENANCE,
                    )

    def test_same_size_checkpoint_pair_requires_same_root_and_empty_proof(self):
        data = build_pair(7, 7)
        result = inspect(data)
        self.assertEqual(result.old_root_sha256, result.new_root_sha256)
        self.assertEqual(result.append_only_continuity_status,
                         "CONSISTENCY_VERIFIED_WITNESS_QUORUM_UNVERIFIED")

    def test_same_size_pair_with_different_root_is_rejected(self):
        data = build_pair(7, 7)
        changed = dict(data["new_checkpoint"])
        changed["root_hash"] = sha(b"different-root")
        unsigned = {key: value for key, value in changed.items() if key != "signature_b64"}
        changed["signature_b64"] = base64.b64encode(
            data["private_key"].sign(CHECKPOINT_DOMAIN + canonical(unsigned))
        ).decode("ascii")
        data["new_bytes"] = canonical(changed)
        data["proof"] = dict(data["proof"])
        data["proof"]["new_checkpoint_sha256"] = sha(data["new_bytes"])
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "same-size checkpoints have different Merkle roots"):
            inspect(data)

    def test_tree_size_rollback_is_rejected(self):
        data = build_pair(4, 3)
        with self.assertRaisesRegex(ValueError, "exceeds new checkpoint"):
            inspect(data)

    def test_tampered_consistency_node_is_rejected(self):
        data = build_pair(3, 9)
        proof = copy.deepcopy(data["proof"])
        node = bytearray(base64.b64decode(proof["consistency_path_b64"][0]))
        node[0] ^= 1
        proof["consistency_path_b64"][0] = base64.b64encode(bytes(node)).decode("ascii")
        data["proof_bytes"] = canonical(proof)
        with self.assertRaisesRegex(ValueError, "does not establish append-only"):
            inspect(data)

    def test_incomplete_consistency_path_is_rejected(self):
        data = build_pair(3, 9)
        proof = copy.deepcopy(data["proof"])
        proof["consistency_path_b64"].pop()
        data["proof_bytes"] = canonical(proof)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            inspect(data)

    def test_extra_consistency_path_node_is_rejected(self):
        data = build_pair(3, 9)
        proof = copy.deepcopy(data["proof"])
        proof["consistency_path_b64"].append(base64.b64encode(b"x" * 32).decode("ascii"))
        data["proof_bytes"] = canonical(proof)
        with self.assertRaisesRegex(ValueError, "extra nodes"):
            inspect(data)

    def test_empty_path_cannot_prove_growth(self):
        data = build_pair(3, 9)
        data["proof"]["consistency_path_b64"] = []
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            inspect(data)

    def test_proof_must_bind_exact_old_checkpoint_bytes(self):
        data = build_pair(3, 9)
        data["proof"]["old_checkpoint_sha256"] = "0" * 64
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "exact old checkpoint bytes"):
            inspect(data)

    def test_proof_must_bind_exact_new_checkpoint_bytes(self):
        data = build_pair(3, 9)
        data["proof"]["new_checkpoint_sha256"] = "0" * 64
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "exact new checkpoint bytes"):
            inspect(data)

    def test_checkpoint_signature_tampering_is_rejected(self):
        data = build_pair(3, 9)
        checkpoint = dict(data["old_checkpoint"])
        checkpoint["signature_b64"] = base64.b64encode(b"\x00" * 64).decode("ascii")
        data["old_bytes"] = canonical(checkpoint)
        data["proof"]["old_checkpoint_sha256"] = sha(data["old_bytes"])
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "old checkpoint Ed25519 signature verification failed"):
            inspect(data)

    def test_wrong_log_public_key_is_rejected(self):
        data = build_pair(3, 9)
        attacker = Ed25519PrivateKey.from_private_bytes(b"\x31" * 32)
        with self.assertRaisesRegex(ValueError, "old checkpoint Ed25519 signature verification failed"):
            inspect(data, pinned_log_public_key_bytes=public_bytes(attacker))

    def test_wrong_expected_log_or_key_id_is_rejected(self):
        data = build_pair(3, 9)
        with self.assertRaisesRegex(ValueError, "log_id does not match"):
            inspect(data, expected_log_id="OTHER-LOG")
        with self.assertRaisesRegex(ValueError, "key_id does not match"):
            inspect(data, expected_key_id="OTHER-KEY")

    def test_minimum_tree_size_floor_is_enforced(self):
        data = build_pair(3, 9)
        with self.assertRaisesRegex(ValueError, "below the caller-supplied monotonic floor"):
            inspect(data, minimum_new_tree_size=10)

    def test_new_checkpoint_cannot_be_issued_before_old_checkpoint(self):
        data = build_pair(
            3, 9,
            old_issued_at="2026-11-24T19:02:00Z",
            new_issued_at="2026-11-24T19:01:00Z",
        )
        with self.assertRaisesRegex(ValueError, "precedes old checkpoint"):
            inspect(data)

    def test_future_checkpoint_is_rejected_against_supplied_clock(self):
        data = build_pair(3, 9)
        with self.assertRaisesRegex(ValueError, "later than supplied verification time"):
            inspect(data, verification_time=datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc))

    def test_boolean_checkpoint_tree_size_is_not_an_integer(self):
        data = build_pair(3, 9)
        checkpoint = dict(data["new_checkpoint"])
        checkpoint["tree_size"] = True
        unsigned = {key: value for key, value in checkpoint.items() if key != "signature_b64"}
        checkpoint["signature_b64"] = base64.b64encode(
            data["private_key"].sign(CHECKPOINT_DOMAIN + canonical(unsigned))
        ).decode("ascii")
        data["new_bytes"] = canonical(checkpoint)
        data["proof"]["new_checkpoint_sha256"] = sha(data["new_bytes"])
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "new checkpoint tree_size must be a positive"):
            inspect(data)

    def test_noncanonical_checkpoint_json_is_rejected(self):
        data = build_pair(3, 9)
        data["old_bytes"] = json.dumps(data["old_checkpoint"], sort_keys=False).encode("utf-8")
        data["proof"]["old_checkpoint_sha256"] = sha(data["old_bytes"])
        data["proof_bytes"] = canonical(data["proof"])
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 JSON"):
            inspect(data)

    def test_duplicate_checkpoint_json_key_is_rejected(self):
        data = build_pair(3, 9)
        data["old_bytes"] = b'{"schema_version":"x","schema_version":"y"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            inspect(data)

    def test_consistency_proof_cannot_promote_provenance_without_external_witnesses(self):
        data = build_pair(3, 9)
        result = inspect(data)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn("INDEPENDENT_CHECKPOINT_WITNESS_QUORUM_NOT_VERIFIED",
                      result.remaining_blockers)
        self.assertEqual(result.trust_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.anti_rollback_source, "CALLER_SUPPLIED_UNAUTHENTICATED")

    def test_consistency_proof_requires_exact_bytes(self):
        data = build_pair(3, 9)
        with self.assertRaises(TypeError):
            verify_checkpoint_consistency(
                bytearray(data["old_bytes"]),
                data["new_bytes"],
                data["proof_bytes"],
                pinned_log_public_key_bytes=data["public_key"],
                expected_log_id=LOG_ID,
                expected_key_id=KEY_ID,
                minimum_new_tree_size=9,
                verification_time=NOW,
            )


    def test_composed_verifier_binds_inclusion_to_the_same_consistent_new_checkpoint(self):
        data = build_fixture()
        leaves = [
            b"unrelated-ledger-record-0",
            data["entry_bytes"],
            b"unrelated-ledger-record-2",
            b"unrelated-ledger-record-3",
            b"unrelated-ledger-record-4",
            b"unrelated-ledger-record-5",
            b"unrelated-ledger-record-6",
        ]
        old_checkpoint, old_bytes = signed_checkpoint(
            data["log_private"],
            leaves[:3],
            issued_at="2026-11-24T18:59:00Z",
        )
        del old_checkpoint
        path = consistency_path(3, leaves, True)
        proof = {
            "schema_version": CONSISTENCY_PROOF_SCHEMA,
            "log_id": LOG_ID,
            "old_checkpoint_sha256": sha(old_bytes),
            "new_checkpoint_sha256": sha(data["checkpoint_bytes"]),
            "old_tree_size": 3,
            "new_tree_size": 7,
            "consistency_path_b64": [
                base64.b64encode(node).decode("ascii") for node in path
            ],
        }
        result = verify_ledger_inclusion_with_checkpoint_continuity(
            data["manifest_bytes"],
            data["entry_bytes"],
            data["proof_bytes"],
            old_bytes,
            data["checkpoint_bytes"],
            canonical(proof),
            pinned_log_public_key_bytes=data["log_public"],
            expected_log_id=LOG_ID,
            expected_key_id=KEY_ID,
            minimum_new_tree_size=7,
            verification_time=NOW,
        )
        self.assertTrue(result.inclusion.inclusion_verified)
        self.assertTrue(result.checkpoint_consistency.consistency_verified)
        self.assertEqual(
            result.inclusion.checkpoint_sha256,
            result.checkpoint_consistency.new_checkpoint_sha256,
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_composed_verifier_rejects_consistency_for_a_different_new_checkpoint(self):
        data = build_fixture()
        leaves = [
            b"unrelated-ledger-record-0",
            data["entry_bytes"],
            b"unrelated-ledger-record-2",
            b"unrelated-ledger-record-3",
            b"unrelated-ledger-record-4",
            b"unrelated-ledger-record-5",
            b"unrelated-ledger-record-6",
        ]
        _, old_bytes = signed_checkpoint(
            data["log_private"],
            leaves[:3],
            issued_at="2026-11-24T18:59:00Z",
        )
        _, other_new_bytes = signed_checkpoint(
            data["log_private"],
            leaves,
            issued_at="2026-11-24T19:02:00Z",
        )
        proof = {
            "schema_version": CONSISTENCY_PROOF_SCHEMA,
            "log_id": LOG_ID,
            "old_checkpoint_sha256": sha(old_bytes),
            "new_checkpoint_sha256": sha(other_new_bytes),
            "old_tree_size": 3,
            "new_tree_size": 7,
            "consistency_path_b64": [
                base64.b64encode(node).decode("ascii")
                for node in consistency_path(3, leaves, True)
            ],
        }
        with self.assertRaisesRegex(ValueError, "checkpoint digest does not match exact checkpoint bytes"):
            verify_ledger_inclusion_with_checkpoint_continuity(
                data["manifest_bytes"],
                data["entry_bytes"],
                data["proof_bytes"],
                old_bytes,
                other_new_bytes,
                canonical(proof),
                pinned_log_public_key_bytes=data["log_public"],
                expected_log_id=LOG_ID,
                expected_key_id=KEY_ID,
                minimum_new_tree_size=7,
                verification_time=NOW,
            )


if __name__ == "__main__":
    unittest.main()
