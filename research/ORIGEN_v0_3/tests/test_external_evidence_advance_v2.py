from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from origen.deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    ExternalEvidenceAdvanceV2,
    _external_evidence_advance_copy,
)
from origen.timestamp_nonce_challenge_v1 import (
    TimestampNonceChallengeV1,
    copy_timestamp_nonce_challenge,
    timestamp_nonce_challenge_sha256,
)
from test_transparency_ledger_bundle_verifier_v2 import build_v2_case


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def valid_advance() -> ExternalEvidenceAdvanceV2:
    values, _ = build_v2_case()
    checkpoint = json.loads(values["raw_signed_checkpoint_bytes"].decode("utf-8"))
    raw_old_checkpoint = b"synthetic-old-checkpoint"
    raw_registry = b"synthetic-witness-registry"
    raw_receipt = b"synthetic-receipt"
    raw_custody = b"synthetic-custody-record"
    raw_portfolio = b"synthetic-portfolio"
    raw_custody_signature = b"synthetic-custody-signature"

    return ExternalEvidenceAdvanceV2(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id="research-backend-1",
        log_id=values["expected_log_id"],
        log_key_id=values["expected_log_key_id"],
        log_public_key_sha256=sha(values["pinned_log_public_key_bytes"]),
        old_tree_size=6,
        old_root_sha256="1" * 64,
        old_checkpoint_sha256=sha(raw_old_checkpoint),
        new_tree_size=checkpoint["tree_size"],
        new_root_sha256=checkpoint["root_hash"],
        new_checkpoint_sha256=sha(values["raw_signed_checkpoint_bytes"]),
        registry_id="research-registry-1",
        registry_root_key_id="research-registry-root-1",
        registry_root_public_key_sha256="2" * 64,
        registry_sequence=1,
        registry_sha256=sha(raw_registry),
        raw_manifest_bytes=values["raw_manifest_bytes"],
        raw_ledger_entry_bytes=values["raw_ledger_entry_bytes"],
        raw_inclusion_proof_bytes=values["raw_inclusion_proof_bytes"],
        raw_old_checkpoint_bytes=raw_old_checkpoint,
        raw_new_checkpoint_bytes=values["raw_signed_checkpoint_bytes"],
        raw_consistency_proof_bytes=b"synthetic-consistency-proof",
        raw_registry_bytes=raw_registry,
        raw_witness_statement_bytes=(b"synthetic-witness-a", b"synthetic-witness-b"),
        receipt_sha256=sha(raw_receipt),
        policy_envelope_sha256=sha(values["signed_policy_envelope_bytes"]),
        raw_receipt_bytes=raw_receipt,
        raw_policy_envelope_bytes=values["signed_policy_envelope_bytes"],
        raw_custody_record_bytes=raw_custody,
        raw_portfolio_bytes=raw_portfolio,
        raw_custody_signature_bytes=raw_custody_signature,
        custodian_key_id="synthetic-custodian-key",
        raw_timestamp_token_der=b"synthetic-custody-token",
        raw_policy_timestamp_token_der=b"synthetic-policy-token",
        raw_artifact_bytes_by_sha256=tuple(
            sorted(values["artifact_bytes_by_sha256"].items())
        ),
        raw_signature_bytes_by_sha256=tuple(
            sorted(values["signature_bytes_by_sha256"].items())
        ),
        raw_timestamp_bundle_bytes=values["raw_timestamp_bundle_bytes"],
        raw_nested_signature_bundle_timestamp_token_der=values["timestamp_token_der"],
        nested_signature_bundle_timestamp_nonce=values["expected_nonce"],
    )


def test_v2_advance_copies_and_binds_exact_sidecar_token_and_leaf():
    advance = valid_advance()

    copied = _external_evidence_advance_copy(advance)

    assert type(copied) is ExternalEvidenceAdvanceV2
    assert copied.raw_timestamp_bundle_bytes == advance.raw_timestamp_bundle_bytes
    assert (
        copied.raw_nested_signature_bundle_timestamp_token_der
        == advance.raw_nested_signature_bundle_timestamp_token_der
    )
    assert copied.nested_signature_bundle_timestamp_nonce == 88091


def test_v2_advance_rejects_token_substitution_against_ledger_leaf():
    advance = valid_advance()
    altered = replace(
        advance,
        raw_nested_signature_bundle_timestamp_token_der=(
            advance.raw_nested_signature_bundle_timestamp_token_der + b"\x00"
        ),
    )

    with pytest.raises(ValueError, match="does not commit to the exact RFC 3161 token"):
        _external_evidence_advance_copy(altered)


def test_v2_advance_rejects_noncanonical_or_substituted_sidecar_bytes():
    advance = valid_advance()

    with pytest.raises(ValueError, match="do not equal the canonical exact-evidence sidecar"):
        _external_evidence_advance_copy(
            replace(advance, raw_timestamp_bundle_bytes=advance.raw_timestamp_bundle_bytes + b" ")
        )


def test_v2_advance_rejects_v1_leaf_downgrade():
    advance = valid_advance()
    entry = json.loads(advance.raw_ledger_entry_bytes.decode("utf-8"))
    entry["schema_version"] = "origen.transparency-ledger-entry.v1"
    entry.pop("timestamp_bundle_sha256")
    entry.pop("timestamp_token_sha256")

    with pytest.raises(ValueError, match="fields mismatch"):
        _external_evidence_advance_copy(
            replace(advance, raw_ledger_entry_bytes=canonical(entry))
        )


def test_v2_advance_rejects_leaf_with_wrong_sidecar_digest():
    advance = valid_advance()
    entry = json.loads(advance.raw_ledger_entry_bytes.decode("utf-8"))
    entry["timestamp_bundle_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="does not commit to the exact timestamp bundle"):
        _external_evidence_advance_copy(
            replace(advance, raw_ledger_entry_bytes=canonical(entry))
        )


@pytest.mark.parametrize("nonce", [True, 0, -1, (1 << 63)])
def test_v2_advance_rejects_invalid_third_nonce(nonce):
    with pytest.raises(ValueError, match="exact positive signed-64-bit integer"):
        _external_evidence_advance_copy(
            replace(valid_advance(), nested_signature_bundle_timestamp_nonce=nonce)
        )


def make_challenge(*, bundle_nonce=33):
    return TimestampNonceChallengeV1(
        challenge_id="research-challenge-1",
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id="research-backend-1",
        policy_timestamp_nonce=11,
        custody_timestamp_nonce=22,
        state_generation=7,
        root_generation=2,
        physical_trust_context_generation=3,
        physical_trust_context_sha256="a" * 64,
        issued_at_utc=datetime(2026, 11, 27, 20, 0, tzinfo=timezone.utc),
        expires_at_utc=datetime(2026, 11, 27, 20, 5, tzinfo=timezone.utc),
        nested_signature_bundle_timestamp_nonce=bundle_nonce,
    )


def test_optional_third_nonce_is_copied_and_bound_into_challenge_digest():
    challenge = make_challenge()

    copied = copy_timestamp_nonce_challenge(challenge)

    assert copied.nested_signature_bundle_timestamp_nonce == 33
    assert timestamp_nonce_challenge_sha256(copied) == timestamp_nonce_challenge_sha256(challenge)
    assert timestamp_nonce_challenge_sha256(challenge) != timestamp_nonce_challenge_sha256(
        replace(challenge, nested_signature_bundle_timestamp_nonce=34)
    )


def test_optional_third_nonce_must_be_distinct_from_policy_and_custody_nonces():
    with pytest.raises(ValueError, match="all present timestamp challenge nonces must be distinct"):
        make_challenge(bundle_nonce=11)


def test_v1_challenge_remains_valid_without_the_optional_third_nonce():
    challenge = make_challenge(bundle_nonce=None)

    copied = copy_timestamp_nonce_challenge(challenge)

    assert copied.nested_signature_bundle_timestamp_nonce is None
