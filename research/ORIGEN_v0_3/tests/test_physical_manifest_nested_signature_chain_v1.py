from __future__ import annotations

import base64
import copy
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_manifest_v1 import REQUIRED_ARTIFACT_TYPES
from origen.physical_manifest_nested_signature_chain_v1 import (
    ROLE_AUTHORIZATION_UNVERIFIED,
    SIGNATURE_CHAIN_STATUS,
    canonical_physical_manifest_signature_payload,
    verify_independent_provenance_with_nested_signatures,
    verify_independent_provenance_with_signed_policy_and_nested_signatures,
)
from origen.trust_policy_envelope_v1 import (
    SCHEMA_VERSION,
    verify_signed_trust_policy,
)
from test_physical_evidence_manifest_v1 import (
    encode as encode_manifest,
    valid_document as valid_manifest_document,
)
from test_trust_receipt_v1 import (
    encode as encode_receipt,
    valid_document as valid_receipt_document,
)


NOW = datetime(2026, 11, 23, 4, 0, tzinfo=timezone.utc)
ROOT_KEY_ID = "synthetic-root-2026"
POLICY_SEQUENCE = 7
MANIFEST_TYPE = "PHYSICAL-EVIDENCE-MANIFEST"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _raw_public_key(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _canonical_json(document: dict) -> bytes:
    return json.dumps(
        document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _signed_receipt(document: dict, issuer: Ed25519PrivateKey) -> bytes:
    signed = copy.deepcopy(document)
    unsigned = copy.deepcopy(signed)
    unsigned["receipt_attestation"].pop("signature_b64")
    payload = _canonical_json(unsigned)
    signed["receipt_attestation"]["signature_b64"] = base64.b64encode(
        issuer.sign(payload)
    ).decode("ascii")
    return encode_receipt(signed)


def _make_signed_policy(
    private_by_identity: dict[tuple[str, str], Ed25519PrivateKey],
    *,
    policy_version: str,
    required_artifact_types: tuple[str, ...],
    revoked_identity: tuple[str, str] | None = None,
    omit_identity: tuple[str, str] | None = None,
):
    root_private = Ed25519PrivateKey.generate()
    issuer_keys = []
    for identity, private_key in sorted(private_by_identity.items()):
        if identity == omit_identity:
            continue
        subject_id, key_id = identity
        issuer_keys.append({
            "issuer_id": subject_id,
            "key_id": key_id,
            "public_key_b64": base64.b64encode(
                _raw_public_key(private_key)
            ).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": identity == revoked_identity,
        })
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": policy_version,
        "policy_sequence": POLICY_SEQUENCE,
        "issuer_id": "synthetic-policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": "2026-11-22T00:00:00Z",
        "not_before_utc": "2026-11-23T03:00:00Z",
        "expires_at_utc": "2026-12-01T00:00:00Z",
        "issuer_keys": issuer_keys,
        "required_artifact_types": list(required_artifact_types),
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    unsigned = copy.deepcopy(document)
    unsigned.pop("signature")
    document["signature"]["signature_b64"] = base64.b64encode(
        root_private.sign(_canonical_json(unsigned))
    ).decode("ascii")
    raw = _canonical_json(document)
    root_public_key_bytes = _raw_public_key(root_private)
    policy = verify_signed_trust_policy(
        raw,
        pinned_root_public_key_bytes=root_public_key_bytes,
        expected_root_key_id=ROOT_KEY_ID,
        minimum_policy_sequence=POLICY_SEQUENCE,
        verification_time=NOW,
    )
    return policy, raw, root_public_key_bytes


def make_case(
    *,
    revoked_identity: tuple[str, str] | None = None,
    omit_identity: tuple[str, str] | None = None,
):
    manifest_document = valid_manifest_document()
    contest_id = manifest_document["target"]["contest_id"]

    old_to_new: dict[str, str] = {}
    artifact_bytes_by_sha256: dict[str, bytes] = {}
    for index, artifact in enumerate(manifest_document["artifacts"]):
        original = (
            "synthetic physical artifact:"
            + artifact["artifact_type"]
            + f":{index}"
        ).encode("ascii")
        old_digest = artifact["sha256"]
        new_digest = _sha(original)
        old_to_new[old_digest] = new_digest
        artifact["sha256"] = new_digest
        artifact["byte_length"] = len(original)
        artifact_bytes_by_sha256[new_digest] = original

    for signature in manifest_document["signatures"]:
        signature["artifact_sha256"] = old_to_new[
            signature["artifact_sha256"]
        ]
    for event in manifest_document["custody_events"]:
        event["artifact_sha256"] = old_to_new[event["artifact_sha256"]]

    private_by_identity: dict[tuple[str, str], Ed25519PrivateKey] = {}
    for signature in manifest_document["signatures"]:
        identity = (signature["subject_id"], signature["key_id"])
        private_by_identity.setdefault(identity, Ed25519PrivateKey.generate())

    placeholder_manifest = encode_manifest(manifest_document)
    payload = canonical_physical_manifest_signature_payload(placeholder_manifest)
    signature_bytes_by_sha256: dict[str, bytes] = {}
    for signature in manifest_document["signatures"]:
        identity = (signature["subject_id"], signature["key_id"])
        original_signature = private_by_identity[identity].sign(payload)
        signature_digest = _sha(original_signature)
        signature["signature_sha256"] = signature_digest
        signature_bytes_by_sha256[signature_digest] = original_signature

    manifest_bytes = encode_manifest(manifest_document)
    assert canonical_physical_manifest_signature_payload(manifest_bytes) == payload
    manifest_digest = _sha(manifest_bytes)
    artifact_bytes_by_sha256[manifest_digest] = manifest_bytes

    receipt_document = valid_receipt_document()
    receipt_document["target"]["contest_id"] = contest_id
    receipt_document["target"]["draw_close_at_utc"] = (
        manifest_document["target"]["draw_close_at_utc"]
    )
    target_list = json.dumps(
        [contest_id], separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    receipt_document["target"]["target_list_sha256"] = _sha(target_list)
    for seal in receipt_document["output_seals"]:
        seal["target_contest_id"] = contest_id

    receipt_document["artifacts"] = [
        {
            "artifact_type": item["artifact_type"],
            "sha256": item["sha256"],
            "byte_length": item["byte_length"],
            "contest_id": contest_id,
        }
        for item in manifest_document["artifacts"]
    ] + [{
        "artifact_type": MANIFEST_TYPE,
        "sha256": manifest_digest,
        "byte_length": len(manifest_bytes),
        "contest_id": contest_id,
    }]

    receipt_issuer = Ed25519PrivateKey.generate()
    receipt_identity = (
        receipt_document["receipt_attestation"]["issuer_id"],
        receipt_document["receipt_attestation"]["key_id"],
    )
    private_by_identity[receipt_identity] = receipt_issuer
    receipt_bytes = _signed_receipt(receipt_document, receipt_issuer)

    required_types = tuple(sorted(set(REQUIRED_ARTIFACT_TYPES) | {MANIFEST_TYPE}))
    policy, policy_envelope_bytes, policy_root_public_key_bytes = _make_signed_policy(
        private_by_identity,
        policy_version=receipt_document["policy_version"],
        required_artifact_types=required_types,
        revoked_identity=revoked_identity,
        omit_identity=omit_identity,
    )
    return {
        "manifest_document": manifest_document,
        "manifest_bytes": manifest_bytes,
        "manifest_sha256": manifest_digest,
        "receipt_document": receipt_document,
        "receipt_bytes": receipt_bytes,
        "receipt_issuer": receipt_issuer,
        "policy": policy,
        "policy_envelope_bytes": policy_envelope_bytes,
        "policy_root_public_key_bytes": policy_root_public_key_bytes,
        "policy_root_key_id": ROOT_KEY_ID,
        "minimum_policy_sequence": POLICY_SEQUENCE,
        "artifact_bytes_by_sha256": artifact_bytes_by_sha256,
        "signature_bytes_by_sha256": signature_bytes_by_sha256,
        "private_by_identity": private_by_identity,
    }


def inspect(data, **overrides):
    values = {
        "original_manifest_bytes": data["manifest_bytes"],
        "verified_trust_policy": data["policy"],
        "verification_time": NOW,
        "artifact_bytes_by_sha256": data["artifact_bytes_by_sha256"],
        "signature_bytes_by_sha256": data["signature_bytes_by_sha256"],
    }
    values.update(overrides)
    return verify_independent_provenance_with_nested_signatures(
        data["receipt_bytes"], **values
    )


def _rebind_manifest(data, manifest_document, signature_bytes_by_sha256):
    manifest_bytes = encode_manifest(manifest_document)
    manifest_digest = _sha(manifest_bytes)
    artifact_bytes = dict(data["artifact_bytes_by_sha256"])
    artifact_bytes.pop(data["manifest_sha256"])
    artifact_bytes[manifest_digest] = manifest_bytes

    receipt_document = copy.deepcopy(data["receipt_document"])
    manifest_claim = next(
        item for item in receipt_document["artifacts"]
        if item["artifact_type"] == MANIFEST_TYPE
    )
    manifest_claim["sha256"] = manifest_digest
    manifest_claim["byte_length"] = len(manifest_bytes)
    receipt_bytes = _signed_receipt(receipt_document, data["receipt_issuer"])

    return {
        **data,
        "manifest_document": manifest_document,
        "manifest_bytes": manifest_bytes,
        "manifest_sha256": manifest_digest,
        "receipt_document": receipt_document,
        "receipt_bytes": receipt_bytes,
        "artifact_bytes_by_sha256": artifact_bytes,
        "signature_bytes_by_sha256": signature_bytes_by_sha256,
    }


def inspect_signed_policy(data, **overrides):
    values = {
        "original_manifest_bytes": data["manifest_bytes"],
        "signed_policy_envelope_bytes": data["policy_envelope_bytes"],
        "pinned_root_public_key_bytes": data["policy_root_public_key_bytes"],
        "expected_root_key_id": data["policy_root_key_id"],
        "minimum_policy_sequence": data["minimum_policy_sequence"],
        "verification_time": NOW,
        "artifact_bytes_by_sha256": data["artifact_bytes_by_sha256"],
        "signature_bytes_by_sha256": data["signature_bytes_by_sha256"],
    }
    values.update(overrides)
    return verify_independent_provenance_with_signed_policy_and_nested_signatures(
        data["receipt_bytes"], **values
    )


class StatefulOffsetTimezone(tzinfo):
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=-2 if self.calls == 1 else 2)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "stateful-signed-policy-test"


class PhysicalManifestNestedSignatureChainTests(unittest.TestCase):
    def test_receipt_manifest_artifacts_and_all_nested_signatures_verify_but_block(self):
        data = make_case()
        result = inspect(data)
        self.assertEqual(result.artifact_count, len(REQUIRED_ARTIFACT_TYPES))
        self.assertEqual(
            result.signatures_verified,
            len(data["signature_bytes_by_sha256"]),
        )
        self.assertTrue(all(
            item.signature_verified for item in result.signature_results
        ))
        self.assertEqual(
            result.role_authorization_status,
            ROLE_AUTHORIZATION_UNVERIFIED,
        )
        self.assertTrue(all(
            item.role_authorization_status == ROLE_AUTHORIZATION_UNVERIFIED
            for item in result.signature_results
        ))
        self.assertEqual(
            result.signature_creation_time_status,
            "NOT_INDEPENDENTLY_PROVEN",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.status, SIGNATURE_CHAIN_STATUS)
        self.assertFalse(hasattr(result, "signature_bytes_by_sha256"))

    def test_signature_byte_digest_mismatch_is_rejected(self):
        data = make_case()
        first_digest = next(iter(data["signature_bytes_by_sha256"]))
        changed = dict(data["signature_bytes_by_sha256"])
        changed[first_digest] = changed[first_digest] + b"x"
        with self.assertRaisesRegex(ValueError, "nested signature SHA-256"):
            inspect(data, signature_bytes_by_sha256=changed)

    def test_missing_or_extra_signature_bytes_are_rejected(self):
        data = make_case()
        missing = dict(data["signature_bytes_by_sha256"])
        missing.pop(next(iter(missing)))
        with self.assertRaisesRegex(ValueError, "nested signature byte set mismatch"):
            inspect(data, signature_bytes_by_sha256=missing)
        extra = dict(data["signature_bytes_by_sha256"])
        extra["f" * 64] = b"unexpected"
        with self.assertRaisesRegex(ValueError, "nested signature byte set mismatch"):
            inspect(data, signature_bytes_by_sha256=extra)

    def test_rehashed_but_invalid_nested_signature_is_rejected(self):
        data = make_case()
        document = copy.deepcopy(data["manifest_document"])
        signature_map = dict(data["signature_bytes_by_sha256"])
        claim = document["signatures"][0]
        old_digest = claim["signature_sha256"]
        original = signature_map.pop(old_digest)
        invalid = bytes([original[0] ^ 1]) + original[1:]
        new_digest = _sha(invalid)
        claim["signature_sha256"] = new_digest
        signature_map[new_digest] = invalid
        changed = _rebind_manifest(data, document, signature_map)
        with self.assertRaisesRegex(
            ValueError, "nested Ed25519 signature verification failed"
        ):
            inspect(changed)

    def test_role_claim_tampering_breaks_manifest_signature(self):
        data = make_case()
        document = copy.deepcopy(data["manifest_document"])
        acta_digest = next(
            item["sha256"] for item in document["artifacts"]
            if item["artifact_type"] == "DRAW-ACTA"
        )
        acta_signatures = [
            item for item in document["signatures"]
            if item["artifact_sha256"] == acta_digest
        ]
        acta_signatures[0]["role"], acta_signatures[1]["role"] = (
            acta_signatures[1]["role"],
            acta_signatures[0]["role"],
        )
        changed = _rebind_manifest(
            data, document, dict(data["signature_bytes_by_sha256"])
        )
        with self.assertRaisesRegex(
            ValueError, "nested Ed25519 signature verification failed"
        ):
            inspect(changed)

    def test_signer_absent_from_verified_policy_is_rejected(self):
        initial = make_case()
        claim = initial["manifest_document"]["signatures"][0]
        identity = (claim["subject_id"], claim["key_id"])
        data = make_case(omit_identity=identity)
        with self.assertRaisesRegex(ValueError, "absent from verified policy"):
            inspect(data)

    def test_revoked_nested_signer_key_is_rejected(self):
        initial = make_case()
        claim = initial["manifest_document"]["signatures"][0]
        identity = (claim["subject_id"], claim["key_id"])
        data = make_case(revoked_identity=identity)
        with self.assertRaisesRegex(ValueError, "signer key is revoked"):
            inspect(data)

    def test_non_ed25519_claim_is_rejected_even_if_manifest_parser_accepts_it(self):
        data = make_case()
        document = copy.deepcopy(data["manifest_document"])
        document["signatures"][0]["algorithm"] = "rsa-pss-sha256"
        changed = _rebind_manifest(
            data, document, dict(data["signature_bytes_by_sha256"])
        )
        with self.assertRaisesRegex(ValueError, "unsupported algorithm"):
            inspect(changed)

    def test_signature_map_requires_exact_builtin_containers_and_bytes(self):
        data = make_case()

        class SignatureMap(dict):
            pass

        with self.assertRaisesRegex(TypeError, "exact dict"):
            inspect(data, signature_bytes_by_sha256=SignatureMap(
                data["signature_bytes_by_sha256"]
            ))
        mutable = dict(data["signature_bytes_by_sha256"])
        first = next(iter(mutable))
        mutable[first] = bytearray(mutable[first])
        with self.assertRaisesRegex(TypeError, "exact immutable bytes"):
            inspect(data, signature_bytes_by_sha256=mutable)

    def test_policy_key_validity_is_checked_at_verification_time(self):
        data = make_case()
        claim = data["manifest_document"]["signatures"][0]
        identity = (claim["subject_id"], claim["key_id"])
        # Rebuild the signed policy with this signer's validity ending before NOW.
        root_private = Ed25519PrivateKey.generate()
        entries = []
        for current_identity, private_key in sorted(data["private_by_identity"].items()):
            subject_id, key_id = current_identity
            entries.append({
                "issuer_id": subject_id,
                "key_id": key_id,
                "public_key_b64": base64.b64encode(
                    _raw_public_key(private_key)
                ).decode("ascii"),
                "valid_from_utc": "2026-01-01T00:00:00Z",
                "valid_until_utc": (
                    "2026-11-23T03:59:59Z"
                    if current_identity == identity
                    else "2027-01-01T00:00:00Z"
                ),
                "revoked": False,
            })
        document = {
            "schema_version": SCHEMA_VERSION,
            "policy_version": data["receipt_document"]["policy_version"],
            "policy_sequence": POLICY_SEQUENCE,
            "issuer_id": "synthetic-policy-authority",
            "root_key_id": ROOT_KEY_ID,
            "issued_at_utc": "2026-11-22T00:00:00Z",
            "not_before_utc": "2026-11-23T03:00:00Z",
            "expires_at_utc": "2026-12-01T00:00:00Z",
            "issuer_keys": entries,
            "required_artifact_types": list(sorted(
                set(REQUIRED_ARTIFACT_TYPES) | {MANIFEST_TYPE}
            )),
            "signature": {"algorithm": "ed25519", "signature_b64": ""},
        }
        unsigned = copy.deepcopy(document)
        unsigned.pop("signature")
        document["signature"]["signature_b64"] = base64.b64encode(
            root_private.sign(_canonical_json(unsigned))
        ).decode("ascii")
        raw = _canonical_json(document)
        expired_policy = verify_signed_trust_policy(
            raw,
            pinned_root_public_key_bytes=_raw_public_key(root_private),
            expected_root_key_id=ROOT_KEY_ID,
            minimum_policy_sequence=POLICY_SEQUENCE,
            verification_time=NOW,
        )
        with self.assertRaisesRegex(ValueError, "outside policy validity"):
            inspect(data, verified_trust_policy=expired_policy)

    def test_claimed_roles_are_not_promoted_to_authorized_roles(self):
        data = make_case()
        result = inspect(data)
        self.assertTrue(all(
            item.claimed_role for item in result.signature_results
        ))
        self.assertEqual(
            {item.role_authorization_status for item in result.signature_results},
            {ROLE_AUTHORIZATION_UNVERIFIED},
        )
        self.assertIn(
            "SIGNER_ROLE_AUTHORIZATION_NOT_BOUND_TO_POLICY_V1",
            result.remaining_blockers,
        )


    def test_raw_signed_policy_is_verified_inside_nested_signature_chain(self):
        data = make_case()
        result = inspect_signed_policy(data)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.policy_envelope_sha256, _sha(data["policy_envelope_bytes"]))
        self.assertEqual(result.policy_sequence, POLICY_SEQUENCE)
        self.assertEqual(result.signatures_verified, len(data["manifest_document"]["signatures"]))
        self.assertEqual(result.status, SIGNATURE_CHAIN_STATUS)

    def test_tampered_raw_policy_envelope_is_rejected_before_nested_verification(self):
        data = make_case()
        tampered = data["policy_envelope_bytes"].replace(
            b'"policy_sequence":7', b'"policy_sequence":8', 1
        )
        self.assertNotEqual(tampered, data["policy_envelope_bytes"])
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            inspect_signed_policy(data, signed_policy_envelope_bytes=tampered)

    def test_wrong_root_pin_is_rejected(self):
        data = make_case()
        wrong_root = bytes([data["policy_root_public_key_bytes"][0] ^ 1]) + data["policy_root_public_key_bytes"][1:]
        with self.assertRaisesRegex(ValueError, "signature verification failed"):
            inspect_signed_policy(data, pinned_root_public_key_bytes=wrong_root)

    def test_wrong_root_key_id_is_rejected(self):
        data = make_case()
        with self.assertRaisesRegex(ValueError, "root_key_id does not match"):
            inspect_signed_policy(data, expected_root_key_id="untrusted-root-id")

    def test_policy_rollback_floor_is_enforced_inside_composition(self):
        data = make_case()
        with self.assertRaisesRegex(ValueError, "below the externally pinned minimum"):
            inspect_signed_policy(data, minimum_policy_sequence=POLICY_SEQUENCE + 1)

    def test_caller_cannot_substitute_a_preverified_policy_object(self):
        data = make_case()
        with self.assertRaisesRegex(TypeError, "unexpected keyword argument"):
            inspect_signed_policy(data, verified_trust_policy=data["policy"])

    def test_stateful_verification_clock_is_sampled_once_for_entire_chain(self):
        data = make_case()
        tz = StatefulOffsetTimezone()
        caller_time = datetime(2026, 11, 23, 2, 0, tzinfo=tz)
        result = inspect_signed_policy(data, verification_time=caller_time)
        self.assertEqual(tz.calls, 1)
        self.assertEqual(result.verification_time_utc, NOW)
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)


if __name__ == "__main__":
    unittest.main()
