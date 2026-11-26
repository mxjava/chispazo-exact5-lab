from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.custody_ledger_witness_integration_v1 import (
    verify_custody_timestamp_ledger_witness_v1,
)
from origen.custody_receipt_verifier_v3 import (
    CUSTODY_ARTIFACT_TYPE,
    CUSTODY_SIGNER_ROLE,
)
from origen.physical_evidence_verifier_v2 import CLASSIC_PHYSICAL_POLICY_DOMAIN
from origen.physical_evidence_verifier_v3 import canonical_physical_manifest_signature_payload_v2
from origen.independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from test_custody_receipt_verifier_v3 import (
    ROOT_KEY_ID,
    POLICY_SEQUENCE,
    POLICY_VERSION,
    StatefulOffsetTimezone,
    CUSTODIAN_ID,
    CUSTODIAN_KEY_ID,
    RECEIPT_ISSUER,
    RECEIPT_KEY_ID,
    raw_public_key,
)
from test_custody_signature_timestamp_integration_v1 import (
    timestamped_bundle,
)
from test_rfc3161_tsa_verifier_v1 import _token
from origen.checkpoint_witness_gossip_v1 import WitnessObservationBatch
from test_checkpoint_witness_gossip_v1 import make_batch
from test_checkpoint_witness_quorum_v1 import (
    REGISTRY_ID,
    ROOT_KEY_ID as WITNESS_ROOT_KEY_ID,
    ROOT_PRIVATE,
    signed_registry,
)
from test_physical_evidence_manifest_v1 import encode
from test_physical_evidence_verifier_v2 import fixture as physical_fixture
from test_transparency_checkpoint_consistency_v1 import (
    CONSISTENCY_PROOF_SCHEMA,
    KEY_ID,
    LOG_ID,
    NOW,
    consistency_path,
    public_bytes,
    signed_checkpoint,
)
from test_transparency_ledger_verifier_v1 import (
    CHECKPOINT_SCHEMA,
    ENTRY_SCHEMA,
    LOG_ID as LEDGER_LOG_ID,
    LOG_KEY_ID,
    PROOF_SCHEMA,
    inclusion_path,
    manifest_commitment,
    sha,
    tree_hash,
)


def _build_physical_signature_bundle(data: dict) -> dict:
    """Build one synthetic V3 policy covering receipt, custody and nested signers."""
    from origen.custody_signature_timestamp_integration_v1 import (
        verify_receipt_custody_signature_timestamp_v1,
    )

    timestamp_args = dict(data)
    timestamp_args.pop("receipt_private", None)
    timestamp_args.pop("custodian_private", None)
    timestamp_args["verification_time"] = NOW
    timestamp = verify_receipt_custody_signature_timestamp_v1(**timestamp_args)
    record = json.loads(data["custody_record_bytes"].decode("utf-8"))

    physical = physical_fixture()
    document = copy.deepcopy(physical["document"])
    artifact_bytes = dict(physical["artifact_bytes_by_sha256"])
    contest_id = str(record["target_contest_id"])
    document["target"]["contest_id"] = contest_id

    old_custody_digest = None
    custody_digest = hashlib.sha256(data["custody_record_bytes"]).hexdigest()
    for artifact in document["artifacts"]:
        artifact["contest_id"] = contest_id
        if artifact["artifact_type"] == "SEGOB-OIC-CUSTODY-RECORD":
            old_custody_digest = artifact["sha256"]
            artifact["sha256"] = custody_digest
            artifact["byte_length"] = len(data["custody_record_bytes"])
            artifact["media_type"] = "application/json"
    if old_custody_digest is None:
        raise AssertionError("synthetic manifest has no custody-record artifact")
    artifact_bytes.pop(old_custody_digest, None)
    artifact_bytes[custody_digest] = data["custody_record_bytes"]

    for claim in document["signatures"]:
        if claim["artifact_sha256"] == old_custody_digest:
            claim["artifact_sha256"] = custody_digest
    for event in document["custody_events"]:
        if event["artifact_sha256"] == old_custody_digest:
            event["artifact_sha256"] = custody_digest
    event = next(item for item in document["custody_events"] if item["artifact_sha256"] == custody_digest)
    event["custodian_subject_id"] = timestamp.custody_chain.custodian_id
    event["custodian_role"] = CUSTODY_SIGNER_ROLE
    event["received_at_utc"] = record["received_at_utc"]
    event["receipt_sha256"] = timestamp.custody_chain.receipt_sha256
    receipt_time_proof = next(
        item for item in document["trusted_time_proofs"]
        if item["proof_sha256"] == event["timestamp_proof_sha256"]
    )
    receipt_time_proof["event_at_utc"] = record["received_at_utc"]
    document["trusted_time_proofs"].append({
        "authority_id": (
            "tsa-root-sha256:" + timestamp.timestamp.tsa_root_certificate_sha256
        ),
        "event_id": timestamp.timestamp_event_id,
        "event_at_utc": timestamp.timestamp.gen_time_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "proof_sha256": hashlib.sha256(data["timestamp_token_der"]).hexdigest(),
    })
    document["ledger_anchor"]["inclusion_proof_sha256"] = "0" * 64
    signature_bytes_by_sha256 = {}

    delegated: dict[tuple[str, str], dict] = {}

    def add_delegation(subject_id, key_id, private_key, role, artifact_type):
        identity = (subject_id, key_id)
        public_key = raw_public_key(private_key)
        entry = delegated.get(identity)
        if entry is None:
            entry = {"public_key": public_key, "authorizations": {}}
            delegated[identity] = entry
        elif entry["public_key"] != public_key:
            raise AssertionError("synthetic signer identity maps to two public keys")
        entry["authorizations"].setdefault(role, set()).add(artifact_type)

    add_delegation(
        RECEIPT_ISSUER, RECEIPT_KEY_ID, data["receipt_private"],
        "RECEIPT-ROOT-ATTESTER", "TRUST-RECEIPT-ROOT-ATTESTATION",
    )
    add_delegation(
        CUSTODIAN_ID, CUSTODIAN_KEY_ID, data["custodian_private"],
        CUSTODY_SIGNER_ROLE, CUSTODY_ARTIFACT_TYPE,
    )
    artifact_types = {item["sha256"]: item["artifact_type"] for item in document["artifacts"]}
    for claim in document["signatures"]:
        identity = (claim["subject_id"], claim["key_id"])
        add_delegation(
            claim["subject_id"], claim["key_id"],
            physical["private_by_identity"][identity],
            claim["role"], artifact_types[claim["artifact_sha256"]],
        )

    issuer_keys = []
    for (issuer_id, key_id), entry in sorted(delegated.items()):
        authorizations = [
            {"role": role, "artifact_types": sorted(types)}
            for role, types in sorted(entry["authorizations"].items())
        ]
        issuer_keys.append({
            "issuer_id": issuer_id,
            "key_id": key_id,
            "public_key_b64": base64.b64encode(entry["public_key"]).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
            "authorizations": authorizations,
        })

    root_private = Ed25519PrivateKey.generate()
    policy_document = {
        "schema_version": "origen.trust-policy-envelope.v3",
        "policy_domain": CLASSIC_PHYSICAL_POLICY_DOMAIN,
        "policy_version": POLICY_VERSION,
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-22T00:00:00Z",
        "not_before_utc": "2026-11-23T02:49:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": issuer_keys,
    }
    unsigned_policy = copy.deepcopy(policy_document)
    policy_signature = root_private.sign(json.dumps(
        unsigned_policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii"))
    policy_document["signature"] = {
        "algorithm": "ed25519",
        "signature_b64": base64.b64encode(policy_signature).decode("ascii"),
    }
    policy_bytes = encode(policy_document)
    policy_timestamp_token_der, policy_tsa_root_der = _token(
        data=policy_bytes,
        nonce=54321,
        gen_time=datetime(2026, 11, 23, 2, 48, 30, tzinfo=timezone.utc),
        accuracy={"seconds": 1},
    )
    document["trusted_time_proofs"].append({
        "authority_id": (
            "tsa-root-sha256:" + hashlib.sha256(policy_tsa_root_der).hexdigest()
            + ":policy-oid:1.2.3.4.5"
        ),
        "event_id": "trust-policy-envelope-sha256:" + hashlib.sha256(policy_bytes).hexdigest(),
        "event_at_utc": "2026-11-23T02:48:30Z",
        "proof_sha256": hashlib.sha256(policy_timestamp_token_der).hexdigest(),
    })

    payload = canonical_physical_manifest_signature_payload_v2(encode(document))
    for claim in document["signatures"]:
        identity = (claim["subject_id"], claim["key_id"])
        signature = physical["private_by_identity"][identity].sign(payload)
        digest = hashlib.sha256(signature).hexdigest()
        claim["signature_sha256"] = digest
        signature_bytes_by_sha256[digest] = signature

    data.update({
        "document": document,
        "artifact_bytes_by_sha256": artifact_bytes,
        "signature_bytes_by_sha256": signature_bytes_by_sha256,
        "raw_manifest_bytes": encode(document),
        "signed_policy_envelope_bytes": policy_bytes,
        "policy_timestamp_token_der": policy_timestamp_token_der,
        "pinned_policy_tsa_root_certificate_der": policy_tsa_root_der,
        "expected_policy_tsa_root_sha256": hashlib.sha256(policy_tsa_root_der).hexdigest(),
        "expected_policy_tsa_policy_oid": "1.2.3.4.5",
        "policy_timestamp_expected_nonce": 54321,
        "pinned_root_public_key_bytes": raw_public_key(root_private),
        "expected_root_key_id": ROOT_KEY_ID,
        "minimum_policy_sequence": POLICY_SEQUENCE,
    })
    return document

def _build_ledger(document: dict):
    document = copy.deepcopy(document)
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
    entry_bytes = json.dumps(
        entry, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    leaves = [
        b"unrelated-ledger-record-0",
        entry_bytes,
        b"unrelated-ledger-record-2",
        b"unrelated-ledger-record-3",
        b"unrelated-ledger-record-4",
        b"unrelated-ledger-record-5",
        b"unrelated-ledger-record-6",
    ]
    log_private = Ed25519PrivateKey.from_private_bytes(b"\x19" * 32)
    new_checkpoint, new_bytes = signed_checkpoint(
        log_private, leaves, issued_at="2026-11-24T19:00:00Z"
    )
    inclusion_proof = {
        "schema_version": PROOF_SCHEMA,
        "ledger_id": document["ledger_anchor"]["ledger_id"],
        "entry_id": document["ledger_anchor"]["entry_id"],
        "log_id": LEDGER_LOG_ID,
        "leaf_index": 1,
        "checkpoint_sha256": sha(new_bytes),
        "audit_path_b64": [
            __import__("base64").b64encode(node).decode("ascii")
            for node in inclusion_path(1, leaves)
        ],
    }
    inclusion_bytes = json.dumps(
        inclusion_proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    document["ledger_anchor"]["inclusion_proof_sha256"] = sha(inclusion_bytes)
    manifest_bytes = encode(document)

    old_checkpoint, old_bytes = signed_checkpoint(
        log_private, leaves[:3], issued_at="2026-11-24T18:59:00Z"
    )
    consistency_proof = {
        "schema_version": CONSISTENCY_PROOF_SCHEMA,
        "log_id": LOG_ID,
        "old_checkpoint_sha256": sha(old_bytes),
        "new_checkpoint_sha256": sha(new_bytes),
        "old_tree_size": 3,
        "new_tree_size": len(leaves),
        "consistency_path_b64": [
            __import__("base64").b64encode(node).decode("ascii")
            for node in consistency_path(3, leaves, True)
        ],
    }
    consistency_bytes = json.dumps(
        consistency_proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return {
        "manifest_bytes": manifest_bytes,
        "entry_bytes": entry_bytes,
        "inclusion_bytes": inclusion_bytes,
        "old_bytes": old_bytes,
        "new_bytes": new_bytes,
        "consistency_bytes": consistency_bytes,
        "log_private": log_private,
        "log_public": public_bytes(log_private),
        "old_checkpoint": old_checkpoint,
        "new_checkpoint": new_checkpoint,
        "leaves": leaves,
        "document": document,
    }


def _witness_batches(ledger, *, split_view=False, omit_ledger_checkpoint=False):
    registry, registry_bytes = signed_registry()
    old_bytes = ledger["old_bytes"]
    old_checkpoint = ledger["old_checkpoint"]
    leaves = list(ledger["leaves"])
    log_private = ledger["log_private"]

    primary = {
        "old_bytes": old_bytes,
        "new_bytes": ledger["new_bytes"],
        "proof_bytes": ledger["consistency_bytes"],
        "proof": {"old_tree_size": 3, "new_tree_size": len(leaves)},
        "old_checkpoint": old_checkpoint,
        "new_checkpoint": ledger["new_checkpoint"],
        "public_key": ledger["log_public"],
    }
    if omit_ledger_checkpoint:
        alt_leaves = leaves[:-1] + [b"not-the-ledger-checkpoint"]
        alt_new, alt_new_bytes = signed_checkpoint(
            log_private, alt_leaves, issued_at="2026-11-24T19:00:00Z"
        )
        alt_proof = {
            "schema_version": CONSISTENCY_PROOF_SCHEMA,
            "log_id": LOG_ID,
            "old_checkpoint_sha256": sha(old_bytes),
            "new_checkpoint_sha256": sha(alt_new_bytes),
            "old_tree_size": 3,
            "new_tree_size": len(alt_leaves),
            "consistency_path_b64": [
                __import__("base64").b64encode(node).decode("ascii")
                for node in consistency_path(3, alt_leaves, True)
            ],
        }
        alt = {
            "old_bytes": old_bytes,
            "new_bytes": alt_new_bytes,
            "proof_bytes": json.dumps(
                alt_proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8"),
            "proof": {"old_tree_size": 3, "new_tree_size": len(alt_leaves)},
            "old_checkpoint": old_checkpoint,
            "new_checkpoint": alt_new,
            "public_key": ledger["log_public"],
        }
        return (
            make_batch(alt, registry_bytes, ("witness-1", "witness-2")),
            make_batch(alt, registry_bytes, ("witness-2", "witness-3")),
        ), registry_bytes

    first = make_batch(primary, registry_bytes, ("witness-1", "witness-2"))
    if not split_view:
        second = make_batch(primary, registry_bytes, ("witness-2", "witness-3"))
        return (first, second), registry_bytes

    alt_leaves = leaves[:-1] + [b"forked-ledger-tail"]
    alt_new, alt_new_bytes = signed_checkpoint(
        log_private, alt_leaves, issued_at="2026-11-24T19:00:00Z"
    )
    alt_proof = {
        "schema_version": CONSISTENCY_PROOF_SCHEMA,
        "log_id": LOG_ID,
        "old_checkpoint_sha256": sha(old_bytes),
        "new_checkpoint_sha256": sha(alt_new_bytes),
        "old_tree_size": 3,
        "new_tree_size": len(alt_leaves),
        "consistency_path_b64": [
            __import__("base64").b64encode(node).decode("ascii")
            for node in consistency_path(3, alt_leaves, True)
        ],
    }
    alt = {
        "old_bytes": old_bytes,
        "new_bytes": alt_new_bytes,
        "proof_bytes": json.dumps(
            alt_proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8"),
        "proof": {"old_tree_size": 3, "new_tree_size": len(alt_leaves)},
        "old_checkpoint": old_checkpoint,
        "new_checkpoint": alt_new,
        "public_key": ledger["log_public"],
    }
    second = make_batch(alt, registry_bytes, ("witness-2", "witness-3"))
    return (first, second), registry_bytes


def _build_case(*, split_view=False, omit_ledger_checkpoint=False):
    data = timestamped_bundle(accuracy={"seconds": 1})
    document = _build_physical_signature_bundle(data)
    ledger = _build_ledger(document)
    data["raw_manifest_bytes"] = ledger["manifest_bytes"]
    batches, registry_bytes = _witness_batches(
        ledger,
        split_view=split_view,
        omit_ledger_checkpoint=omit_ledger_checkpoint,
    )
    return data, ledger, batches, registry_bytes


def _verify(data, ledger, batches, **overrides):
    values = {
        "original_receipt_bytes": data["original_receipt_bytes"],
        "signed_policy_envelope_bytes": data["signed_policy_envelope_bytes"],
        "custody_record_bytes": data["custody_record_bytes"],
        "portfolio_bytes": data["portfolio_bytes"],
        "custody_signature_bytes": data["custody_signature_bytes"],
        "custodian_key_id": data["custodian_key_id"],
        "timestamp_token_der": data["timestamp_token_der"],
        "policy_timestamp_token_der": data["policy_timestamp_token_der"],
        "pinned_policy_tsa_root_certificate_der": data["pinned_policy_tsa_root_certificate_der"],
        "expected_policy_tsa_root_sha256": data["expected_policy_tsa_root_sha256"],
        "expected_policy_tsa_policy_oid": data["expected_policy_tsa_policy_oid"],
        "policy_timestamp_expected_nonce": data["policy_timestamp_expected_nonce"],
        "pinned_root_public_key_bytes": data["pinned_root_public_key_bytes"],
        "expected_root_key_id": data["expected_root_key_id"],
        "minimum_policy_sequence": data["minimum_policy_sequence"],
        "pinned_tsa_root_certificate_der": data["pinned_tsa_root_certificate_der"],
        "expected_tsa_root_sha256": data["expected_tsa_root_sha256"],
        "expected_nonce": data["expected_nonce"],
        "raw_manifest_bytes": ledger["manifest_bytes"],
        "artifact_bytes_by_sha256": data["artifact_bytes_by_sha256"],
        "signature_bytes_by_sha256": data["signature_bytes_by_sha256"],
        "raw_ledger_entry_bytes": ledger["entry_bytes"],
        "raw_inclusion_proof_bytes": ledger["inclusion_bytes"],
        "raw_old_checkpoint_bytes": ledger["old_bytes"],
        "raw_new_checkpoint_bytes": ledger["new_bytes"],
        "raw_consistency_proof_bytes": ledger["consistency_bytes"],
        "witness_observation_batches": batches,
        "pinned_log_public_key_bytes": ledger["log_public"],
        "expected_log_id": LEDGER_LOG_ID,
        "expected_log_key_id": LOG_KEY_ID,
        "minimum_new_tree_size": len(ledger["leaves"]),
        "pinned_registry_root_public_key_bytes": public_bytes(ROOT_PRIVATE),
        "expected_registry_root_key_id": WITNESS_ROOT_KEY_ID,
        "expected_registry_id": REGISTRY_ID,
        "minimum_registry_sequence": 7,
        "verification_time": NOW,
    }
    values.update(overrides)
    return verify_custody_timestamp_ledger_witness_v1(**values)


class CustodyLedgerWitnessIntegrationV1Tests(unittest.TestCase):
    def test_exact_custody_timestamp_ledger_and_witnesses_compose_but_remain_blocked(self):
        data, ledger, batches, _ = _build_case()
        result = _verify(data, ledger, batches)
        self.assertTrue(result.ledger_checkpoint_observed_in_witness_batches)
        self.assertEqual(result.physical_signatures.signatures_verified, len(data["signature_bytes_by_sha256"]))
        self.assertIs(result.physical_signatures.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertFalse(result.witness_gossip.split_view_detected)
        self.assertEqual(
            result.witness_comparison_status,
            "NO_CONFLICT_FOUND_IN_SUPPLIED_BATCHES_NOT_GLOBAL_PROOF",
        )
        self.assertEqual(result.timestamp_event_id, result.custody_timestamp.timestamp_event_id)
        self.assertEqual(
            result.policy_envelope_timestamp.policy_envelope_sha256,
            hashlib.sha256(data["signed_policy_envelope_bytes"]).hexdigest(),
        )
        self.assertTrue(result.policy_envelope_timestamp.existence_before_effective_time_verified)
        self.assertEqual(result.policy_envelope_timestamp.expected_policy_oid, "1.2.3.4.5")
        self.assertTrue(result.policy_envelope_timestamp_proof_in_manifest_commitment_verified)
        self.assertEqual(
            result.policy_envelope_timestamp.timestamp.message_imprint_hex,
            hashlib.sha256(data["signed_policy_envelope_bytes"]).hexdigest(),
        )
        self.assertEqual(result.ledger_checkpoint_sha256, sha(ledger["new_bytes"]))
        self.assertEqual(
            result.ledger.inclusion.manifest_commitment_sha256,
            manifest_commitment(ledger["document"]),
        )
        self.assertIs(result.independent_boundary_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_policy_timestamp_token_must_imprint_exact_signed_v3_envelope(self):
        data, ledger, batches, _ = _build_case()
        with self.assertRaisesRegex(ValueError, "message imprint"):
            _verify(
                data, ledger, batches,
                policy_timestamp_token_der=data["timestamp_token_der"],
                pinned_policy_tsa_root_certificate_der=data["pinned_tsa_root_certificate_der"],
                expected_policy_tsa_root_sha256=data["expected_tsa_root_sha256"],
                policy_timestamp_expected_nonce=data["expected_nonce"],
            )

    def test_policy_envelope_must_exist_before_its_signed_effective_time(self):
        data, ledger, batches, _ = _build_case()
        token, root_der = _token(
            data=data["signed_policy_envelope_bytes"],
            nonce=data["policy_timestamp_expected_nonce"],
            gen_time=datetime(2026, 11, 23, 2, 49, 1, tzinfo=timezone.utc),
            accuracy={"seconds": 0},
        )
        with self.assertRaisesRegex(ValueError, "must end strictly before signed not_before_utc"):
            _verify(
                data, ledger, batches,
                policy_timestamp_token_der=token,
                pinned_policy_tsa_root_certificate_der=root_der,
                expected_policy_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
            )

    def test_policy_envelope_timestamp_requires_accuracy(self):
        data, ledger, batches, _ = _build_case()
        token, root_der = _token(
            data=data["signed_policy_envelope_bytes"],
            nonce=data["policy_timestamp_expected_nonce"],
            gen_time=datetime(2026, 11, 23, 2, 48, 30, tzinfo=timezone.utc),
            accuracy=None,
        )
        with self.assertRaisesRegex(ValueError, "accuracy is required"):
            _verify(
                data, ledger, batches,
                policy_timestamp_token_der=token,
                pinned_policy_tsa_root_certificate_der=root_der,
                expected_policy_tsa_root_sha256=hashlib.sha256(root_der).hexdigest(),
            )

    def test_policy_timestamp_oid_must_match_the_caller_pinned_policy(self):
        data, ledger, batches, _ = _build_case()
        with self.assertRaisesRegex(ValueError, "policy OID does not match"):
            _verify(data, ledger, batches, expected_policy_tsa_policy_oid="1.2.3.4.6")

    def test_malformed_expected_policy_oid_is_rejected(self):
        data, ledger, batches, _ = _build_case()
        with self.assertRaisesRegex(ValueError, "canonical numeric OID"):
            _verify(data, ledger, batches, expected_policy_tsa_policy_oid="1.2..3")

    def test_policy_envelope_timestamp_nonce_is_checked(self):
        data, ledger, batches, _ = _build_case()
        with self.assertRaisesRegex(ValueError, "nonce does not match"):
            _verify(data, ledger, batches, policy_timestamp_expected_nonce=54322)

    def test_manifest_must_bind_exact_timestamp_token_digest(self):
        data, ledger, batches, _ = _build_case()
        document = copy.deepcopy(ledger["document"])
        proof = next(
            item for item in document["trusted_time_proofs"]
            if item["event_id"].startswith("custody-signature-sha256:")
        )
        proof["proof_sha256"] = "0" * 64
        bad_manifest = encode(document)
        with self.assertRaisesRegex(ValueError, "nested Ed25519 signature verification failed"):
            _verify(data, {**ledger, "manifest_bytes": bad_manifest}, batches)


    def test_policy_timestamp_token_digest_is_covered_by_nested_signatures(self):
        data, ledger, batches, _ = _build_case()
        document = copy.deepcopy(ledger["document"])
        proof = next(
            item for item in document["trusted_time_proofs"]
            if item["event_id"].startswith("trust-policy-envelope-sha256:")
        )
        proof["proof_sha256"] = "0" * 64
        bad_manifest = encode(document)
        with self.assertRaisesRegex(ValueError, "nested Ed25519 signature verification failed"):
            _verify(data, {**ledger, "manifest_bytes": bad_manifest}, batches)

    def test_ledger_inclusion_proof_digest_is_not_part_of_nested_signature_payload_but_is_verified_separately(self):
        data, ledger, batches, _ = _build_case()
        document = copy.deepcopy(ledger["document"])
        document["ledger_anchor"]["inclusion_proof_sha256"] = "0" * 64
        bad_manifest = encode(document)
        with self.assertRaisesRegex(ValueError, "exact inclusion-proof bytes"):
            _verify(data, {**ledger, "manifest_bytes": bad_manifest}, batches)

    def test_exact_artifact_byte_map_is_required_by_composed_verifier(self):
        data, ledger, batches, _ = _build_case()
        altered = dict(data["artifact_bytes_by_sha256"])
        digest = next(iter(altered))
        altered[digest] = altered[digest] + b"x"
        with self.assertRaisesRegex(ValueError, "artifact byte length mismatch|artifact SHA-256 mismatch"):
            _verify(data, ledger, batches, artifact_bytes_by_sha256=altered)

    def test_exact_nested_signature_byte_map_is_required_by_composed_verifier(self):
        data, ledger, batches, _ = _build_case()
        altered = dict(data["signature_bytes_by_sha256"])
        digest = next(iter(altered))
        altered[digest] = altered[digest][:-1] + bytes([altered[digest][-1] ^ 1])
        with self.assertRaisesRegex(ValueError, "signature SHA-256"):
            _verify(data, ledger, batches, signature_bytes_by_sha256=altered)

    def test_ledger_checkpoint_must_be_observed_by_at_least_one_witness_batch(self):
        data, ledger, batches, _ = _build_case(omit_ledger_checkpoint=True)
        with self.assertRaisesRegex(ValueError, "ledger checkpoint is absent"):
            _verify(data, ledger, batches)

    def test_split_view_in_supplied_witness_batches_is_reported_without_promotion(self):
        data, ledger, batches, _ = _build_case(split_view=True)
        result = _verify(data, ledger, batches)
        self.assertTrue(result.witness_gossip.split_view_detected)
        self.assertEqual(
            result.witness_comparison_status,
            "SPLIT_VIEW_DETECTED_IN_SUPPLIED_BATCHES",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_lazy_or_mutable_witness_collections_are_rejected_before_iteration(self):
        data, ledger, batches, _ = _build_case()
        consumed = []

        def lazy_batches():
            consumed.append("iterated")
            yield batches[0]
            yield batches[1]

        with self.assertRaisesRegex(TypeError, "exact tuple"):
            _verify(data, ledger, lazy_batches())
        self.assertEqual(consumed, [])

        with self.assertRaisesRegex(TypeError, "exact tuple"):
            _verify(data, ledger, list(batches))

    def test_oversized_witness_tuple_is_rejected_before_checkpoint_scan(self):
        data, ledger, _, _ = _build_case()
        oversized = tuple(
            WitnessObservationBatch(b"", b"", b"", b"", (b"",))
            for _ in range(33)
        )
        with self.assertRaisesRegex(ValueError, r"2\.\.32"):
            _verify(data, ledger, oversized)

    def test_stateful_caller_clock_is_sampled_once_at_composition_boundary(self):
        data, ledger, batches, _ = _build_case()
        stateful = StatefulOffsetTimezone()
        supplied = datetime(2026, 11, 24, 17, 30, tzinfo=stateful)
        result = _verify(data, ledger, batches, verification_time=supplied)
        self.assertEqual(stateful.calls, 1)
        self.assertEqual(
            result.custody_timestamp.custody_chain.verification_time_utc,
            datetime(2026, 11, 24, 19, 30, tzinfo=timezone.utc),
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)


    def test_independent_boundary_reverifies_exact_receipt_and_policy_after_evidence_chain(self):
        data, ledger, batches, _ = _build_case()
        with patch(
            "origen.custody_ledger_witness_integration_v1.verify_independent_provenance",
            wraps=verify_independent_provenance,
        ) as boundary:
            result = _verify(data, ledger, batches)

        boundary.assert_called_once()
        args, kwargs = boundary.call_args
        self.assertIs(args[0], data["original_receipt_bytes"])
        self.assertIs(kwargs["signed_policy_envelope_bytes"], data["signed_policy_envelope_bytes"])
        self.assertIs(kwargs["pinned_root_public_key_bytes"], data["pinned_root_public_key_bytes"])
        self.assertEqual(kwargs["expected_root_key_id"], data["expected_root_key_id"])
        self.assertEqual(kwargs["minimum_policy_sequence"], data["minimum_policy_sequence"])
        self.assertEqual(
            kwargs["verification_time"],
            datetime(2026, 11, 24, 19, 30, tzinfo=timezone.utc),
        )
        self.assertIs(result.independent_boundary_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)

    def test_non_blocked_or_stringified_independent_boundary_status_fails_closed(self):
        data, ledger, batches, _ = _build_case()
        with patch(
            "origen.custody_ledger_witness_integration_v1.verify_independent_provenance",
            return_value="BLOCKED_PROVENANCE",
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "independent provenance boundary returned an unsupported non-blocked status",
            ):
                _verify(data, ledger, batches)

    def test_independent_boundary_is_not_reached_when_nested_signature_validation_fails(self):
        data, ledger, batches, _ = _build_case()
        altered = dict(data["signature_bytes_by_sha256"])
        digest = next(iter(altered))
        altered[digest] = altered[digest][:-1] + bytes([altered[digest][-1] ^ 1])
        with patch(
            "origen.custody_ledger_witness_integration_v1.verify_independent_provenance",
            wraps=verify_independent_provenance,
        ) as boundary:
            with self.assertRaisesRegex(ValueError, "signature SHA-256"):
                _verify(data, ledger, batches, signature_bytes_by_sha256=altered)
            boundary.assert_not_called()
