"""Synthetic tests for signed trust-policy/TSA-policy/RFC3161 composition."""
from __future__ import annotations

import base64
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone

from asn1crypto import cms, tsp, x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.independent_trust_adapter import ProvenanceStatus
from origen.trust_policy_integration_v1 import ROOT_CHAIN_REMAINING_BLOCKERS
from origen.trust_policy_envelope_v1 import SCHEMA_VERSION
from origen.trust_policy_rfc3161_integration_v1 import (
    OutputSealTimestampEvidence,
    inspect_signed_root_attestation_chain_with_output_seal_timestamps,
)
from test_rfc3161_tsa_verifier_v1 import _certs
from test_trust_policy_integration_v1 import ROOT_KEY_ID
from test_trust_receipt_v1 import valid_document
from test_trust_verifier_v1 import sign_document

UTC = timezone.utc
NOW = datetime(2026, 11, 25, 6, 0, tzinfo=UTC)
CLOSE = datetime(2026, 11, 26, 3, 0, tzinfo=UTC)
SEAL_TIMES = (
    datetime(2026, 11, 25, 5, 50, tzinfo=UTC),
    datetime(2026, 11, 25, 5, 51, tzinfo=UTC),
)
ATTESTATION_TIME = datetime(2026, 11, 25, 5, 55, tzinfo=UTC)
POLICY_ISSUED = "2026-11-24T10:00:00Z"
POLICY_NOT_BEFORE = "2026-11-24T11:00:00Z"
POLICY_EXPIRES = "2026-12-01T00:00:00Z"
ALLOWED_TSA_OID = "1.2.3.4.5"


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z").replace(".000000Z", "Z")


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sign_envelope(document, root_private):
    unsigned = dict(document)
    unsigned.pop("signature")
    document["signature"]["signature_b64"] = base64.b64encode(
        root_private.sign(_canonical(unsigned))
    ).decode("ascii")
    return _canonical(document)


def _signed_policy_pair(
    issuer_public_bytes,
    tsa_root_der,
    *,
    policy_authority_id="tsa-test",
    policy_oids=(ALLOWED_TSA_OID,),
    tsa_policy_revoked=False,
    tsa_policy_sequence=7,
    bound_policy_digest_override=None,
):
    root_private = Ed25519PrivateKey.generate()
    root_public = root_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trust_policy = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": "policy-2026-11",
        "policy_sequence": 7,
        "issuer_id": "policy-authority",
        "root_key_id": ROOT_KEY_ID,
        "issued_at_utc": POLICY_ISSUED,
        "not_before_utc": POLICY_NOT_BEFORE,
        "expires_at_utc": POLICY_EXPIRES,
        "issuer_keys": [{
            "issuer_id": "independent-verifier",
            "key_id": "verifier-key-1",
            "public_key_b64": base64.b64encode(issuer_public_bytes).decode("ascii"),
            "valid_from_utc": "2026-01-01T00:00:00Z",
            "valid_until_utc": "2027-01-01T00:00:00Z",
            "revoked": False,
        }],
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    trust_policy_bytes = _sign_envelope(trust_policy, root_private)
    tsa_policy = {
        "schema_version": "origen.timestamp-authority-policy.v1",
        "root_key_id": ROOT_KEY_ID,
        "policy_sequence": tsa_policy_sequence,
        "trust_policy_envelope_sha256": (
            bound_policy_digest_override
            if bound_policy_digest_override is not None
            else hashlib.sha256(trust_policy_bytes).hexdigest()
        ),
        "issued_at_utc": POLICY_ISSUED,
        "not_before_utc": POLICY_NOT_BEFORE,
        "expires_at_utc": POLICY_EXPIRES,
        "authorities": [{
            "authority_id": policy_authority_id,
            "root_certificate_sha256": hashlib.sha256(tsa_root_der).hexdigest(),
            "policy_oids": list(policy_oids),
            "valid_from_utc": POLICY_NOT_BEFORE,
            "valid_until_utc": POLICY_EXPIRES,
            "revoked": tsa_policy_revoked,
        }],
        "signature": {"algorithm": "ed25519", "signature_b64": ""},
    }
    tsa_policy_bytes = _sign_envelope(tsa_policy, root_private)
    return trust_policy_bytes, tsa_policy_bytes, root_public


def _timestamp_token(
    data, root, tsa, tsa_key, *, nonce, gen_time, accuracy,
    policy_oid=ALLOWED_TSA_OID,
):
    tst_info = tsp.TSTInfo({
        "version": "v1",
        "policy": policy_oid,
        "message_imprint": {
            "hash_algorithm": {"algorithm": "sha256"},
            "hashed_message": hashlib.sha256(data).digest(),
        },
        "serial_number": 1000 + nonce,
        "gen_time": gen_time,
        "accuracy": accuracy,
        "nonce": nonce,
    })
    tst_bytes = tst_info.dump()
    tsa_der = tsa.public_bytes(serialization.Encoding.DER)
    tsa_asn1 = asn1_x509.Certificate.load(tsa_der)
    signing_certificate_v2 = tsp.SigningCertificateV2({
        "certs": [{
            "cert_hash": hashlib.sha256(tsa_der).digest(),
        }],
    })
    attrs = cms.CMSAttributes([
        cms.CMSAttribute({"type": "content_type", "values": ["tst_info"]}),
        cms.CMSAttribute({
            "type": "message_digest",
            "values": [hashlib.sha256(tst_bytes).digest()],
        }),
        cms.CMSAttribute({
            "type": "signing_certificate_v2",
            "values": [signing_certificate_v2],
        }),
    ])
    signature = tsa_key.sign(
        attrs.untag().dump(), padding.PKCS1v15(), hashes.SHA256()
    )
    signer = cms.SignerInfo({
        "version": "v1",
        "sid": {
            "issuer_and_serial_number": {
                "issuer": tsa_asn1.issuer,
                "serial_number": tsa_asn1.serial_number,
            }
        },
        "digest_algorithm": {"algorithm": "sha256"},
        "signed_attrs": attrs,
        "signature_algorithm": {"algorithm": "rsassa_pkcs1v15"},
        "signature": signature,
    })
    encap = cms.EncapsulatedContentInfo({
        "content_type": "tst_info",
        "content": tst_info,
    })
    signed_data = cms.SignedData({
        "version": "v3",
        "digest_algorithms": [{"algorithm": "sha256"}],
        "encap_content_info": encap,
        "certificates": [tsa_asn1],
        "signer_infos": [signer],
    })
    return cms.ContentInfo({
        "content_type": "signed_data",
        "content": signed_data,
    }).dump()


def _fixture(
    *,
    token_data_overrides=None,
    token_times=None,
    declared_times=None,
    accuracy=None,
    verification_time=NOW,
    receipt_authority_id="tsa-test",
    policy_authority_id="tsa-test",
    policy_oids=(ALLOWED_TSA_OID,),
    token_policy_oids=None,
    tsa_policy_revoked=False,
    tsa_policy_sequence=7,
    bound_policy_digest_override=None,
):
    token_data_overrides = token_data_overrides or {}
    token_times = token_times or SEAL_TIMES
    declared_times = declared_times or token_times
    token_policy_oids = token_policy_oids or (ALLOWED_TSA_OID, ALLOWED_TSA_OID)

    issuer_private = Ed25519PrivateKey.generate()
    issuer_public = issuer_private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    document = valid_document()
    contest_id = "900001"
    document["target"]["contest_id"] = contest_id
    document["target"]["draw_close_at_utc"] = _stamp(CLOSE)
    target_bytes = json.dumps([contest_id], separators=(",", ":"), ensure_ascii=True).encode("ascii")
    document["target"]["target_list_sha256"] = hashlib.sha256(target_bytes).hexdigest()
    for artifact in document["artifacts"]:
        artifact["contest_id"] = contest_id
    for seal in document["output_seals"]:
        seal["target_contest_id"] = contest_id

    root, tsa, tsa_key = _certs()
    root_der = root.public_bytes(serialization.Encoding.DER)
    evidence = []
    for index, seal in enumerate(document["output_seals"]):
        generator = Ed25519PrivateKey.generate()
        signature_bytes = generator.sign(f"synthetic-output-seal-{index}".encode("ascii"))
        signature_digest = hashlib.sha256(signature_bytes).hexdigest()
        seal["signature_sha256"] = signature_digest
        document["signers"][index]["signature_sha256"] = signature_digest
        seal_time = declared_times[index]
        token_gen_time = token_times[index]
        seal["created_at_utc"] = _stamp(seal_time)
        proof = document["trusted_time_proofs"][index + 1]
        proof["authority_id"] = receipt_authority_id
        proof["event_id"] = f"event-seal-{index}"
        proof["event_at_utc"] = _stamp(seal_time)
        token_data = token_data_overrides.get(index, signature_bytes)
        nonce = 12345 + index
        token = _timestamp_token(
            token_data,
            root,
            tsa,
            tsa_key,
            nonce=nonce,
            gen_time=token_gen_time,
            accuracy=accuracy,
            policy_oid=token_policy_oids[index],
        )
        proof_digest = hashlib.sha256(token).hexdigest()
        proof["proof_sha256"] = proof_digest
        seal["timestamp_proof_sha256"] = proof_digest
        evidence.append(OutputSealTimestampEvidence(
            event_id=proof["event_id"],
            token_der=token,
            signature_bytes=signature_bytes,
            expected_nonce=nonce,
        ))

    latest_seal_time = max(declared_times)
    attestation_time = max(ATTESTATION_TIME, latest_seal_time + timedelta(seconds=5))
    document["trusted_time_proofs"][0]["event_at_utc"] = _stamp(attestation_time)
    document["receipt_attestation"]["signed_at_utc"] = _stamp(attestation_time)
    receipt_bytes = sign_document(document, issuer_private)
    trust_policy_bytes, tsa_policy_bytes, policy_root_public = _signed_policy_pair(
        issuer_public,
        root_der,
        policy_authority_id=policy_authority_id,
        policy_oids=policy_oids,
        tsa_policy_revoked=tsa_policy_revoked,
        tsa_policy_sequence=tsa_policy_sequence,
        bound_policy_digest_override=bound_policy_digest_override,
    )
    return {
        "receipt_bytes": receipt_bytes,
        "policy_bytes": trust_policy_bytes,
        "tsa_policy_bytes": tsa_policy_bytes,
        "policy_root_public": policy_root_public,
        "tsa_root_der": root_der,
        # Ephemeral fixture material is exposed only to sibling synthetic tests.
        "tsa_root_certificate": root,
        "tsa_signer_certificate": tsa,
        "tsa_signer_private_key": tsa_key,
        "evidence": tuple(evidence),
        "verification_time": verification_time,
    }


def _inspect(fixture, **overrides):
    values = {
        "pinned_root_public_key_bytes": fixture["policy_root_public"],
        "expected_root_key_id": ROOT_KEY_ID,
        "minimum_policy_sequence": 7,
        "verification_time": fixture["verification_time"],
        "signed_timestamp_authority_policy_bytes": fixture["tsa_policy_bytes"],
        "output_seal_timestamp_evidence": fixture["evidence"],
        "pinned_tsa_root_certificate_der": fixture["tsa_root_der"],
    }
    values.update(overrides)
    return inspect_signed_root_attestation_chain_with_output_seal_timestamps(
        fixture["receipt_bytes"], fixture["policy_bytes"], **values
    )


class TestSignedRootRFC3161OutputSealIntegrationV1(unittest.TestCase):
    def test_two_exact_seal_tokens_verify_under_signed_tsa_policy_but_provenance_stays_blocked(self):
        fixture = _fixture(accuracy={"seconds": 1})
        result = _inspect(fixture)
        self.assertEqual(len(result.output_seal_timestamps), 2)
        self.assertEqual(
            {item.event_id for item in result.output_seal_timestamps},
            {"event-seal-0", "event-seal-1"},
        )
        self.assertEqual(
            {item.tsa_policy_oid for item in result.output_seal_timestamps},
            {ALLOWED_TSA_OID},
        )
        self.assertTrue(all(item.accuracy_microseconds == 1_000_000 for item in result.output_seal_timestamps))
        self.assertEqual(result.timestamp_authority_id, "tsa-test")
        self.assertEqual(result.timestamp_authority_policy_sequence, 7)
        self.assertEqual(len(result.timestamp_authority_policy_sha256), 64)
        self.assertEqual(
            result.timestamp_authority_source,
            "ROOT_SIGNED_POLICY_RELATIVE_TO_CALLER_SUPPLIED_ROOT",
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertIn(
            "RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED",
            result.remaining_blockers,
        )
        self.assertIn("TSA_REVOCATION_FRESHNESS_NOT_CHECKED", result.remaining_blockers)
        self.assertNotIn("RFC3161_TIMESTAMP_TOKENS_NOT_VERIFIED", result.root_chain.remaining_blockers)

    def test_evidence_order_is_not_semantically_significant(self):
        fixture = _fixture(accuracy={"seconds": 1})
        result = _inspect(
            fixture,
            output_seal_timestamp_evidence=tuple(reversed(fixture["evidence"])),
        )
        self.assertEqual(len(result.output_seal_timestamps), 2)

    def test_missing_one_seal_token_fails_closed(self):
        fixture = _fixture(accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "exactly two"):
            _inspect(fixture, output_seal_timestamp_evidence=fixture["evidence"][:1])

    def test_duplicate_event_identity_fails_closed(self):
        fixture = _fixture(accuracy={"seconds": 1})
        first, second = fixture["evidence"]
        duplicate = OutputSealTimestampEvidence(
            event_id=first.event_id,
            token_der=second.token_der,
            signature_bytes=second.signature_bytes,
            expected_nonce=second.expected_nonce,
        )
        with self.assertRaisesRegex(ValueError, "duplicate event IDs"):
            _inspect(fixture, output_seal_timestamp_evidence=(first, duplicate))

    def test_receipt_authority_must_be_present_in_root_signed_tsa_policy(self):
        fixture = _fixture(policy_authority_id="different-authority")
        with self.assertRaisesRegex(ValueError, "not authorized"):
            _inspect(fixture)

    def test_revoked_tsa_authority_is_rejected(self):
        fixture = _fixture(tsa_policy_revoked=True, accuracy={"seconds": 1})
        with self.assertRaisesRegex(ValueError, "is revoked"):
            _inspect(fixture)

    def test_caller_supplied_tsa_root_must_match_root_signed_policy(self):
        fixture = _fixture(accuracy={"seconds": 1})
        other_root, _, _ = _certs()
        other_root_der = other_root.public_bytes(serialization.Encoding.DER)
        with self.assertRaisesRegex(ValueError, "does not match root-signed"):
            _inspect(fixture, pinned_tsa_root_certificate_der=other_root_der)

    def test_tsa_policy_oid_must_be_authorized(self):
        fixture = _fixture(
            accuracy={"seconds": 1},
            token_policy_oids=("1.2.3.4.6", ALLOWED_TSA_OID),
        )
        with self.assertRaisesRegex(ValueError, "policy OID is not authorized"):
            _inspect(fixture)

    def test_tsa_policy_must_bind_exact_verified_trust_policy_digest(self):
        fixture = _fixture(
            accuracy={"seconds": 1},
            bound_policy_digest_override="a" * 64,
        )
        with self.assertRaisesRegex(ValueError, "not bound to the verified trust-policy"):
            _inspect(fixture)

    def test_tsa_policy_sequence_must_match_verified_trust_policy_sequence(self):
        fixture = _fixture(accuracy={"seconds": 1}, tsa_policy_sequence=8)
        with self.assertRaisesRegex(ValueError, "sequence does not match"):
            _inspect(fixture)

    def test_tsa_policy_signature_tampering_fails_closed(self):
        fixture = _fixture(accuracy={"seconds": 1})
        tampered = bytearray(fixture["tsa_policy_bytes"])
        tampered[-3] ^= 1
        with self.assertRaises(ValueError):
            _inspect(fixture, signed_timestamp_authority_policy_bytes=bytes(tampered))

    def test_token_digest_must_match_signed_receipt_reference(self):
        fixture = _fixture(accuracy={"seconds": 1})
        first, second = fixture["evidence"]
        altered = OutputSealTimestampEvidence(
            event_id=first.event_id,
            token_der=first.token_der + b"\\x00",
            signature_bytes=first.signature_bytes,
            expected_nonce=first.expected_nonce,
        )
        with self.assertRaisesRegex(ValueError, "token SHA-256"):
            _inspect(fixture, output_seal_timestamp_evidence=(altered, second))

    def test_token_imprint_must_match_exact_seal_signature_bytes(self):
        fixture = _fixture(
            accuracy={"seconds": 1},
            token_data_overrides={0: b"not-the-seal-signature"},
        )
        with self.assertRaisesRegex(ValueError, "message imprint"):
            _inspect(fixture)

    def test_gen_time_must_match_signed_event_time(self):
        token_times = (SEAL_TIMES[0] + timedelta(seconds=1), SEAL_TIMES[1])
        fixture = _fixture(
            accuracy={"seconds": 1},
            token_times=token_times,
            declared_times=SEAL_TIMES,
        )
        with self.assertRaisesRegex(ValueError, "genTime does not match"):
            _inspect(fixture)

    def test_missing_accuracy_cannot_establish_strict_preclose_bound(self):
        fixture = _fixture(accuracy=None)
        with self.assertRaisesRegex(ValueError, "accuracy is absent"):
            _inspect(fixture)

    def test_accuracy_interval_crossing_close_is_rejected(self):
        late_seal = CLOSE - timedelta(milliseconds=500)
        fixture = _fixture(
            accuracy={"seconds": 1},
            token_times=(late_seal, SEAL_TIMES[1]),
            verification_time=CLOSE + timedelta(seconds=10),
        )
        with self.assertRaisesRegex(ValueError, "not strictly before"):
            _inspect(fixture)


if __name__ == "__main__":
    unittest.main()
