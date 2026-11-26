"""Provider-owned physical trust context; caller-supplied pins are forbidden.

The dataclass is a transport contract, not proof of institutional provisioning.
Only a separately administered deployment provider may construct and return it.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhysicalTrustContextV1:
    """Trust anchors and floors for TSA, policy, transparency log and registry."""

    policy_tsa_root_certificate_der: bytes
    policy_tsa_root_sha256: str
    policy_tsa_policy_oid: str
    policy_root_public_key_bytes: bytes
    policy_root_key_id: str
    minimum_policy_sequence: int
    custody_tsa_root_certificate_der: bytes
    custody_tsa_root_sha256: str
    log_public_key_bytes: bytes
    log_id: str
    log_key_id: str
    registry_root_public_key_bytes: bytes
    registry_root_key_id: str
    registry_id: str
    minimum_registry_sequence: int
    minimum_log_tree_size: int = 0
    context_generation: int = 0

    def __post_init__(self) -> None:
        byte_fields = (
            "policy_tsa_root_certificate_der",
            "policy_root_public_key_bytes",
            "custody_tsa_root_certificate_der",
            "log_public_key_bytes",
            "registry_root_public_key_bytes",
        )
        for field in byte_fields:
            value = getattr(self, field)
            if type(value) is not bytes or not value:
                raise ValueError(f"{field} must be non-empty immutable bytes")
        if len(self.policy_root_public_key_bytes) != 32:
            raise ValueError("policy_root_public_key_bytes must be a 32-byte Ed25519 key")
        if len(self.log_public_key_bytes) != 32:
            raise ValueError("log_public_key_bytes must be a 32-byte Ed25519 key")
        if len(self.registry_root_public_key_bytes) != 32:
            raise ValueError("registry_root_public_key_bytes must be a 32-byte Ed25519 key")
        for field, data_field in (
            ("policy_tsa_root_sha256", "policy_tsa_root_certificate_der"),
            ("custody_tsa_root_sha256", "custody_tsa_root_certificate_der"),
        ):
            digest = getattr(self, field)
            if type(digest) is not str or len(digest) != 64:
                raise ValueError(f"{field} must be a lowercase SHA-256 digest")
            if any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError(f"{field} must be a lowercase SHA-256 digest")
            if hashlib.sha256(getattr(self, data_field)).hexdigest() != digest:
                raise ValueError(f"{field} does not bind the exact certificate bytes")
        for field in (
            "policy_tsa_policy_oid",
            "policy_root_key_id",
            "log_id",
            "log_key_id",
            "registry_root_key_id",
            "registry_id",
        ):
            value = getattr(self, field)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{field} must be a non-empty identifier")
        for field in (
            "minimum_policy_sequence",
            "minimum_registry_sequence",
            "minimum_log_tree_size",
            "context_generation",
        ):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field} must be a non-negative integer")

def physical_trust_context_sha256(context: PhysicalTrustContextV1) -> str:
    """Hash every physical trust pin and floor, including its monotonic generation."""
    if type(context) is not PhysicalTrustContextV1:
        raise TypeError("physical trust context must be an exact PhysicalTrustContextV1")
    payload = {
        "schema": "origen.physical-trust-context.v1",
        "context_generation": context.context_generation,
        "policy_tsa_root_sha256": context.policy_tsa_root_sha256,
        "policy_tsa_policy_oid": context.policy_tsa_policy_oid,
        "policy_root_public_key_sha256": hashlib.sha256(
            context.policy_root_public_key_bytes
        ).hexdigest(),
        "policy_root_key_id": context.policy_root_key_id,
        "minimum_policy_sequence": context.minimum_policy_sequence,
        "custody_tsa_root_sha256": context.custody_tsa_root_sha256,
        "log_public_key_sha256": hashlib.sha256(
            context.log_public_key_bytes
        ).hexdigest(),
        "log_id": context.log_id,
        "log_key_id": context.log_key_id,
        "minimum_log_tree_size": context.minimum_log_tree_size,
        "registry_root_public_key_sha256": hashlib.sha256(
            context.registry_root_public_key_bytes
        ).hexdigest(),
        "registry_root_key_id": context.registry_root_key_id,
        "registry_id": context.registry_id,
        "minimum_registry_sequence": context.minimum_registry_sequence,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()

