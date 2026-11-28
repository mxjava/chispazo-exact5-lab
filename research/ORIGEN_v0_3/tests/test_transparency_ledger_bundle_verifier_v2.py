from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest

from origen.independent_trust_adapter import ProvenanceStatus
from origen.nested_signature_bundle_timestamp_v1 import (
    canonical_nested_signature_bundle_timestamp_payload_v1,
)
from origen.transparency_ledger_bundle_verifier_v2 import (
    ENTRY_SCHEMA_V2,
    verify_transparency_ledger_bundle_inclusion_v2,
)
from origen.transparency_ledger_verifier_v1 import (
    CHECKPOINT_DOMAIN,
    CHECKPOINT_SCHEMA,
    PROOF_SCHEMA,
    _manifest_commitment_sha256,
)
from test_custody_ledger_witness_integration_v1 import _build_case
from test_physical_evidence_manifest_v1 import encode
from test_rfc3161_tsa_verifier_v1 import _token
from test_transparency_checkpoint_consistency_v1 import NOW
from test_transparency_ledger_verifier_v1 import (
    LOG_ID as LEDGER_LOG_ID,
    LOG_KEY_ID,
    canonical,
    inclusion_path,
    sha,
    tree_hash,
)

PRE_CLOSE = __import__("datetime").datetime(
    2026, 11, 23, 2, 59, 50, tzinfo=__import__("datetime").timezone.utc
)


def build_v2_case():
    data, old_ledger, _, _ = _build_case()
    raw_manifest_before_proof = old_ledger["manifest_bytes"]
    bundle_bytes = canonical_nested_signature_bundle_timestamp_payload_v1(
        raw_manifest_before_proof,
        data["signed_policy_envelope_bytes"],
        data["artifact_bytes_by_sha256"],
        data["signature_bytes_by_sha256"],
    )
    token, tsa_root = _token(
        data=bundle_bytes,
        nonce=88091,
        gen_time=PRE_CLOSE,
        accuracy={"millis": 250},
    )

    document = copy.deepcopy(old_ledger["document"])
    manifest_commitment = _manifest_commitment_sha256(raw_manifest_before_proof)
    artifact_sha256s = sorted(item["sha256"] for item in document["artifacts"])
    entry = {
        "schema_version": ENTRY_SCHEMA_V2,
        "ledger_id": document["ledger_anchor"]["ledger_id"],
        "entry_id": document["ledger_anchor"]["entry_id"],
        "manifest_commitment_sha256": manifest_commitment,
        "artifact_sha256s": artifact_sha256s,
        "timestamp_bundle_sha256": sha(bundle_bytes),
        "timestamp_token_sha256": sha(token),
    }
    entry_bytes = canonical(entry)

    leaves = list(old_ledger["leaves"])
    leaves[1] = entry_bytes
    root_hash = tree_hash(leaves)
    unsigned_checkpoint = {
        "schema_version": CHECKPOINT_SCHEMA,
        "log_id": LEDGER_LOG_ID,
        "key_id": LOG_KEY_ID,
        "tree_size": len(leaves),
        "root_hash": root_hash.hex(),
        "issued_at_utc": "2026-11-23T03:10:00Z",
    }
    signature = old_ledger["log_private"].sign(
        CHECKPOINT_DOMAIN + canonical(unsigned_checkpoint)
    )
    checkpoint = dict(unsigned_checkpoint)
    checkpoint["signature_b64"] = base64.b64encode(signature).decode("ascii")
    checkpoint_bytes = canonical(checkpoint)

    proof = {
        "schema_version": PROOF_SCHEMA,
        "ledger_id": document["ledger_anchor"]["ledger_id"],
        "entry_id": document["ledger_anchor"]["entry_id"],
        "log_id": LEDGER_LOG_ID,
        "leaf_index": 1,
        "checkpoint_sha256": sha(checkpoint_bytes),
        "audit_path_b64": [
            base64.b64encode(node).decode("ascii")
            for node in inclusion_path(1, leaves)
        ],
    }
    proof_bytes = canonical(proof)
    document["ledger_anchor"]["inclusion_proof_sha256"] = sha(proof_bytes)
    manifest_bytes = encode(document)

    values = {
        "raw_manifest_bytes": manifest_bytes,
        "raw_ledger_entry_bytes": entry_bytes,
        "raw_inclusion_proof_bytes": proof_bytes,
        "raw_signed_checkpoint_bytes": checkpoint_bytes,
        "raw_timestamp_bundle_bytes": bundle_bytes,
        "timestamp_token_der": token,
        "signed_policy_envelope_bytes": data["signed_policy_envelope_bytes"],
        "artifact_bytes_by_sha256": data["artifact_bytes_by_sha256"],
        "signature_bytes_by_sha256": data["signature_bytes_by_sha256"],
        "pinned_log_public_key_bytes": old_ledger["log_public"],
        "expected_log_id": LEDGER_LOG_ID,
        "expected_log_key_id": LOG_KEY_ID,
        "minimum_tree_size": len(leaves),
        "pinned_root_public_key_bytes": data["pinned_root_public_key_bytes"],
        "expected_root_key_id": data["expected_root_key_id"],
        "minimum_policy_sequence": data["minimum_policy_sequence"],
        "pinned_tsa_root_certificate_der": tsa_root,
        "expected_tsa_root_sha256": sha(tsa_root),
        "expected_tsa_policy_oid": "1.2.3.4.5",
        "expected_nonce": 88091,
        "verification_time": NOW,
    }
    return values, entry


class TransparencyLedgerBundleVerifierV2Tests(unittest.TestCase):
    def test_v2_leaf_commits_exact_bundle_and_token_and_inclusion_verifies(self):
        values, entry = build_v2_case()
        result = verify_transparency_ledger_bundle_inclusion_v2(**values)

        self.assertEqual(result.timestamp_bundle_sha256, entry["timestamp_bundle_sha256"])
        self.assertEqual(result.timestamp_token_sha256, entry["timestamp_token_sha256"])
        self.assertTrue(result.timestamp_bundle_bytes_verified)
        self.assertTrue(result.timestamp_bundle_digest_committed)
        self.assertTrue(result.timestamp_token_digest_committed)
        self.assertTrue(result.timestamp_existence_preclose_verified)
        self.assertTrue(result.checkpoint_signature_verified)
        self.assertTrue(result.inclusion_verified)
        self.assertEqual(result.tree_size, 7)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(
            result.append_only_continuity_status,
            "UNVERIFIED_NO_CONSISTENCY_PROOF_OR_INDEPENDENT_WITNESS",
        )

    def test_ledger_entry_cannot_substitute_timestamp_bundle_digest(self):
        values, entry = build_v2_case()
        altered = dict(entry)
        altered["timestamp_bundle_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not commit to the exact timestamp bundle"):
            verify_transparency_ledger_bundle_inclusion_v2(
                **{**values, "raw_ledger_entry_bytes": canonical(altered)}
            )

    def test_ledger_entry_cannot_substitute_timestamp_token_digest(self):
        values, entry = build_v2_case()
        altered = dict(entry)
        altered["timestamp_token_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not commit to the exact RFC 3161 token"):
            verify_transparency_ledger_bundle_inclusion_v2(
                **{**values, "raw_ledger_entry_bytes": canonical(altered)}
            )

    def test_supplied_bundle_must_equal_rebuilt_exact_evidence_sidecar(self):
        values, _ = build_v2_case()
        with self.assertRaisesRegex(ValueError, "do not equal the canonical exact-evidence sidecar"):
            verify_transparency_ledger_bundle_inclusion_v2(
                **{**values, "raw_timestamp_bundle_bytes": values["raw_timestamp_bundle_bytes"] + b" "}
            )

    def test_v1_ledger_entry_is_not_accepted_as_a_timestamp_committing_leaf(self):
        values, entry = build_v2_case()
        legacy = dict(entry)
        legacy["schema_version"] = "origen.transparency-ledger-entry.v1"
        with self.assertRaisesRegex(ValueError, "V2 timestamp commitment is required"):
            verify_transparency_ledger_bundle_inclusion_v2(
                **{**values, "raw_ledger_entry_bytes": canonical(legacy)}
            )

    def test_manifest_proof_digest_still_binds_exact_inclusion_proof_bytes(self):
        values, _ = build_v2_case()
        document = json.loads(values["raw_manifest_bytes"].decode("utf-8"))
        document["ledger_anchor"]["inclusion_proof_sha256"] = "f" * 64
        changed_manifest = encode(document)
        with self.assertRaisesRegex(ValueError, "exact inclusion-proof bytes"):
            verify_transparency_ledger_bundle_inclusion_v2(
                **{**values, "raw_manifest_bytes": changed_manifest}
            )

    def test_mutated_inclusion_path_is_rejected_after_proof_digest_is_rebound(self):
        values, _ = build_v2_case()
        proof = json.loads(values["raw_inclusion_proof_bytes"].decode("utf-8"))
        node = bytearray(base64.b64decode(proof["audit_path_b64"][0]))
        node[0] ^= 1
        proof["audit_path_b64"][0] = base64.b64encode(bytes(node)).decode("ascii")
        proof_bytes = canonical(proof)
        document = json.loads(values["raw_manifest_bytes"].decode("utf-8"))
        document["ledger_anchor"]["inclusion_proof_sha256"] = sha(proof_bytes)
        changed = {
            **values,
            "raw_manifest_bytes": encode(document),
            "raw_inclusion_proof_bytes": proof_bytes,
        }
        with self.assertRaisesRegex(ValueError, "not included"):
            verify_transparency_ledger_bundle_inclusion_v2(**changed)


if __name__ == "__main__":
    unittest.main()
