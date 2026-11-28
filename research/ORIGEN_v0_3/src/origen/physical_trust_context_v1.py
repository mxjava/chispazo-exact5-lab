"""Provider-owned physical trust context; caller-supplied pins are forbidden.

The dataclass is a transport contract, not proof of institutional provisioning.
Only a separately administered deployment provider may construct and return it.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


MAX_NESTED_BUNDLE_TSA_ROOT_DER_BYTES = 1_048_576
_NESTED_BUNDLE_TSA_OID = re.compile(r"(?:0|1|2)(?:\.(?:0|[1-9][0-9]*)){1,30}\Z")


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
    nested_signature_bundle_tsa_root_certificate_der: bytes | None = None
    nested_signature_bundle_tsa_root_sha256: str | None = None
    nested_signature_bundle_tsa_policy_oid: str | None = None

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
        nested_tsa = (
            self.nested_signature_bundle_tsa_root_certificate_der,
            self.nested_signature_bundle_tsa_root_sha256,
            self.nested_signature_bundle_tsa_policy_oid,
        )
        if any(value is None for value in nested_tsa) and not all(
            value is None for value in nested_tsa
        ):
            raise ValueError(
                "nested-signature bundle TSA root DER, fingerprint and policy OID must be provisioned together"
            )
        if all(value is not None for value in nested_tsa):
            root_der, root_sha256, policy_oid = nested_tsa
            if (
                type(root_der) is not bytes
                or not root_der
                or len(root_der) > MAX_NESTED_BUNDLE_TSA_ROOT_DER_BYTES
            ):
                raise ValueError(
                    "nested-signature bundle TSA root must be non-empty exact immutable DER bytes within the size limit"
                )
            if (
                type(root_sha256) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", root_sha256)
                or hashlib.sha256(root_der).hexdigest() != root_sha256
            ):
                raise ValueError(
                    "nested-signature bundle TSA fingerprint does not bind the exact root DER bytes"
                )
            if (
                type(policy_oid) is not str
                or len(policy_oid) > 128
                or not _NESTED_BUNDLE_TSA_OID.fullmatch(policy_oid)
            ):
                raise ValueError(
                    "nested-signature bundle TSA policy OID must be canonical numeric dotted text"
                )
            arcs = policy_oid.split(".")
            if int(arcs[0]) > 2 or (int(arcs[0]) < 2 and int(arcs[1]) > 39):
                raise ValueError(
                    "nested-signature bundle TSA policy OID has invalid first arcs"
                )
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
    if context.nested_signature_bundle_tsa_root_certificate_der is not None:
        payload["nested_signature_bundle_tsa_root_sha256"] = (
            context.nested_signature_bundle_tsa_root_sha256
        )
        payload["nested_signature_bundle_tsa_policy_oid"] = (
            context.nested_signature_bundle_tsa_policy_oid
        )
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(canonical).hexdigest()

