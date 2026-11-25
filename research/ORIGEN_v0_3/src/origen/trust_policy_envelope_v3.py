"""V3 signed trust policies with key-to-role-to-artifact authorization.

V3 extends the domain-bound V2 envelope. Every issuer key must carry a
root-signed, explicit authorization matrix. This is authorization relative to
the caller-supplied root only; it does not authenticate institutional identity.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .trust_policy_envelope_v1 import (
    MAX_POLICY_BYTES,
    MAX_POLICY_KEYS,
    MAX_POLICY_SEQUENCE,
    _b64,
    _canonical,
    _identifier,
    _pairs_no_duplicates,
    _parse_bounded_integer,
    _timestamp,
    _validate_json_depth,
)
from .trust_verifier_v1 import TrustPolicy, TrustedIssuerKey

SCHEMA_VERSION_V3 = "origen.trust-policy-envelope.v3"
MAX_AUTHORIZATIONS_PER_KEY = 32
MAX_ARTIFACT_TYPES_PER_AUTHORIZATION = 32


@dataclass(frozen=True, slots=True)
class VerifiedTrustPolicyV3:
    """V3 policy authenticated relative to caller-supplied deployment pins."""

    policy: TrustPolicy
    policy_domain: str
    policy_sequence: int
    root_key_id: str
    envelope_sha256: str
    issued_at_utc: datetime
    expires_at_utc: datetime
    # (issuer_id, key_id, role, allowed artifact types), all from signed bytes.
    key_authorizations: tuple[tuple[str, str, str, tuple[str, ...]], ...]


def verify_signed_trust_policy_v3(
    raw: bytes,
    *,
    pinned_root_public_key_bytes: bytes,
    expected_root_key_id: str,
    expected_policy_domain: str,
    minimum_policy_sequence: int,
    verification_time: datetime,
) -> VerifiedTrustPolicyV3:
    """Verify canonical V3 policy bytes and their signed role authorization.

    Root pin, key ID, domain expectation, sequence floor and clock remain
    caller-supplied. The returned role matrix is cryptographically bound to
    the envelope but is not proof that the root or identities are institutional.
    """
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_POLICY_BYTES:
        raise ValueError("policy envelope must be exact bytes within size limit")
    if type(pinned_root_public_key_bytes) is not bytes or len(pinned_root_public_key_bytes) != 32:
        raise ValueError("pinned root public key must be exactly 32 immutable bytes")

    root_key_id = _identifier(expected_root_key_id, "expected_root_key_id")
    policy_domain = _identifier(expected_policy_domain, "expected_policy_domain")
    if type(minimum_policy_sequence) is not int or not 1 <= minimum_policy_sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError("minimum_policy_sequence must be an exact positive signed 64-bit integer")
    if type(verification_time) is not datetime or verification_time.tzinfo is None:
        raise ValueError("verification_time must be a timezone-aware exact datetime")
    try:
        offset = verification_time.utcoffset()
    except Exception as exc:
        raise ValueError("verification_time timezone is invalid") from exc
    if offset is None:
        raise ValueError("verification_time must be timezone-aware")
    now = (verification_time.replace(tzinfo=None) - offset).replace(tzinfo=timezone.utc)

    _validate_json_depth(raw)
    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs_no_duplicates,
            parse_int=_parse_bounded_integer,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-standard JSON constant: {value}")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("policy envelope must be valid UTF-8 JSON") from exc
    if type(document) is not dict:
        raise ValueError("policy envelope must be a JSON object")
    if raw != _canonical(document):
        raise ValueError("policy envelope JSON must use canonical UTF-8 encoding")

    fields = {
        "schema_version", "policy_domain", "policy_version", "policy_sequence",
        "issuer_id", "root_key_id", "issued_at_utc", "not_before_utc",
        "expires_at_utc", "issuer_keys", "signature",
    }
    if set(document) != fields:
        raise ValueError("V3 policy envelope fields mismatch")
    if document["schema_version"] != SCHEMA_VERSION_V3:
        raise ValueError("unsupported trust-policy envelope schema")
    actual_domain = _identifier(document["policy_domain"], "policy_domain")
    if actual_domain != policy_domain:
        raise ValueError("policy domain does not match externally expected deployment domain")
    policy_version = _identifier(document["policy_version"], "policy_version")
    _identifier(document["issuer_id"], "issuer_id")
    if document["root_key_id"] != root_key_id:
        raise ValueError("policy root_key_id does not match pinned deployment key")

    sequence = document["policy_sequence"]
    if type(sequence) is not int or not 1 <= sequence <= MAX_POLICY_SEQUENCE:
        raise ValueError("policy_sequence must be a positive signed 64-bit integer")
    if sequence < minimum_policy_sequence:
        raise ValueError("policy sequence is below the externally pinned minimum")

    issued = _timestamp(document["issued_at_utc"], "issued_at_utc")
    not_before = _timestamp(document["not_before_utc"], "not_before_utc")
    expires = _timestamp(document["expires_at_utc"], "expires_at_utc")
    if not (issued <= now and not_before <= now < expires):
        raise ValueError("policy envelope is not currently valid at verification time")
    if not (issued <= not_before <= expires):
        raise ValueError("policy envelope validity chronology is inverted")

    entries = document["issuer_keys"]
    if type(entries) is not list or not 1 <= len(entries) <= MAX_POLICY_KEYS:
        raise ValueError(f"issuer_keys must contain 1..{MAX_POLICY_KEYS} entries")
    trusted_keys = []
    authorizations: list[tuple[str, str, str, tuple[str, ...]]] = []
    seen_pairs = set()
    seen_bytes = set()
    for index, item in enumerate(entries):
        if type(item) is not dict or set(item) != {
            "issuer_id", "key_id", "public_key_b64", "valid_from_utc",
            "valid_until_utc", "revoked", "authorizations",
        }:
            raise ValueError(f"issuer_keys[{index}] fields mismatch")
        key_issuer = _identifier(item["issuer_id"], f"issuer_keys[{index}].issuer_id")
        key_id = _identifier(item["key_id"], f"issuer_keys[{index}].key_id")
        public_bytes = _b64(
            item["public_key_b64"], f"issuer_keys[{index}].public_key_b64", 32
        )
        valid_from = _timestamp(
            item["valid_from_utc"], f"issuer_keys[{index}].valid_from_utc"
        )
        valid_until = _timestamp(
            item["valid_until_utc"], f"issuer_keys[{index}].valid_until_utc"
        )
        if valid_from > valid_until:
            raise ValueError(f"issuer_keys[{index}] validity interval is inverted")
        if type(item["revoked"]) is not bool:
            raise ValueError(f"issuer_keys[{index}].revoked must be an exact boolean")
        pair = (key_issuer, key_id)
        if pair in seen_pairs:
            raise ValueError("duplicate issuer/key identifiers in signed policy")
        if public_bytes in seen_bytes:
            raise ValueError("public key reused across signed policy identities")

        raw_authorizations = item["authorizations"]
        if (
            type(raw_authorizations) is not list
            or not 1 <= len(raw_authorizations) <= MAX_AUTHORIZATIONS_PER_KEY
        ):
            raise ValueError(
                f"issuer_keys[{index}].authorizations must contain "
                f"1..{MAX_AUTHORIZATIONS_PER_KEY} entries"
            )
        seen_roles: set[str] = set()
        parsed_for_key: list[tuple[str, tuple[str, ...]]] = []
        for auth_index, auth in enumerate(raw_authorizations):
            if type(auth) is not dict or set(auth) != {"role", "artifact_types"}:
                raise ValueError(
                    f"issuer_keys[{index}].authorizations[{auth_index}] fields mismatch"
                )
            role = _identifier(
                auth["role"],
                f"issuer_keys[{index}].authorizations[{auth_index}].role",
            )
            if role in seen_roles:
                raise ValueError("duplicate role authorization for issuer/key")
            raw_types = auth["artifact_types"]
            if (
                type(raw_types) is not list
                or not 1 <= len(raw_types) <= MAX_ARTIFACT_TYPES_PER_AUTHORIZATION
            ):
                raise ValueError(
                    f"issuer_keys[{index}].authorizations[{auth_index}].artifact_types "
                    f"must contain 1..{MAX_ARTIFACT_TYPES_PER_AUTHORIZATION} entries"
                )
            artifact_types = tuple(
                _identifier(
                    value,
                    f"issuer_keys[{index}].authorizations[{auth_index}].artifact_types",
                )
                for value in raw_types
            )
            if artifact_types != tuple(sorted(set(artifact_types))):
                raise ValueError("authorized artifact_types must be sorted and unique")
            seen_roles.add(role)
            parsed_for_key.append((role, artifact_types))
        if [role for role, _ in parsed_for_key] != sorted(seen_roles):
            raise ValueError("role authorizations must be sorted by role")

        for role, artifact_types in parsed_for_key:
            authorizations.append((key_issuer, key_id, role, artifact_types))
        seen_pairs.add(pair)
        seen_bytes.add(public_bytes)
        trusted_keys.append(TrustedIssuerKey(
            issuer_id=key_issuer,
            key_id=key_id,
            public_key_bytes=public_bytes,
            valid_from_utc=valid_from,
            valid_until_utc=valid_until,
            revoked=item["revoked"],
        ))

    signature_doc = document["signature"]
    if type(signature_doc) is not dict or set(signature_doc) != {
        "algorithm", "signature_b64"
    }:
        raise ValueError("signature object fields mismatch")
    if signature_doc["algorithm"] != "ed25519":
        raise ValueError("trust-policy envelope supports Ed25519 only")
    signature = _b64(signature_doc["signature_b64"], "signature.signature_b64", 64)

    unsigned = dict(document)
    unsigned.pop("signature")
    try:
        Ed25519PublicKey.from_public_bytes(pinned_root_public_key_bytes).verify(
            signature, _canonical(unsigned)
        )
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("trust-policy root signature verification failed") from exc

    return VerifiedTrustPolicyV3(
        policy=TrustPolicy(policy_version=policy_version, issuer_keys=tuple(trusted_keys)),
        policy_domain=actual_domain,
        policy_sequence=sequence,
        root_key_id=root_key_id,
        envelope_sha256=hashlib.sha256(raw).hexdigest(),
        issued_at_utc=issued,
        expires_at_utc=expires,
        key_authorizations=tuple(authorizations),
    )
