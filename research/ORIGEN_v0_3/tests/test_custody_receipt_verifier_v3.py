"""Adversarial V3 custody-receipt integration tests; all keys and records are synthetic."""
from __future__ import annotations

import base64
import copy
import hashlib
import itertools
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.custody import build_seal_record, canonical_json_bytes, sha256_bytes
from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_verifier_v2 import CLASSIC_PHYSICAL_POLICY_DOMAIN
from origen.custody_receipt_verifier_v3 import (
    CUSTODY_ARTIFACT_TYPE,
    CUSTODY_SIGNER_ROLE,
    canonical_custody_signature_payload,
    verify_receipt_and_custody_v3,
)
from test_trust_receipt_v1 import encode, valid_document
from test_trust_verifier_v1 import NOW


ROOT_KEY_ID = "synthetic-classic-policy-root"
POLICY_SEQUENCE = 17
POLICY_VERSION = "policy-2026-11"
RECEIPT_ISSUER = "independent-verifier"
RECEIPT_KEY_ID = "verifier-key-1"
CUSTODIAN_ID = "independent-custodian-1"
CUSTODIAN_KEY_ID = "custodian-key-1"


def raw_public_key(private_key):
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def sign_receipt(document, private_key):
    unsigned = copy.deepcopy(document)
    unsigned["receipt_attestation"].pop("signature_b64")
    payload = json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["receipt_attestation"]["signature_b64"] = base64.b64encode(
        private_key.sign(payload)
    ).decode("ascii")
    return encode(document)


def _portfolio_bytes():
    rows = [
        "-".join(f"{number:02d}" for number in combo)
        for combo in itertools.islice(itertools.combinations(range(1, 29), 5), 30)
    ]
    return ("\n".join(rows) + "\n").encode("ascii")


def _signed_policy(receipt_private, custodian_private, root_private, *, custody_role=CUSTODY_SIGNER_ROLE):
    authorizations = {
        RECEIPT_ISSUER: {
            "key_id": RECEIPT_KEY_ID,
            "public_key": raw_public_key(receipt_private),
            "role": "RECEIPT-ROOT-ATTESTER",
            "artifact_type": "TRUST-RECEIPT-ROOT-ATTESTATION",
        },
        CUSTODIAN_ID: {
            "key_id": CUSTODIAN_KEY_ID,
            "public_key": raw_public_key(custodian_private),
            "role": custody_role,
            "artifact_type": CUSTODY_ARTIFACT_TYPE,
        },
    }
    issuer_keys = []
    for issuer_id in sorted(authorizations):
        item = authorizations[issuer_id]
        issuer_keys.append({
            "issuer_id": issuer_id,
            "key_id": item["key_id"],
            "public_key_b64": base64.b64encode(item["public_key"]).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
            "authorizations": [{
                "role": item["role"],
                "artifact_types": [item["artifact_type"]],
            }],
        })
    document = {
        "schema_version": "origen.trust-policy-envelope.v3",
        "policy_domain": CLASSIC_PHYSICAL_POLICY_DOMAIN,
        "policy_version": POLICY_VERSION,
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-22T00:00:00Z",
        "not_before_utc": "2026-11-22T00:00:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": issuer_keys,
    }
    unsigned = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    document["signature"] = {
        "algorithm": "ed25519",
        "signature_b64": base64.b64encode(root_private.sign(unsigned)).decode("ascii"),
    }
    envelope = json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return envelope, raw_public_key(root_private)


def bundle(*, custody_role=CUSTODY_SIGNER_ROLE, root_reused=False):
    receipt_private = Ed25519PrivateKey.generate()
    custodian_private = Ed25519PrivateKey.generate()
    root_private = Ed25519PrivateKey.generate()
    if root_reused:
        custodian_private = root_private

    portfolio = _portfolio_bytes()
    portfolio_digest = sha256_bytes(portfolio)
    record = build_seal_record(
        candidate_id="SYNTHETIC-CANDIDATE-1",
        candidate_spec_sha256="9" * 64,
        target_contest_id=12389,
        history_max_contest_id=12388,
        modality="CLASSIC",
        history_sha256="a" * 64,
        source_commit="b" * 40,
        environment_manifest_sha256="b" * 64,
        portfolio=portfolio,
        generator_id="generator-a",
        generated_at_utc="2026-11-23T02:40:00Z",
        generator_clock_source="synthetic-test-clock",
        custodian_id=CUSTODIAN_ID,
        received_at_utc="2026-11-23T02:45:00Z",
        custodian_clock_source="synthetic-test-clock",
        custodian_recomputed_sha256=portfolio_digest,
        official_draw_close_at_utc="2026-11-23T03:00:00Z",
        official_draw_close_source="synthetic-test-only",
    )
    record_bytes = canonical_json_bytes(record) + b"\n"

    receipt_document = valid_document()
    receipt_document["custodians"][0]["subject_id"] = CUSTODIAN_ID
    receipt_document["custodians"][0]["role"] = CUSTODY_SIGNER_ROLE
    receipt_document["custodians"][0]["receipt_sha256"] = sha256_bytes(record_bytes)
    receipt_document["output_seals"][0]["portfolio_sha256"] = portfolio_digest
    receipt_bytes = sign_receipt(receipt_document, receipt_private)

    policy_bytes, root_public = _signed_policy(
        receipt_private,
        custodian_private,
        root_private,
        custody_role=custody_role,
    )
    signature = custodian_private.sign(
        canonical_custody_signature_payload(
            record_bytes,
            hashlib.sha256(receipt_bytes).hexdigest(),
            CUSTODIAN_KEY_ID,
        )
    )
    return {
        "original_receipt_bytes": receipt_bytes,
        "signed_policy_envelope_bytes": policy_bytes,
        "custody_record_bytes": record_bytes,
        "portfolio_bytes": portfolio,
        "custody_signature_bytes": signature,
        "custodian_key_id": CUSTODIAN_KEY_ID,
        "pinned_root_public_key_bytes": root_public,
        "expected_root_key_id": ROOT_KEY_ID,
        "minimum_policy_sequence": POLICY_SEQUENCE,
        "verification_time": NOW,
        "receipt_private": receipt_private,
    }


def inspect(data, **overrides):
    args = dict(data)
    args.pop("receipt_private", None)
    args.update(overrides)
    return verify_receipt_and_custody_v3(**args)


class StatefulOffsetTimezone(tzinfo):
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=-2 if self.calls == 1 else 2)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "stateful-custody-test"


class CustodyReceiptVerifierV3Tests(unittest.TestCase):
    def test_valid_signed_custody_receipt_verifies_but_provenance_stays_blocked(self):
        result = inspect(bundle())
        self.assertTrue(result.custody_signature_verified)
        self.assertEqual(result.custodian_id, CUSTODIAN_ID)
        self.assertEqual(result.custodian_key_id, CUSTODIAN_KEY_ID)
        self.assertEqual(result.target_contest_id, 12389)
        self.assertEqual(result.covered_generator_id, "generator-a")
        self.assertEqual(result.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.role_authorization_status,
                         "SIGNED_POLICY_MATCH_ONLY_NOT_INSTITUTIONALLY_AUTHENTICATED")
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn("CUSTODY_RECEIPT_SIGNATURES_AND_CUSTODIAN_IDENTITY_NOT_VERIFIED",
                      result.remaining_blockers)
        self.assertIn("CUSTODIAN_LEGAL_IDENTITY_AND_INSTITUTIONAL_DELEGATION_NOT_AUTHENTICATED",
                      result.remaining_blockers)
        self.assertIn("CUSTODY_SIGNATURE_TRUSTED_TIME_NOT_VERIFIED", result.remaining_blockers)

    def test_mutated_custody_record_bytes_are_rejected(self):
        data = bundle()
        with self.assertRaisesRegex(ValueError, "canonical UTF-8 JSON bytes"):
            inspect(data, custody_record_bytes=data["custody_record_bytes"][:-1] + b" " + b"\n")

    def test_tampered_portfolio_bytes_are_rejected(self):
        data = bundle()
        changed = data["portfolio_bytes"][:-2] + b"99\n"
        with self.assertRaisesRegex(ValueError, "custody seal record verification failed"):
            inspect(data, portfolio_bytes=changed)

    def test_tampered_detached_signature_is_rejected(self):
        data = bundle()
        changed = bytes([data["custody_signature_bytes"][0] ^ 1]) + data["custody_signature_bytes"][1:]
        with self.assertRaisesRegex(ValueError, "detached custody Ed25519 signature verification failed"):
            inspect(data, custody_signature_bytes=changed)

    def test_receipt_custodian_claim_must_bind_exact_record_bytes(self):
        data = bundle()
        document = json.loads(data["original_receipt_bytes"])
        document["custodians"][0]["receipt_sha256"] = "d" * 64
        changed_receipt = sign_receipt(document, data["receipt_private"])
        with self.assertRaisesRegex(ValueError, "does not bind exact original custody-record bytes"):
            inspect(data, original_receipt_bytes=changed_receipt)

    def test_custody_key_id_cannot_alias_receipt_or_physical_signer_key(self):
        data = bundle()
        with self.assertRaisesRegex(ValueError, "must be distinct from receipt and physical signer key IDs"):
            inspect(data, custodian_key_id=RECEIPT_KEY_ID)

    def test_unknown_custodian_key_is_rejected(self):
        data = bundle()
        with self.assertRaisesRegex(ValueError, "unknown or ambiguous"):
            inspect(data, custodian_key_id="unknown-custodian-key")

    def test_role_must_be_authorized_by_signed_v3_matrix(self):
        data = bundle(custody_role="different-custodian-role")
        with self.assertRaisesRegex(ValueError, "not authorized for external-custodian"):
            inspect(data)

    def test_policy_root_key_cannot_be_reused_as_custodian_key(self):
        data = bundle(root_reused=True)
        with self.assertRaisesRegex(ValueError, "pinned root public key must not be reused"):
            inspect(data)

    def test_noncanonical_custody_timestamp_is_rejected_before_permissive_parser(self):
        data = bundle()
        record = json.loads(data["custody_record_bytes"])
        record["generated_at_utc"] = "2026-11-23 02:40:00Z"
        raw = canonical_json_bytes(record) + b"\n"
        with self.assertRaisesRegex(ValueError, "canonical UTC RFC3339"):
            inspect(data, custody_record_bytes=raw)

    def test_duplicate_json_keys_are_rejected(self):
        data = bundle()
        raw = b'{"candidate_id":"first","candidate_id":"second"}\n'
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            inspect(data, custody_record_bytes=raw)

    def test_stateful_caller_timezone_is_sampled_once_across_receipt_and_custody(self):
        data = bundle()
        tz = StatefulOffsetTimezone()
        data["verification_time"] = datetime(2026, 11, 23, 2, 0, tzinfo=tz)
        result = inspect(data)
        self.assertEqual(tz.calls, 1)
        self.assertEqual(result.verification_time_utc, NOW)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)


if __name__ == "__main__":
    unittest.main()
