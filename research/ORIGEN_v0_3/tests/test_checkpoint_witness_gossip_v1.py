from __future__ import annotations

import base64
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.checkpoint_witness_gossip_v1 import (
    WitnessObservationBatch,
    inspect_witness_gossip,
)
from origen.independent_trust_adapter import ProvenanceStatus
from test_checkpoint_witness_quorum_v1 import (
    REGISTRY_DOMAIN,
    REGISTRY_ID,
    REGISTRY_SCHEMA,
    ROOT_KEY_ID,
    ROOT_PRIVATE,
    WITNESS_DOMAIN,
    WITNESS_PRIVATE,
    WITNESS_SCHEMA,
    signed_registry,
    signed_statements,
)
from test_transparency_checkpoint_consistency_v1 import (
    CONSISTENCY_PROOF_SCHEMA,
    KEY_ID,
    LOG_ID,
    NOW,
    build_pair,
    canonical,
    consistency_path,
    public_bytes,
    sha,
    signed_checkpoint,
)


def forked_pair():
    """Create a valid alternate append-only history with the same size 3 -> 9."""
    private_key = Ed25519PrivateKey.from_private_bytes(bytes([0x2A]) * 32)
    old_leaves = [f"leaf-{index}".encode("ascii") for index in range(3)]
    new_leaves = old_leaves + [
        f"alternate-leaf-{index}".encode("ascii") for index in range(3, 9)
    ]
    old_checkpoint, old_bytes = signed_checkpoint(
        private_key, old_leaves, issued_at="2026-11-24T19:00:00Z"
    )
    new_checkpoint, new_bytes = signed_checkpoint(
        private_key, new_leaves, issued_at="2026-11-24T19:01:00Z"
    )
    path = consistency_path(3, new_leaves, True)
    proof = {
        "schema_version": CONSISTENCY_PROOF_SCHEMA,
        "log_id": LOG_ID,
        "old_checkpoint_sha256": sha(old_bytes),
        "new_checkpoint_sha256": sha(new_bytes),
        "old_tree_size": 3,
        "new_tree_size": 9,
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


def signed_registry_four():
    keys = dict(WITNESS_PRIVATE)
    keys["witness-4"] = Ed25519PrivateKey.from_private_bytes(bytes([0x64]) * 32)
    witnesses = []
    for index, witness_id in enumerate(sorted(keys), start=1):
        witnesses.append({
            "witness_id": witness_id,
            "key_id": f"KEY-{index}",
            "public_key_b64": base64.b64encode(
                public_bytes(keys[witness_id])
            ).decode("ascii"),
            "valid_from_utc": "2026-11-24T18:00:00Z",
            "valid_until_utc": "2026-11-25T18:00:00Z",
            "revoked": False,
        })
    unsigned = {
        "schema_version": REGISTRY_SCHEMA,
        "registry_id": REGISTRY_ID,
        "registry_sequence": 7,
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-24T18:30:00Z",
        "not_before_utc": "2026-11-24T18:45:00Z",
        "expires_at_utc": "2026-11-25T18:30:00Z",
        "log_id": LOG_ID,
        "minimum_witness_quorum": 2,
        "maximum_witness_age_seconds": 3600,
        "maximum_witness_time_skew_seconds": 60,
        "witnesses": witnesses,
    }
    signature = ROOT_PRIVATE.sign(REGISTRY_DOMAIN + canonical(unsigned))
    document = dict(unsigned)
    document["signature_b64"] = base64.b64encode(signature).decode("ascii")
    return document, canonical(document), keys


def signed_statements_four(data, registry, registry_bytes, witness_ids, keys):
    registry_digest = sha(registry_bytes)
    result = []
    for witness_id in witness_ids:
        index = int(witness_id.rsplit("-", 1)[1])
        unsigned = {
            "schema_version": WITNESS_SCHEMA,
            "registry_id": REGISTRY_ID,
            "registry_sequence": registry["registry_sequence"],
            "registry_sha256": registry_digest,
            "witness_id": witness_id,
            "key_id": f"KEY-{index}",
            "log_id": LOG_ID,
            "old_checkpoint_sha256": sha(data["old_bytes"]),
            "new_checkpoint_sha256": sha(data["new_bytes"]),
            "old_tree_size": data["proof"]["old_tree_size"],
            "new_tree_size": data["proof"]["new_tree_size"],
            "old_root_sha256": data["old_checkpoint"]["root_hash"],
            "new_root_sha256": data["new_checkpoint"]["root_hash"],
            "consistency_proof_sha256": sha(data["proof_bytes"]),
            "issued_at_utc": "2026-11-24T19:02:00Z",
        }
        signature = keys[witness_id].sign(WITNESS_DOMAIN + canonical(unsigned))
        statement = dict(unsigned)
        statement["signature_b64"] = base64.b64encode(signature).decode("ascii")
        result.append(canonical(statement))
    return tuple(result)


def make_batch(data, registry_bytes, witness_ids=("witness-1", "witness-2"),
               issued_at_by_id=None, invalid_signature_for=None):
    registry = json.loads(registry_bytes.decode("utf-8"))
    statements = signed_statements(
        data,
        registry,
        registry_bytes,
        witness_ids,
        issued_at_by_id=issued_at_by_id,
        invalid_signature_for=invalid_signature_for,
    )
    return WitnessObservationBatch(
        raw_registry_bytes=registry_bytes,
        raw_old_checkpoint_bytes=data["old_bytes"],
        raw_new_checkpoint_bytes=data["new_bytes"],
        raw_consistency_proof_bytes=data["proof_bytes"],
        raw_witness_statement_bytes=tuple(statements),
    )


def make_batch_from_statements(data, registry_bytes, statements):
    return WitnessObservationBatch(
        raw_registry_bytes=registry_bytes,
        raw_old_checkpoint_bytes=data["old_bytes"],
        raw_new_checkpoint_bytes=data["new_bytes"],
        raw_consistency_proof_bytes=data["proof_bytes"],
        raw_witness_statement_bytes=tuple(statements),
    )


def inspect(batches, **overrides):
    kwargs = {
        "pinned_registry_root_public_key_bytes": public_bytes(ROOT_PRIVATE),
        "expected_registry_root_key_id": ROOT_KEY_ID,
        "expected_registry_id": REGISTRY_ID,
        "minimum_registry_sequence": 7,
        "pinned_log_public_key_bytes": build_pair(3, 9)["public_key"],
        "expected_log_id": LOG_ID,
        "expected_log_key_id": KEY_ID,
        "minimum_new_tree_size": 1,
        "verification_time": NOW,
    }
    kwargs.update(overrides)
    return inspect_witness_gossip(batches, **kwargs)


class WitnessGossipComparisonV1Tests(unittest.TestCase):
    def setUp(self):
        self.registry, self.registry_bytes = signed_registry()
        self.first_pair = build_pair(3, 9)
        self.first_batch = make_batch(
            self.first_pair, self.registry_bytes
        )

    def test_adjacent_append_only_batches_have_no_observed_conflict(self):
        second_pair = build_pair(
            9,
            12,
            old_issued_at="2026-11-24T19:01:00Z",
            new_issued_at="2026-11-24T19:03:00Z",
        )
        second_batch = make_batch(
            second_pair,
            self.registry_bytes,
            witness_ids=("witness-2", "witness-3"),
            issued_at_by_id={
                "witness-2": "2026-11-24T19:04:00Z",
                "witness-3": "2026-11-24T19:04:00Z",
            },
        )
        result = inspect((self.first_batch, second_batch))
        self.assertFalse(result.split_view_detected)
        self.assertFalse(result.witness_equivocation_detected)
        self.assertEqual(
            result.comparison_status,
            "NO_CONFLICT_FOUND_IN_SUPPLIED_BATCHES_NOT_GLOBAL_PROOF",
        )
        self.assertEqual(result.batch_count, 2)
        self.assertEqual(result.registry_sequences, (7,))
        self.assertGreater(result.compared_checkpoint_observation_count, 0)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_same_size_conflicting_roots_detect_split_view_and_key_equivocation(self):
        alternate_pair = forked_pair()
        alternate_batch = make_batch(
            alternate_pair,
            self.registry_bytes,
            witness_ids=("witness-2", "witness-3"),
        )
        result = inspect((self.first_batch, alternate_batch))
        self.assertTrue(result.split_view_detected)
        self.assertTrue(result.witness_equivocation_detected)
        self.assertEqual(
            result.comparison_status,
            "SPLIT_VIEW_DETECTED_IN_SUPPLIED_BATCHES",
        )
        finding = next(item for item in result.findings if item.tree_size == 9)
        self.assertEqual(len(finding.conflicting_root_sha256), 2)
        self.assertEqual(len(finding.equivocating_witness_key_sha256), 1)
        self.assertEqual(finding.batch_indexes, (0, 1))
        self.assertEqual(finding.witness_ids, ("witness-1", "witness-2", "witness-3"))

    def test_conflicting_views_from_disjoint_witnesses_still_detect_split_view(self):
        registry, registry_bytes, keys = signed_registry_four()
        first_statements = signed_statements_four(
            self.first_pair, registry, registry_bytes,
            ("witness-1", "witness-2"), keys,
        )
        alternate_statements = signed_statements_four(
            forked_pair(), registry, registry_bytes,
            ("witness-3", "witness-4"), keys,
        )
        first = make_batch_from_statements(
            self.first_pair, registry_bytes, first_statements
        )
        alternate = make_batch_from_statements(
            forked_pair(), registry_bytes, alternate_statements
        )
        result = inspect((first, alternate))
        self.assertTrue(result.split_view_detected)
        self.assertFalse(result.witness_equivocation_detected)
        finding = next(item for item in result.findings if item.tree_size == 9)
        self.assertEqual(len(finding.conflicting_root_sha256), 2)
        self.assertEqual(finding.equivocating_witness_key_sha256, ())
        self.assertEqual(
            finding.witness_ids,
            ("witness-1", "witness-2", "witness-3", "witness-4"),
        )

    def test_invalid_statement_in_any_batch_fails_the_entire_comparison(self):
        invalid = make_batch(
            self.first_pair,
            self.registry_bytes,
            invalid_signature_for="witness-1",
        )
        with self.assertRaisesRegex(ValueError, "Ed25519 signature verification failed"):
            inspect((invalid, self.first_batch))

    def test_duplicate_batch_is_not_counted_as_additional_gossip_evidence(self):
        with self.assertRaisesRegex(ValueError, "duplicate observation batch"):
            inspect((self.first_batch, self.first_batch))

    def test_single_batch_cannot_claim_cross_batch_comparison(self):
        with self.assertRaisesRegex(ValueError, "must contain 2"):
            inspect((self.first_batch,))

    def test_transport_wrapper_and_statement_container_types_are_exact(self):
        with self.assertRaisesRegex(TypeError, "exact WitnessObservationBatch"):
            inspect((object(), self.first_batch))
        invalid_container = WitnessObservationBatch(
            raw_registry_bytes=self.first_batch.raw_registry_bytes,
            raw_old_checkpoint_bytes=self.first_batch.raw_old_checkpoint_bytes,
            raw_new_checkpoint_bytes=self.first_batch.raw_new_checkpoint_bytes,
            raw_consistency_proof_bytes=self.first_batch.raw_consistency_proof_bytes,
            raw_witness_statement_bytes=list(self.first_batch.raw_witness_statement_bytes),
        )
        with self.assertRaisesRegex(TypeError, "exact tuple"):
            inspect((invalid_container, self.first_batch))

    def test_results_never_claim_global_gossip_or_authenticated_provenance(self):
        second_pair = build_pair(
            9,
            12,
            old_issued_at="2026-11-24T19:01:00Z",
            new_issued_at="2026-11-24T19:03:00Z",
        )
        second_batch = make_batch(
            second_pair,
            self.registry_bytes,
            witness_ids=("witness-2", "witness-3"),
            issued_at_by_id={
                "witness-2": "2026-11-24T19:04:00Z",
                "witness-3": "2026-11-24T19:04:00Z",
            },
        )
        result = inspect((self.first_batch, second_batch))
        self.assertEqual(result.observation_scope, "SUPPLIED_VERIFIED_BATCHES_ONLY")
        self.assertEqual(result.persistence_status, "NOT_PERSISTED_BY_THIS_MODULE")
        self.assertEqual(result.trust_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.registry_sequence_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.verification_clock_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn(
            "NETWORK_GOSSIP_AND_GLOBAL_SPLIT_VIEW_DETECTION_NOT_ESTABLISHED",
            result.remaining_blockers,
        )


if __name__ == "__main__":
    unittest.main()
