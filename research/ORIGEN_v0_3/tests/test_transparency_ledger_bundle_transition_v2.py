from __future__ import annotations

import base64
import json
import unittest

from origen.independent_trust_adapter import ProvenanceStatus
from origen.transparency_ledger_bundle_transition_v2 import (
    verify_transparency_ledger_bundle_transition_v2,
)
from test_custody_ledger_witness_integration_v1 import _build_case
from test_physical_evidence_manifest_v1 import encode
from test_transparency_checkpoint_consistency_v1 import (
    CONSISTENCY_PROOF_SCHEMA,
    consistency_path,
    signed_checkpoint,
    tree_hash,
)
from test_transparency_ledger_bundle_verifier_v2 import build_v2_case, canonical, sha


def build_transition_case():
    values, entry = build_v2_case()
    _, previous_ledger, _, _ = _build_case()
    leaves = list(previous_ledger["leaves"])
    leaves[1] = canonical(entry)
    log_private = previous_ledger["log_private"]

    _, new_checkpoint_bytes = signed_checkpoint(
        log_private,
        leaves,
        issued_at="2026-11-23T03:10:00Z",
    )
    _, old_checkpoint_bytes = signed_checkpoint(
        log_private,
        leaves[:1],
        issued_at="2026-11-23T02:58:00Z",
    )
    consistency = {
        "schema_version": CONSISTENCY_PROOF_SCHEMA,
        "log_id": "SYNTHETIC-TRANSPARENCY-LOG",
        "old_checkpoint_sha256": sha(old_checkpoint_bytes),
        "new_checkpoint_sha256": sha(new_checkpoint_bytes),
        "old_tree_size": 1,
        "new_tree_size": len(leaves),
        "consistency_path_b64": [
            base64.b64encode(node).decode("ascii")
            for node in consistency_path(1, leaves, True)
        ],
    }

    inclusion = json.loads(values["raw_inclusion_proof_bytes"].decode("utf-8"))
    inclusion["checkpoint_sha256"] = sha(new_checkpoint_bytes)
    inclusion_bytes = canonical(inclusion)
    manifest = json.loads(values["raw_manifest_bytes"].decode("utf-8"))
    manifest["ledger_anchor"]["inclusion_proof_sha256"] = sha(inclusion_bytes)

    values.update({
        "raw_manifest_bytes": encode(manifest),
        "raw_inclusion_proof_bytes": inclusion_bytes,
        "raw_signed_checkpoint_bytes": new_checkpoint_bytes,
        "raw_old_checkpoint_bytes": old_checkpoint_bytes,
        "raw_consistency_proof_bytes": canonical(consistency),
        "expected_old_tree_size": 1,
        "expected_old_root_sha256": tree_hash(leaves[:1]).hex(),
        "expected_old_checkpoint_sha256": sha(old_checkpoint_bytes),
    })
    return values


class TransparencyLedgerBundleTransitionV2Tests(unittest.TestCase):
    def test_v2_inclusion_and_consistency_bind_same_new_checkpoint_and_old_watermark(self):
        result = verify_transparency_ledger_bundle_transition_v2(**build_transition_case())
        self.assertTrue(result.inclusion.inclusion_verified)
        self.assertTrue(result.inclusion.timestamp_bundle_bytes_verified)
        self.assertTrue(result.inclusion.timestamp_token_digest_committed)
        self.assertTrue(result.checkpoint_consistency.checkpoint_signatures_verified)
        self.assertTrue(result.checkpoint_consistency.consistency_verified)
        self.assertEqual(
            result.inclusion.checkpoint_sha256,
            result.checkpoint_consistency.new_checkpoint_sha256,
        )
        self.assertEqual(result.accepted_old_tree_size, 1)
        self.assertEqual(result.checkpoint_consistency.new_tree_size, 7)
        self.assertEqual(
            result.append_only_continuity_status,
            "CONSISTENCY_VERIFIED_WITNESS_QUORUM_UNVERIFIED",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_old_checkpoint_digest_must_match_accepted_watermark(self):
        values = build_transition_case()
        values["expected_old_checkpoint_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "old checkpoint digest does not match"):
            verify_transparency_ledger_bundle_transition_v2(**values)

    def test_old_checkpoint_tree_size_must_match_accepted_watermark(self):
        values = build_transition_case()
        values["expected_old_tree_size"] = 2
        with self.assertRaisesRegex(ValueError, "tree size does not match"):
            verify_transparency_ledger_bundle_transition_v2(**values)

    def test_old_checkpoint_root_must_match_accepted_watermark(self):
        values = build_transition_case()
        values["expected_old_root_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "root does not match"):
            verify_transparency_ledger_bundle_transition_v2(**values)

    def test_tampered_consistency_node_is_rejected(self):
        values = build_transition_case()
        proof = json.loads(values["raw_consistency_proof_bytes"].decode("utf-8"))
        node = bytearray(base64.b64decode(proof["consistency_path_b64"][0]))
        node[0] ^= 1
        proof["consistency_path_b64"][0] = base64.b64encode(bytes(node)).decode("ascii")
        values["raw_consistency_proof_bytes"] = canonical(proof)
        with self.assertRaisesRegex(ValueError, "does not establish append-only"):
            verify_transparency_ledger_bundle_transition_v2(**values)

    def test_equal_size_checkpoint_is_not_an_evidence_advance(self):
        values = build_transition_case()
        checkpoint_bytes = values["raw_signed_checkpoint_bytes"]
        checkpoint = json.loads(checkpoint_bytes.decode("utf-8"))
        checkpoint_sha256 = sha(checkpoint_bytes)
        proof = {
            "schema_version": CONSISTENCY_PROOF_SCHEMA,
            "log_id": "SYNTHETIC-TRANSPARENCY-LOG",
            "old_checkpoint_sha256": checkpoint_sha256,
            "new_checkpoint_sha256": checkpoint_sha256,
            "old_tree_size": 7,
            "new_tree_size": 7,
            "consistency_path_b64": [],
        }
        values.update({
            "raw_old_checkpoint_bytes": checkpoint_bytes,
            "raw_consistency_proof_bytes": canonical(proof),
            "expected_old_tree_size": 7,
            "expected_old_root_sha256": checkpoint["root_hash"],
            "expected_old_checkpoint_sha256": checkpoint_sha256,
        })
        with self.assertRaisesRegex(ValueError, "strictly advance"):
            verify_transparency_ledger_bundle_transition_v2(**values)


if __name__ == "__main__":
    unittest.main()
