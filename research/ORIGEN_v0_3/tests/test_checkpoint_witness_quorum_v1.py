from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.checkpoint_witness_quorum_v1 import (
    REGISTRY_DOMAIN,
    REGISTRY_SCHEMA,
    WITNESS_DOMAIN,
    WITNESS_SCHEMA,
    verify_checkpoint_witness_quorum,
    verify_signed_witness_registry,
)
from test_transparency_checkpoint_consistency_v1 import (
    KEY_ID,
    LOG_ID,
    NOW,
    build_pair,
    canonical,
    public_bytes,
    sha,
)

REGISTRY_ID = "SYNTHETIC-WITNESS-REGISTRY"
ROOT_KEY_ID = "SYNTHETIC-WITNESS-ROOT"
ROOT_PRIVATE = Ed25519PrivateKey.from_private_bytes(b"\x51" * 32)
WITNESS_PRIVATE = {
    f"witness-{index}": Ed25519PrivateKey.from_private_bytes(bytes([0x60 + index]) * 32)
    for index in range(1, 4)
}


def signed_registry(
    *,
    quorum: int = 2,
    sequence: int = 7,
    revoked: tuple[str, ...] = (),
    duplicate_public_key: bool = False,
    public_key_overrides: dict[str, bytes] | None = None,
    issued_at: str = "2026-11-24T18:30:00Z",
    not_before: str = "2026-11-24T18:45:00Z",
    expires_at: str = "2026-11-25T18:30:00Z",
) -> tuple[dict, bytes]:
    witnesses = []
    public_key_overrides = public_key_overrides or {}
    for index, (witness_id, private_key) in enumerate(WITNESS_PRIVATE.items(), start=1):
        key_bytes = public_key_overrides.get(witness_id, public_bytes(private_key))
        if duplicate_public_key and index == 2:
            key_bytes = public_bytes(WITNESS_PRIVATE["witness-1"])
        witnesses.append({
            "witness_id": witness_id,
            "key_id": f"KEY-{index}",
            "public_key_b64": base64.b64encode(key_bytes).decode("ascii"),
            "valid_from_utc": "2026-11-24T18:00:00Z",
            "valid_until_utc": "2026-11-25T18:00:00Z",
            "revoked": witness_id in revoked,
        })
    unsigned = {
        "schema_version": REGISTRY_SCHEMA,
        "registry_id": REGISTRY_ID,
        "registry_sequence": sequence,
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": issued_at,
        "not_before_utc": not_before,
        "expires_at_utc": expires_at,
        "log_id": LOG_ID,
        "minimum_witness_quorum": quorum,
        "maximum_witness_age_seconds": 3600,
        "maximum_witness_time_skew_seconds": 60,
        "witnesses": witnesses,
    }
    signature = ROOT_PRIVATE.sign(REGISTRY_DOMAIN + canonical(unsigned))
    document = dict(unsigned)
    document["signature_b64"] = base64.b64encode(signature).decode("ascii")
    return document, canonical(document)


def signed_statements(
    data: dict,
    registry: dict,
    registry_bytes: bytes,
    witness_ids: tuple[str, ...] = ("witness-1", "witness-2"),
    *,
    issued_at_by_id: dict[str, str] | None = None,
    mutate_by_id: dict[str, dict] | None = None,
    invalid_signature_for: str | None = None,
    private_key_overrides: dict[str, Ed25519PrivateKey] | None = None,
) -> list[bytes]:
    issued_at_by_id = issued_at_by_id or {}
    mutate_by_id = mutate_by_id or {}
    private_key_overrides = private_key_overrides or {}
    registry_sha = sha(registry_bytes)
    result = []
    for witness_id in witness_ids:
        index = int(witness_id.rsplit("-", 1)[1])
        unsigned = {
            "schema_version": WITNESS_SCHEMA,
            "registry_id": REGISTRY_ID,
            "registry_sequence": registry["registry_sequence"],
            "registry_sha256": registry_sha,
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
            "issued_at_utc": issued_at_by_id.get(
                witness_id, "2026-11-24T19:02:00Z"
            ),
        }
        unsigned.update(mutate_by_id.get(witness_id, {}))
        signer = private_key_overrides.get(witness_id, WITNESS_PRIVATE[witness_id])
        signature = signer.sign(WITNESS_DOMAIN + canonical(unsigned))
        if witness_id == invalid_signature_for:
            signature = b"\x00" * 64
        statement = dict(unsigned)
        statement["signature_b64"] = base64.b64encode(signature).decode("ascii")
        result.append(canonical(statement))
    return result


def inspect(
    data: dict,
    registry_bytes: bytes,
    statements: list[bytes],
    **overrides,
):
    kwargs = {
        "pinned_registry_root_public_key_bytes": public_bytes(ROOT_PRIVATE),
        "expected_registry_root_key_id": ROOT_KEY_ID,
        "expected_registry_id": REGISTRY_ID,
        "minimum_registry_sequence": 7,
        "pinned_log_public_key_bytes": data["public_key"],
        "expected_log_id": LOG_ID,
        "expected_log_key_id": KEY_ID,
        "minimum_new_tree_size": data["proof"]["new_tree_size"],
        "verification_time": NOW,
    }
    kwargs.update(overrides)
    return verify_checkpoint_witness_quorum(
        registry_bytes,
        statements,
        data["old_bytes"],
        data["new_bytes"],
        data["proof_bytes"],
        **kwargs,
    )


class CheckpointWitnessQuorumV1Tests(unittest.TestCase):
    def setUp(self):
        self.checkpoints = build_pair(3, 9)
        self.registry, self.registry_bytes = signed_registry()
        self.statements = signed_statements(
            self.checkpoints, self.registry, self.registry_bytes
        )

    def test_valid_distinct_witness_quorum_verifies_exact_checkpoint_pair(self):
        result = inspect(self.checkpoints, self.registry_bytes, self.statements)
        self.assertTrue(result.witness_quorum_verified)
        self.assertEqual(result.witness_quorum_required, 2)
        self.assertEqual(result.witness_quorum_observed, 2)
        self.assertEqual(result.agreeing_witness_ids, ("witness-1", "witness-2"))
        self.assertEqual(
            result.agreement_status,
            "QUORUM_AGREES_ON_EXACT_CHECKPOINT_AND_CONSISTENCY_PROOF",
        )
        self.assertEqual(
            result.split_view_detection_status,
            "CROSS_BATCH_GOSSIP_NOT_VERIFIED",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_valid_three_witness_quorum_is_accepted(self):
        statements = signed_statements(
            self.checkpoints, self.registry, self.registry_bytes,
            ("witness-1", "witness-2", "witness-3"),
        )
        result = inspect(self.checkpoints, self.registry_bytes, statements)
        self.assertEqual(result.witness_quorum_observed, 3)

    def test_insufficient_quorum_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "quorum threshold was not met"):
            inspect(self.checkpoints, self.registry_bytes, self.statements[:1])

    def test_duplicate_witness_identity_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate witness identity"):
            inspect(
                self.checkpoints,
                self.registry_bytes,
                [self.statements[0], self.statements[0]],
            )

    def test_duplicate_key_identity_is_rejected_by_signed_registry(self):
        registry, raw = signed_registry(duplicate_public_key=True)
        statements = signed_statements(
            self.checkpoints, registry, raw
        )
        with self.assertRaisesRegex(ValueError, "public key is reused"):
            inspect(self.checkpoints, raw, statements)

    def test_revoked_witness_cannot_contribute_to_quorum(self):
        registry, raw = signed_registry(revoked=("witness-1",))
        statements = signed_statements(self.checkpoints, registry, raw)
        with self.assertRaisesRegex(ValueError, "witness key is revoked"):
            inspect(self.checkpoints, raw, statements)

    def test_registry_quorum_cannot_exceed_active_membership(self):
        registry, raw = signed_registry(
            quorum=3, revoked=("witness-3",)
        )
        with self.assertRaisesRegex(ValueError, "exceeds active registry membership"):
            verify_signed_witness_registry(
                raw,
                pinned_registry_root_public_key_bytes=public_bytes(ROOT_PRIVATE),
                expected_registry_root_key_id=ROOT_KEY_ID,
                expected_registry_id=REGISTRY_ID,
                expected_log_id=LOG_ID,
                minimum_registry_sequence=7,
                verification_time=NOW,
            )

    def test_registry_root_and_log_signing_keys_must_be_distinct(self):
        with self.assertRaisesRegex(ValueError, "registry root and log signing keys must be distinct roles"):
            inspect(
                self.checkpoints,
                self.registry_bytes,
                self.statements,
                pinned_log_public_key_bytes=public_bytes(ROOT_PRIVATE),
            )

    def test_witness_key_cannot_reuse_registry_root_key(self):
        registry, raw = signed_registry(
            public_key_overrides={"witness-1": public_bytes(ROOT_PRIVATE)}
        )
        statements = signed_statements(
            self.checkpoints,
            registry,
            raw,
            private_key_overrides={"witness-1": ROOT_PRIVATE},
        )
        with self.assertRaisesRegex(ValueError, "witness signing key must be distinct"):
            inspect(self.checkpoints, raw, statements)

    def test_witness_key_cannot_reuse_log_signing_key(self):
        registry, raw = signed_registry(
            public_key_overrides={"witness-1": self.checkpoints["public_key"]}
        )
        statements = signed_statements(
            self.checkpoints,
            registry,
            raw,
            private_key_overrides={"witness-1": self.checkpoints["private_key"]},
        )
        with self.assertRaisesRegex(ValueError, "witness signing key must be distinct"):
            inspect(self.checkpoints, raw, statements)

    def test_registry_root_signature_is_required(self):
        tampered = dict(self.registry)
        tampered["signature_b64"] = base64.b64encode(b"\x00" * 64).decode("ascii")
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            inspect(
                self.checkpoints,
                canonical(tampered),
                self.statements,
            )

    def test_wrong_registry_root_key_is_rejected(self):
        attacker = Ed25519PrivateKey.from_private_bytes(b"\x52" * 32)
        with self.assertRaisesRegex(ValueError, "root signature verification failed"):
            inspect(
                self.checkpoints,
                self.registry_bytes,
                self.statements,
                pinned_registry_root_public_key_bytes=public_bytes(attacker),
            )

    def test_registry_sequence_rollback_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "below external minimum"):
            inspect(
                self.checkpoints,
                self.registry_bytes,
                self.statements,
                minimum_registry_sequence=8,
            )

    def test_registry_not_yet_valid_is_rejected(self):
        registry, raw = signed_registry(
            not_before="2026-11-24T20:01:00Z"
        )
        statements = signed_statements(self.checkpoints, registry, raw)
        with self.assertRaisesRegex(ValueError, "not currently valid"):
            inspect(self.checkpoints, raw, statements)

    def test_statement_cannot_predate_registry_not_before(self):
        statements = signed_statements(
            self.checkpoints,
            self.registry,
            self.registry_bytes,
            issued_at_by_id={
                "witness-1": "2026-11-24T18:44:00Z",
                "witness-2": "2026-11-24T19:02:00Z",
            },
        )
        with self.assertRaisesRegex(ValueError, "outside signed registry validity"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_statement_cannot_predate_registry_issuance(self):
        registry, raw = signed_registry(
            issued_at="2026-11-24T19:03:00Z",
            not_before="2026-11-24T19:03:00Z",
        )
        statements = signed_statements(
            self.checkpoints, registry, raw,
            issued_at_by_id={
                "witness-1": "2026-11-24T19:02:00Z",
                "witness-2": "2026-11-24T19:04:00Z",
            },
        )
        with self.assertRaisesRegex(ValueError, "outside signed registry validity"):
            inspect(self.checkpoints, raw, statements)

    def test_statement_cannot_predate_checkpoint(self):
        statements = signed_statements(
            self.checkpoints,
            self.registry,
            self.registry_bytes,
            issued_at_by_id={
                "witness-1": "2026-11-24T19:00:30Z",
                "witness-2": "2026-11-24T19:02:00Z",
            },
        )
        with self.assertRaisesRegex(ValueError, "predates the checkpoint"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_future_witness_statement_is_rejected(self):
        statements = signed_statements(
            self.checkpoints,
            self.registry,
            self.registry_bytes,
            issued_at_by_id={
                "witness-1": "2026-11-24T20:01:00Z",
                "witness-2": "2026-11-24T20:01:00Z",
            },
        )
        with self.assertRaisesRegex(ValueError, "issued in the future"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_stale_witness_statement_is_rejected(self):
        later = datetime(2026, 11, 24, 21, 2, tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError, "exceeds maximum witness statement age"):
            inspect(
                self.checkpoints,
                self.registry_bytes,
                self.statements,
                verification_time=later,
            )

    def test_witness_statement_clock_skew_is_rejected(self):
        statements = signed_statements(
            self.checkpoints,
            self.registry,
            self.registry_bytes,
            issued_at_by_id={
                "witness-1": "2026-11-24T19:02:00Z",
                "witness-2": "2026-11-24T19:04:00Z",
            },
        )
        with self.assertRaisesRegex(ValueError, "exceed registry skew limit"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_unknown_witness_is_rejected(self):
        rogue = Ed25519PrivateKey.from_private_bytes(b"\x71" * 32)
        statement = {
            "schema_version": WITNESS_SCHEMA,
            "registry_id": REGISTRY_ID,
            "registry_sequence": self.registry["registry_sequence"],
            "registry_sha256": sha(self.registry_bytes),
            "witness_id": "witness-unknown",
            "key_id": "KEY-UNKNOWN",
            "log_id": LOG_ID,
            "old_checkpoint_sha256": sha(self.checkpoints["old_bytes"]),
            "new_checkpoint_sha256": sha(self.checkpoints["new_bytes"]),
            "old_tree_size": 3,
            "new_tree_size": 9,
            "old_root_sha256": self.checkpoints["old_checkpoint"]["root_hash"],
            "new_root_sha256": self.checkpoints["new_checkpoint"]["root_hash"],
            "consistency_proof_sha256": sha(self.checkpoints["proof_bytes"]),
            "issued_at_utc": "2026-11-24T19:02:00Z",
        }
        signature = rogue.sign(WITNESS_DOMAIN + canonical(statement))
        statement["signature_b64"] = base64.b64encode(signature).decode("ascii")
        with self.assertRaisesRegex(ValueError, "not present in signed registry"):
            inspect(
                self.checkpoints,
                self.registry_bytes,
                [canonical(statement), self.statements[1]],
            )

    def test_witness_statement_signature_is_verified(self):
        statements = list(self.statements)
        document = json.loads(statements[0])
        document["signature_b64"] = base64.b64encode(b"\x00" * 64).decode("ascii")
        statements[0] = canonical(document)
        with self.assertRaisesRegex(ValueError, "Ed25519 signature verification failed"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_witness_statement_must_bind_exact_checkpoint_and_proof_digests(self):
        statements = signed_statements(
            self.checkpoints,
            self.registry,
            self.registry_bytes,
            mutate_by_id={"witness-1": {"new_checkpoint_sha256": "0" * 64}},
        )
        with self.assertRaisesRegex(ValueError, "new_checkpoint_sha256 does not match"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_witness_statement_must_bind_exact_registry_bytes(self):
        statements = signed_statements(
            self.checkpoints,
            self.registry,
            self.registry_bytes,
            mutate_by_id={"witness-1": {"registry_sha256": "0" * 64}},
        )
        with self.assertRaisesRegex(ValueError, "does not bind exact registry bytes"):
            inspect(self.checkpoints, self.registry_bytes, statements)

    def test_duplicate_json_keys_and_noncanonical_json_are_rejected(self):
        duplicate = b'{"schema_version":"x","schema_version":"y"}'
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            inspect(self.checkpoints, self.registry_bytes, [duplicate])
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 JSON"):
            inspect(
                self.checkpoints,
                self.registry_bytes + b" ",
                self.statements,
            )

    def test_successful_quorum_never_promotes_provenance_or_claims_gossip(self):
        result = inspect(self.checkpoints, self.registry_bytes, self.statements)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.trust_anchor_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.registry_sequence_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertEqual(result.verification_clock_source, "CALLER_SUPPLIED_UNAUTHENTICATED")
        self.assertIn(
            "CROSS_WITNESS_GOSSIP_AND_GLOBAL_SPLIT_VIEW_DETECTION_NOT_VERIFIED",
            result.remaining_blockers,
        )
        self.assertIn(
            "WITNESS_OPERATOR_INDEPENDENCE_NOT_INSTITUTIONALLY_ESTABLISHED",
            result.remaining_blockers,
        )


if __name__ == "__main__":
    unittest.main()
