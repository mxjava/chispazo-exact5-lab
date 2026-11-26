"""Provider-issued, single-use RFC 3161 nonce challenge contract.

This is a transport contract only. A real provider must issue unpredictable
nonces, retain the pending challenge in authoritative state, and consume both
nonces atomically with the deployment trust CAS. Synthetic instances belong
only in tests.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

_MAX_NONCE = (1 << 63) - 1
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class TimestampNonceChallengeV1:
    challenge_id: str
    policy_timestamp_nonce: int
    custody_timestamp_nonce: int
    state_generation: int
    root_generation: int
    physical_trust_context_generation: int
    physical_trust_context_sha256: str
    issued_at_utc: datetime
    expires_at_utc: datetime

    def __post_init__(self) -> None:
        if type(self.challenge_id) is not str or not _IDENTIFIER.fullmatch(self.challenge_id):
            raise ValueError("challenge_id must be a canonical identifier")
        for field in ("policy_timestamp_nonce", "custody_timestamp_nonce"):
            value = getattr(self, field)
            if type(value) is not int or not 1 <= value <= _MAX_NONCE:
                raise ValueError(f"{field} must be an exact positive signed 64-bit integer")
        if self.policy_timestamp_nonce == self.custody_timestamp_nonce:
            raise ValueError("policy and custody timestamp nonces must be distinct")
        for field, minimum in (
            ("state_generation", 0),
            ("root_generation", 1),
            ("physical_trust_context_generation", 1),
        ):
            value = getattr(self, field)
            if type(value) is not int or not minimum <= value <= _MAX_NONCE:
                raise ValueError(f"{field} must be an exact bounded integer")
        digest = self.physical_trust_context_sha256
        if type(digest) is not str or not _SHA256.fullmatch(digest):
            raise ValueError("physical_trust_context_sha256 must be lowercase SHA-256 hex")
        for field in ("issued_at_utc", "expires_at_utc"):
            value = getattr(self, field)
            if type(value) is not datetime or value.tzinfo is not timezone.utc:
                raise ValueError(f"{field} must be an exact normalized UTC datetime")
        if self.issued_at_utc >= self.expires_at_utc:
            raise ValueError("timestamp nonce challenge expiry must follow issuance")


def copy_timestamp_nonce_challenge(value: object) -> TimestampNonceChallengeV1:
    """Copy and revalidate provider data before consuming nonce values."""
    if type(value) is not TimestampNonceChallengeV1:
        raise TypeError("provider must return an exact TimestampNonceChallengeV1")
    return TimestampNonceChallengeV1(
        challenge_id=value.challenge_id,
        policy_timestamp_nonce=value.policy_timestamp_nonce,
        custody_timestamp_nonce=value.custody_timestamp_nonce,
        state_generation=value.state_generation,
        root_generation=value.root_generation,
        physical_trust_context_generation=value.physical_trust_context_generation,
        physical_trust_context_sha256=value.physical_trust_context_sha256,
        issued_at_utc=value.issued_at_utc,
        expires_at_utc=value.expires_at_utc,
    )


def timestamp_nonce_challenge_sha256(value: TimestampNonceChallengeV1) -> str:
    """Hash every challenge field in one canonical, domain-specific encoding."""
    challenge = copy_timestamp_nonce_challenge(value)
    payload = {
        "schema": "origen.timestamp-nonce-challenge.v1",
        "challenge_id": challenge.challenge_id,
        "policy_timestamp_nonce": challenge.policy_timestamp_nonce,
        "custody_timestamp_nonce": challenge.custody_timestamp_nonce,
        "state_generation": challenge.state_generation,
        "root_generation": challenge.root_generation,
        "physical_trust_context_generation": challenge.physical_trust_context_generation,
        "physical_trust_context_sha256": challenge.physical_trust_context_sha256,
        "issued_at_utc": challenge.issued_at_utc.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "expires_at_utc": challenge.expires_at_utc.isoformat(timespec="microseconds").replace("+00:00", "Z"),
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()
