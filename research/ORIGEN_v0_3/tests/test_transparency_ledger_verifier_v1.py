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
from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from origen.transparency_ledger_verifier_v1 import (
    CHECKPOINT_DOMAIN,
    CHECKPOINT_SCHEMA,
    ENTRY_SCHEMA,
    PROOF_SCHEMA,
    _verify_inclusion,
    verify_transparency_ledger_inclusion,
)
from test_physical_evidence_manifest_v1 import encode, valid_document

NOW = datetime(2026, 11, 24, 19, 30, tzinfo=timezone.utc)
LOG_ID = "SYNTHETIC-TRANSPARENCY-LOG"
LOG_KEY_ID = "SYNTHETIC-LOG-KEY-1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


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


def inclusion_path(index: int, leaves: list[bytes]) -> list[bytes]:
    if len(leaves) == 1:
        return []
    split = 1 << ((len(leaves) - 1).bit_length() - 1)
    if index < split:
        return inclusion_path(index, leaves[:split]) + [tree_hash(leaves[split:])]
    return inclusion_path(index - split, leaves[split:]) + [tree_hash(leaves[:split])]


def manifest_commitment(document: dict) -> str:
    normalized = copy.deepcopy(document)
    normalized["ledger_anchor"].pop("inclusion_proof_sha256")
    return sha(canonical(normalized))


def build_fixture():
    document = valid_document()
    document["ledger_anchor"]["inclusion_proof_sha256"] = "0" * 64
    commitment = manifest_commitment(document)
    artifact_digests = sorted(item["sha256"] for item in document["artifacts"])
    entry = {
        "schema_version": ENTRY_SCHEMA,
        "ledger_id": document["ledger_anchor"]["ledger_id"],
        "entry_id": document["ledger_anchor"]["entry_id"],
        "manifest_commitment_sha256": commitment,
        "artifact_sha256s": artifact_digests,
    }
    entry_bytes = canonical(entry)
    leaves = [
        b"unrelated-ledger-record-0",
        entry_bytes,
        b"unrelated-ledger-record-2",
        b"unrelated-ledger-record-3",
        b"unrelated-ledger-record-4",
        b"unrelated-ledger-record-5",
        b"unrelated-ledger-record-6",
    ]
    index = 1
    root_hash = tree_hash(leaves)
    log_private = Ed25519PrivateKey.from_private_bytes(b"\x19" * 32)
    unsigned_checkpoint = {
        "schema_version": CHECKPOINT_SCHEMA,
        "log_id": LOG_ID,
        "key_id": LOG_KEY_ID,
        "tree_size": len(leaves),
        "root_hash": root_hash.hex(),
        "issued_at_utc": "2026-11-24T19:00:00Z",
    }
    checkpoint_signature = log_private.sign(
        CHECKPOINT_DOMAIN + canonical(unsigned_checkpoint)
    )
    checkpoint = dict(unsigned_checkpoint)
    checkpoint["signature_b64"] = base64.b64encode(checkpoint_signature).decode("ascii")
    checkpoint_bytes = canonical(checkpoint)
    proof = {
        "schema_version": PROOF_SCHEMA,
        "ledger_id": document["ledger_anchor"]["ledger_id"],
        "entry_id": document["ledger_anchor"]["entry_id"],
        "log_id": LOG_ID,
        "leaf_index": index,
        "checkpoint_sha256": sha(checkpoint_bytes),
        "audit_path_b64": [
            base64.b64encode(node).decode("ascii")
            for node in inclusion_path(index, leaves)
        ],
    }
    proof_bytes = canonical(proof)
    document["ledger_anchor"]["inclusion_proof_sha256"] = sha(proof_bytes)
    manifest_bytes = encode(document)
    parsed = parse_unverified_physical_manifest(manifest_bytes)
    assert parsed.raw_sha256 == sha(manifest_bytes)
    assert manifest_commitment(document) == commitment
    return {
        "document": document,
        "manifest_bytes": manifest_bytes,
        "entry_bytes": entry_bytes,
        "proof": proof,
        "proof_bytes": proof_bytes,
        "checkpoint": checkpoint,
        "checkpoint_bytes": checkpoint_bytes,
        "log_private": log_private,
        "log_public": public_bytes(log_private),
        "tree_size": len(leaves),
        "leaf_index": index,
    }


def inspect(data, **overrides):
    values = {
        "pinned_log_public_key_bytes": data["log_public"],
        "expected_log_id": LOG_ID,
        "expected_key_id": LOG_KEY_ID,
        "minimum_tree_size": data["tree_size"],
        "verification_time": NOW,
    }
    values.update(overrides)
    return verify_transparency_ledger_inclusion(
        data["manifest_bytes"],
        data["entry_bytes"],
        data["proof_bytes"],
        data["checkpoint_bytes"],
        **values,
    )


def rebind_proof(data, proof):
    updated = dict(data)
    updated["proof"] = proof
    updated["proof_bytes"] = canonical(proof)
    document = copy.deepcopy(data["document"])
    document["ledger_anchor"]["inclusion_proof_sha256"] = sha(updated["proof_bytes"])
    updated["document"] = document
    updated["manifest_bytes"] = encode(document)
    return updated


class TransparencyLedgerVerifierV1Tests(unittest.TestCase):
    def test_signed_checkpoint_and_exact_manifest_entry_inclusion_verify(self):
        data = build_fixture()
        result = inspect(data)
        self.assertEqual(result.ledger_id, "EXTERNAL-LEDGER")
        self.assertEqual(result.entry_id, "ENTRY-12390")
        self.assertEqual(result.manifest_sha256, sha(data["manifest_bytes"]))
        self.assertEqual(result.ledger_entry_sha256, sha(data["entry_bytes"]))
        self.assertEqual(result.inclusion_proof_sha256, sha(data["proof_bytes"]))
        self.assertEqual(result.tree_size, 7)
        self.assertEqual(result.leaf_index, 1)
        self.assertTrue(result.checkpoint_signature_verified)
        self.assertTrue(result.inclusion_verified)
        self.assertEqual(result.trust_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.anti_rollback_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.verification_clock_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(
            result.append_only_continuity_status,
            "UNVERIFIED_NO_CONSISTENCY_PROOF",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_rfc6962_audit_path_verifies_every_leaf_across_tree_shapes(self):
        for tree_size in range(1, 65):
            leaves = [
                f"tree-{tree_size}-leaf-{index}".encode("ascii")
                for index in range(tree_size)
            ]
            root = tree_hash(leaves)
            for leaf_index, leaf in enumerate(leaves):
                with self.subTest(tree_size=tree_size, leaf_index=leaf_index):
                    _verify_inclusion(
                        leaf,
                        leaf_index,
                        tree_size,
                        tuple(inclusion_path(leaf_index, leaves)),
                        root,
                    )

    def test_manifest_commitment_excludes_only_the_proof_digest_to_break_cycle(self):
        data = build_fixture()
        changed = copy.deepcopy(data["document"])
        changed["ledger_anchor"]["inclusion_proof_sha256"] = "f" * 64
        self.assertEqual(
            manifest_commitment(changed),
            manifest_commitment(data["document"]),
        )
        changed["ledger_anchor"]["head_sha256"] = sha(b"altered-head")
        self.assertNotEqual(
            manifest_commitment(changed),
            manifest_commitment(data["document"]),
        )

    def test_manifest_claim_mutation_invalidates_ledger_entry_commitment(self):
        data = build_fixture()
        document = copy.deepcopy(data["document"])
        document["artifacts"][0]["source_object_id"] = "ALTERED-SOURCE-OBJECT"
        document["ledger_anchor"]["inclusion_proof_sha256"] = data["document"]["ledger_anchor"]["inclusion_proof_sha256"]
        data["manifest_bytes"] = encode(document)
        with self.assertRaisesRegex(ValueError, "manifest commitment"):
            inspect(data)

    def test_entry_digest_set_must_match_all_manifest_artifacts(self):
        data = build_fixture()
        entry = json.loads(data["entry_bytes"])
        entry["artifact_sha256s"].pop()
        data["entry_bytes"] = canonical(entry)
        with self.assertRaisesRegex(ValueError, "artifact digests do not match manifest"):
            inspect(data)

    def test_entry_must_be_bound_to_manifest_ledger_and_entry_ids(self):
        cases = (
            ("ledger_id", "OTHER-LEDGER", "ledger_id does not match"),
            ("entry_id", "OTHER-ENTRY", "entry_id does not match"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                data = build_fixture()
                entry = json.loads(data["entry_bytes"])
                entry[field] = value
                data["entry_bytes"] = canonical(entry)
                with self.assertRaisesRegex(ValueError, message):
                    inspect(data)

    def test_proof_bytes_must_match_manifest_declared_digest(self):
        data = build_fixture()
        data["proof_bytes"] += b" "
        with self.assertRaisesRegex(ValueError, "proof bytes do not match"):
            inspect(data)

    def test_proof_binds_exact_checkpoint_bytes(self):
        data = build_fixture()
        checkpoint = dict(data["checkpoint"])
        checkpoint["issued_at_utc"] = "2026-11-24T19:01:00Z"
        signature = data["log_private"].sign(
            CHECKPOINT_DOMAIN + canonical({
                key: value for key, value in checkpoint.items()
                if key != "signature_b64"
            })
        )
        checkpoint["signature_b64"] = base64.b64encode(signature).decode("ascii")
        data["checkpoint_bytes"] = canonical(checkpoint)
        with self.assertRaisesRegex(ValueError, "checkpoint digest does not match"):
            inspect(data)

    def test_mutated_audit_path_is_rejected_even_when_proof_digest_is_rebound(self):
        data = build_fixture()
        proof = copy.deepcopy(data["proof"])
        node = bytearray(base64.b64decode(proof["audit_path_b64"][0]))
        node[0] ^= 1
        proof["audit_path_b64"][0] = base64.b64encode(bytes(node)).decode("ascii")
        with self.assertRaisesRegex(ValueError, "not included"):
            inspect(rebind_proof(data, proof))

    def test_incomplete_audit_path_is_rejected(self):
        data = build_fixture()
        proof = copy.deepcopy(data["proof"])
        proof["audit_path_b64"].pop()
        with self.assertRaisesRegex(ValueError, "inclusion proof is incomplete"):
            inspect(rebind_proof(data, proof))

    def test_extra_audit_path_node_is_rejected(self):
        data = build_fixture()
        proof = copy.deepcopy(data["proof"])
        proof["audit_path_b64"].append(base64.b64encode(b"x" * 32).decode("ascii"))
        with self.assertRaisesRegex(ValueError, "extra nodes"):
            inspect(rebind_proof(data, proof))

    def test_wrong_leaf_index_is_rejected(self):
        data = build_fixture()
        proof = copy.deepcopy(data["proof"])
        proof["leaf_index"] = 0
        with self.assertRaisesRegex(ValueError, "not included"):
            inspect(rebind_proof(data, proof))

    def test_wrong_checkpoint_signature_is_rejected(self):
        data = build_fixture()
        checkpoint = dict(data["checkpoint"])
        checkpoint["root_hash"] = sha(b"wrong-root")
        signature = data["log_private"].sign(
            CHECKPOINT_DOMAIN + canonical({
                key: value for key, value in checkpoint.items()
                if key != "signature_b64"
            })
        )
        checkpoint["signature_b64"] = base64.b64encode(signature).decode("ascii")
        data["checkpoint_bytes"] = canonical(checkpoint)
        proof = copy.deepcopy(data["proof"])
        proof["checkpoint_sha256"] = sha(data["checkpoint_bytes"])
        data = rebind_proof(data, proof)
        with self.assertRaisesRegex(ValueError, "not included"):
            inspect(data)

    def test_wrong_log_public_key_is_rejected(self):
        data = build_fixture()
        attacker = Ed25519PrivateKey.from_private_bytes(b"\x20" * 32)
        with self.assertRaisesRegex(ValueError, "checkpoint signature verification failed"):
            inspect(data, pinned_log_public_key_bytes=public_bytes(attacker))

    def test_wrong_expected_log_id_is_rejected(self):
        data = build_fixture()
        with self.assertRaisesRegex(ValueError, "log_id does not match"):
            inspect(data, expected_log_id="OTHER-LOG")

    def test_wrong_expected_key_id_is_rejected(self):
        data = build_fixture()
        with self.assertRaisesRegex(ValueError, "key_id does not match"):
            inspect(data, expected_key_id="OTHER-KEY")

    def test_tree_size_below_external_floor_is_rejected(self):
        data = build_fixture()
        with self.assertRaisesRegex(ValueError, "below the caller-supplied monotonic floor"):
            inspect(data, minimum_tree_size=data["tree_size"] + 1)

    def test_checkpoint_after_supplied_verification_time_is_rejected(self):
        data = build_fixture()
        with self.assertRaisesRegex(ValueError, "later than supplied verification time"):
            inspect(data, verification_time=datetime(2026, 11, 24, 18, 0, tzinfo=timezone.utc))

    def test_boolean_tree_size_is_not_an_integer(self):
        data = build_fixture()
        checkpoint = dict(data["checkpoint"])
        checkpoint["tree_size"] = True
        unsigned = {key: value for key, value in checkpoint.items() if key != "signature_b64"}
        checkpoint["signature_b64"] = base64.b64encode(
            data["log_private"].sign(CHECKPOINT_DOMAIN + canonical(unsigned))
        ).decode("ascii")
        data["checkpoint_bytes"] = canonical(checkpoint)
        proof = copy.deepcopy(data["proof"])
        proof["checkpoint_sha256"] = sha(data["checkpoint_bytes"])
        data = rebind_proof(data, proof)
        with self.assertRaisesRegex(ValueError, "tree_size must be a positive"):
            inspect(data)

    def test_noncanonical_checkpoint_json_is_rejected(self):
        data = build_fixture()
        data["checkpoint_bytes"] = json.dumps(
            data["checkpoint"], sort_keys=False, separators=(",", ":")
        ).encode("utf-8")
        proof = copy.deepcopy(data["proof"])
        proof["checkpoint_sha256"] = sha(data["checkpoint_bytes"])
        data = rebind_proof(data, proof)
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 JSON"):
            inspect(data)

    def test_duplicate_json_key_in_proof_is_rejected_after_manifest_rebind(self):
        data = build_fixture()
        raw = (
            b'{"schema_version":"' + PROOF_SCHEMA.encode("ascii")
            + b'","schema_version":"' + PROOF_SCHEMA.encode("ascii")
            + b'"}'
        )
        data["proof_bytes"] = raw
        document = copy.deepcopy(data["document"])
        document["ledger_anchor"]["inclusion_proof_sha256"] = sha(raw)
        data["manifest_bytes"] = encode(document)
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            inspect(data)

    def test_provenance_never_promotes_after_valid_inclusion(self):
        data = build_fixture()
        result = inspect(data)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn("APPEND_ONLY_CONSISTENCY_NOT_VERIFIED", result.remaining_blockers)
        self.assertIn("LOG_SIGNING_KEY_NOT_INDEPENDENTLY_PROVISIONED", result.remaining_blockers)


if __name__ == "__main__":
    unittest.main()
