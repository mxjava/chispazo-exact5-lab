"""Strict V1 parser for untrusted ORIGEN trust-receipt documents.

Receipt bytes use the repository canonical JSON profile: UTF-8, sorted object keys,
no insignificant whitespace, and ASCII escapes. Parsing validates shape and
internal consistency only; it does not verify signatures,
keys, identities, trusted time, ledger inclusion, or physical provenance. In
particular, a declared status of AUTHENTICATED is untrusted input and MUST NOT be
used as an eligibility decision.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

MAX_TRUST_RECEIPT_BYTES = 262_144
MAX_TRUST_RECEIPT_JSON_DEPTH = 64
# Receipt integer claims are bounded to the portable signed 64-bit range.
MAX_TRUST_RECEIPT_INTEGER = (1 << 63) - 1
SCHEMA_VERSION = "origen.trust-receipt.v1"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_CONTEST_ID = re.compile(r"[1-9][0-9]{0,11}\Z")
_UTC_TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?Z\Z"
)
_SIGNATURE_ALGORITHMS = {"ed25519", "ecdsa-p256-sha256", "rsa-pss-sha256"}
_CHISPAZO_LOCAL_TIMEZONE = ZoneInfo("America/Mexico_City")
_CLASSIC_DRAW_SLOT = (21, 0, 0, 0)

_ROOT_FIELDS = {
    "schema_version", "status", "policy_version", "verifier_build_sha256",
    "artifacts", "signers", "custodians", "trusted_time_proofs",
    "ledger_anchor", "target", "commitments", "output_seals",
    "failure_codes", "receipt_attestation",
}


@dataclass(frozen=True, slots=True)
class ArtifactDigest:
    artifact_type: str
    sha256: str
    byte_length: int
    contest_id: str


@dataclass(frozen=True, slots=True)
class SignerClaim:
    subject_id: str
    role: str
    key_id: str
    algorithm: str
    signature_sha256: str


@dataclass(frozen=True, slots=True)
class CustodianClaim:
    subject_id: str
    role: str
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class TrustedTimeProofClaim:
    authority_id: str
    event_id: str
    event_at_utc: str
    proof_sha256: str


@dataclass(frozen=True, slots=True)
class LedgerAnchorClaim:
    ledger_id: str
    entry_id: str
    previous_head_sha256: str
    head_sha256: str
    inclusion_proof_sha256: str


@dataclass(frozen=True, slots=True)
class TargetClaim:
    modality: str
    contest_id: str
    draw_close_at_utc: str
    target_list_sha256: str


@dataclass(frozen=True, slots=True)
class RunCommitments:
    preregistration_sha256: str
    candidate_sha256: str
    code_sha256: str
    environment_sha256: str


@dataclass(frozen=True, slots=True)
class OutputSealClaim:
    target_contest_id: str
    generator_id: str
    created_at_utc: str
    portfolio_sha256: str
    seal_sha256: str
    signature_sha256: str


@dataclass(frozen=True, slots=True)
class ReceiptAttestationClaim:
    issuer_id: str
    key_id: str
    algorithm: str
    signature_b64: str
    signed_at_utc: str
    timestamp_proof_sha256: str


@dataclass(frozen=True, slots=True)
class UnverifiedTrustReceipt:
    """Parsed untrusted claims; never an authenticated verification receipt."""

    declared_status: str
    policy_version: str
    verifier_build_sha256: str
    artifacts: tuple[ArtifactDigest, ...]
    signers: tuple[SignerClaim, ...]
    custodians: tuple[CustodianClaim, ...]
    trusted_time_proofs: tuple[TrustedTimeProofClaim, ...]
    ledger_anchor: LedgerAnchorClaim
    target: TargetClaim
    commitments: RunCommitments
    output_seals: tuple[OutputSealClaim, ...]
    failure_codes: tuple[str, ...]
    attestation: ReceiptAttestationClaim
    raw_sha256: str


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not accepted: {value}")


def _reject_json_float(value: str) -> None:
    raise ValueError("floating-point JSON numbers are not accepted in trust receipts")


def _validate_json_nesting_depth(raw: bytes) -> None:
    """Reject excessive JSON container nesting before invoking recursive codecs.

    This byte-level scan ignores brackets inside quoted strings and escaped
    quotes/backslashes. JSON grammar and delimiter matching remain the decoder's
    responsibility; this function only enforces a conservative resource bound.
    """
    depth = 0
    in_string = False
    escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:  # backslash
                escaped = True
            elif byte == 0x22:  # quote
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):  # { [
            depth += 1
            if depth > MAX_TRUST_RECEIPT_JSON_DEPTH:
                raise ValueError(
                    "trust receipt exceeds maximum JSON nesting depth "
                    f"{MAX_TRUST_RECEIPT_JSON_DEPTH}"
                )
        elif byte in (0x7D, 0x5D) and depth:  # } ]
            depth -= 1


def _parse_json_integer(value: str) -> int:
    """Parse only portable signed-64-bit JSON integers at the decode boundary."""
    negative = value.startswith("-")
    digits = value[1:] if negative else value
    limit = "9223372036854775808" if negative else "9223372036854775807"
    if len(digits) > len(limit) or (len(digits) == len(limit) and digits > limit):
        raise ValueError("JSON integer exceeds signed 64-bit range")
    return int(value)


def _object(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be a JSON object")
    actual = set(value)
    if actual != fields:
        missing = sorted(fields - actual)
        extra = sorted(actual - fields)
        raise ValueError(f"{label} fields mismatch; missing={missing}, unexpected={extra}")
    return value


def _array(value: object, label: str, *, minimum: int, maximum: int) -> list[object]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} must be an array with {minimum}..{maximum} entries")
    return value


def _identifier(value: object, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical non-empty identifier")
    return value


def _digest(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be 64 lowercase hexadecimal characters")
    return value


def _positive_integer(value: object, field: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} must be a positive integer")
    return value


def _contest_id(value: object, field: str) -> str:
    if type(value) is not str or not _CONTEST_ID.fullmatch(value):
        raise ValueError(f"{field} must be a canonical positive decimal contest ID")
    return value


def _timestamp(value: object, field: str) -> str:
    if type(value) is not str or not _UTC_TIMESTAMP.fullmatch(value):
        raise ValueError(f"{field} must be a canonical UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} is not a valid calendar timestamp") from exc
    return value


def _is_classic_draw_slot(value: str) -> bool:
    """Match the official 21:00 Chispazo Clásico slot in Mexico City time."""
    instant = datetime.fromisoformat(value[:-1] + "+00:00")
    local = instant.astimezone(_CHISPAZO_LOCAL_TIMEZONE)
    return (local.hour, local.minute, local.second, local.microsecond) == _CLASSIC_DRAW_SLOT


def _algorithm(value: object, field: str) -> str:
    if type(value) is not str or value not in _SIGNATURE_ALGORITHMS:
        raise ValueError(f"{field} is not a supported receipt-schema algorithm")
    return value


def _target_list_digest(contest_id: str) -> str:
    encoded = json.dumps([contest_id], separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _parse_artifact(value: object, index: int, target_id: str) -> ArtifactDigest:
    item = _object(
        value, {"artifact_type", "sha256", "byte_length", "contest_id"},
        f"artifacts[{index}]",
    )
    contest_id = _contest_id(item["contest_id"], f"artifacts[{index}].contest_id")
    if contest_id != target_id:
        raise ValueError("every artifact must bind to the receipt target contest")
    return ArtifactDigest(
        artifact_type=_identifier(item["artifact_type"], f"artifacts[{index}].artifact_type"),
        sha256=_digest(item["sha256"], f"artifacts[{index}].sha256"),
        byte_length=_positive_integer(item["byte_length"], f"artifacts[{index}].byte_length"),
        contest_id=contest_id,
    )


def _parse_signer(value: object, index: int) -> SignerClaim:
    item = _object(
        value, {"subject_id", "role", "key_id", "algorithm", "signature_sha256"},
        f"signers[{index}]",
    )
    return SignerClaim(
        subject_id=_identifier(item["subject_id"], f"signers[{index}].subject_id"),
        role=_identifier(item["role"], f"signers[{index}].role"),
        key_id=_identifier(item["key_id"], f"signers[{index}].key_id"),
        algorithm=_algorithm(item["algorithm"], f"signers[{index}].algorithm"),
        signature_sha256=_digest(item["signature_sha256"], f"signers[{index}].signature_sha256"),
    )


def _parse_custodian(value: object, index: int) -> CustodianClaim:
    item = _object(
        value, {"subject_id", "role", "receipt_sha256"},
        f"custodians[{index}]",
    )
    return CustodianClaim(
        subject_id=_identifier(item["subject_id"], f"custodians[{index}].subject_id"),
        role=_identifier(item["role"], f"custodians[{index}].role"),
        receipt_sha256=_digest(item["receipt_sha256"], f"custodians[{index}].receipt_sha256"),
    )


def _parse_time_proof(value: object, index: int) -> TrustedTimeProofClaim:
    item = _object(
        value, {"authority_id", "event_id", "event_at_utc", "proof_sha256"},
        f"trusted_time_proofs[{index}]",
    )
    return TrustedTimeProofClaim(
        authority_id=_identifier(item["authority_id"], f"trusted_time_proofs[{index}].authority_id"),
        event_id=_identifier(item["event_id"], f"trusted_time_proofs[{index}].event_id"),
        event_at_utc=_timestamp(item["event_at_utc"], f"trusted_time_proofs[{index}].event_at_utc"),
        proof_sha256=_digest(item["proof_sha256"], f"trusted_time_proofs[{index}].proof_sha256"),
    )


def _parse_ledger(value: object) -> LedgerAnchorClaim:
    item = _object(
        value,
        {"ledger_id", "entry_id", "previous_head_sha256", "head_sha256", "inclusion_proof_sha256"},
        "ledger_anchor",
    )
    previous_head = _digest(
        item["previous_head_sha256"], "ledger_anchor.previous_head_sha256"
    )
    head = _digest(item["head_sha256"], "ledger_anchor.head_sha256")
    if head == previous_head:
        raise ValueError("ledger head must advance beyond the previous head")
    return LedgerAnchorClaim(
        ledger_id=_identifier(item["ledger_id"], "ledger_anchor.ledger_id"),
        entry_id=_identifier(item["entry_id"], "ledger_anchor.entry_id"),
        previous_head_sha256=previous_head,
        head_sha256=head,
        inclusion_proof_sha256=_digest(item["inclusion_proof_sha256"], "ledger_anchor.inclusion_proof_sha256"),
    )


def _parse_target(value: object) -> TargetClaim:
    item = _object(
        value, {"modality", "contest_id", "draw_close_at_utc", "target_list_sha256"},
        "target",
    )
    modality = item["modality"]
    if type(modality) is not str or modality != "CLASSIC":
        raise ValueError("V1 trust receipts are restricted to CLASSIC targets")
    contest_id = _contest_id(item["contest_id"], "target.contest_id")
    target_digest = _digest(item["target_list_sha256"], "target.target_list_sha256")
    if target_digest != _target_list_digest(contest_id):
        raise ValueError("target_list_sha256 does not match the canonical one-contest target list")
    draw_close_at_utc = _timestamp(
        item["draw_close_at_utc"], "target.draw_close_at_utc"
    )
    if not _is_classic_draw_slot(draw_close_at_utc):
        raise ValueError(
            "CLASSIC draw_close_at_utc must resolve to the official 21:00 "
            "America/Mexico_City slot"
        )
    return TargetClaim(
        modality=modality,
        contest_id=contest_id,
        draw_close_at_utc=draw_close_at_utc,
        target_list_sha256=target_digest,
    )


def _parse_commitments(value: object) -> RunCommitments:
    item = _object(
        value,
        {"preregistration_sha256", "candidate_sha256", "code_sha256", "environment_sha256"},
        "commitments",
    )
    return RunCommitments(
        preregistration_sha256=_digest(item["preregistration_sha256"], "commitments.preregistration_sha256"),
        candidate_sha256=_digest(item["candidate_sha256"], "commitments.candidate_sha256"),
        code_sha256=_digest(item["code_sha256"], "commitments.code_sha256"),
        environment_sha256=_digest(item["environment_sha256"], "commitments.environment_sha256"),
    )


def _parse_output_seal(value: object, index: int, target_id: str, close_at: str) -> OutputSealClaim:
    item = _object(
        value,
        {"target_contest_id", "generator_id", "created_at_utc", "portfolio_sha256", "seal_sha256", "signature_sha256"},
        f"output_seals[{index}]",
    )
    contest_id = _contest_id(item["target_contest_id"], f"output_seals[{index}].target_contest_id")
    if contest_id != target_id:
        raise ValueError("both output seals must bind to the receipt target contest")
    created = _timestamp(item["created_at_utc"], f"output_seals[{index}].created_at_utc")
    close = datetime.fromisoformat(close_at[:-1] + "+00:00")
    created_dt = datetime.fromisoformat(created[:-1] + "+00:00")
    if created_dt >= close:
        raise ValueError("output seal must be created strictly before the declared draw close")
    return OutputSealClaim(
        target_contest_id=contest_id,
        generator_id=_identifier(item["generator_id"], f"output_seals[{index}].generator_id"),
        created_at_utc=created,
        portfolio_sha256=_digest(item["portfolio_sha256"], f"output_seals[{index}].portfolio_sha256"),
        seal_sha256=_digest(item["seal_sha256"], f"output_seals[{index}].seal_sha256"),
        signature_sha256=_digest(item["signature_sha256"], f"output_seals[{index}].signature_sha256"),
    )


def _parse_attestation(value: object) -> ReceiptAttestationClaim:
    item = _object(
        value,
        {"issuer_id", "key_id", "algorithm", "signature_b64", "signed_at_utc", "timestamp_proof_sha256"},
        "receipt_attestation",
    )
    algorithm = _algorithm(item["algorithm"], "receipt_attestation.algorithm")
    signature_b64 = item["signature_b64"]
    if type(signature_b64) is not str or not signature_b64:
        raise ValueError("receipt_attestation.signature_b64 must be non-empty canonical base64")
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("receipt_attestation.signature_b64 is invalid base64") from exc
    if base64.b64encode(signature).decode("ascii") != signature_b64:
        raise ValueError("receipt_attestation.signature_b64 is not canonical base64")
    if algorithm == "ed25519" and len(signature) != 64:
        raise ValueError("Ed25519 receipt attestation must contain exactly 64 signature bytes")
    return ReceiptAttestationClaim(
        issuer_id=_identifier(item["issuer_id"], "receipt_attestation.issuer_id"),
        key_id=_identifier(item["key_id"], "receipt_attestation.key_id"),
        algorithm=algorithm,
        signature_b64=signature_b64,
        signed_at_utc=_timestamp(item["signed_at_utc"], "receipt_attestation.signed_at_utc"),
        timestamp_proof_sha256=_digest(item["timestamp_proof_sha256"], "receipt_attestation.timestamp_proof_sha256"),
    )


def parse_unverified_receipt(raw: bytes) -> UnverifiedTrustReceipt:
    """Parse a bounded receipt document without authenticating any of its claims."""
    if type(raw) is not bytes:
        raise TypeError("trust receipt input must be exact bytes")
    if not raw or len(raw) > MAX_TRUST_RECEIPT_BYTES:
        raise ValueError(f"trust receipt must contain 1..{MAX_TRUST_RECEIPT_BYTES} bytes")
    _validate_json_nesting_depth(raw)
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("trust receipt must be valid UTF-8") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_float,
            parse_int=_parse_json_integer,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("trust receipt is not valid bounded JSON") from exc
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    if raw != canonical:
        raise ValueError("trust receipt JSON must use canonical UTF-8 encoding")
    root = _object(payload, _ROOT_FIELDS, "receipt")
    if root["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported trust receipt schema_version")
    status = root["status"]
    if type(status) is not str or status not in {"AUTHENTICATED", "REJECTED"}:
        raise ValueError("status must be AUTHENTICATED or REJECTED")
    policy_version = _identifier(root["policy_version"], "policy_version")
    verifier_digest = _digest(root["verifier_build_sha256"], "verifier_build_sha256")
    target = _parse_target(root["target"])
    artifacts = tuple(
        _parse_artifact(item, index, target.contest_id)
        for index, item in enumerate(_array(root["artifacts"], "artifacts", minimum=1, maximum=4096))
    )
    artifact_keys = [(item.artifact_type, item.sha256) for item in artifacts]
    if len(set(artifact_keys)) != len(artifact_keys):
        raise ValueError("artifacts contain duplicate type/digest pairs")
    signers = tuple(
        _parse_signer(item, index)
        for index, item in enumerate(_array(root["signers"], "signers", minimum=1, maximum=64))
    )
    if len({item.key_id for item in signers}) != len(signers):
        raise ValueError("signers contain duplicate key IDs")
    if len({item.subject_id for item in signers}) != len(signers):
        raise ValueError("signers contain duplicate subject IDs")
    if len({item.signature_sha256 for item in signers}) != len(signers):
        raise ValueError("signers contain duplicate signature digests")
    custodians = tuple(
        _parse_custodian(item, index)
        for index, item in enumerate(_array(root["custodians"], "custodians", minimum=1, maximum=64))
    )
    if len({item.subject_id for item in custodians}) != len(custodians):
        raise ValueError("custodians contain duplicate subject IDs")
    signer_subjects = {item.subject_id for item in signers}
    custodian_subjects = {item.subject_id for item in custodians}
    if signer_subjects.intersection(custodian_subjects):
        raise ValueError("signer and custodian claims must be separate")
    time_proofs = tuple(
        _parse_time_proof(item, index)
        for index, item in enumerate(_array(root["trusted_time_proofs"], "trusted_time_proofs", minimum=1, maximum=4096))
    )
    if len({item.proof_sha256 for item in time_proofs}) != len(time_proofs):
        raise ValueError("trusted_time_proofs contain duplicate proof digests")
    # A time authority/event pair is a unique event identity. Accepting two
    # different timestamps or proofs for the same identity makes downstream
    # selection ambiguous even when each proof digest is individually unique.
    time_event_keys = [(item.authority_id, item.event_id) for item in time_proofs]
    if len(set(time_event_keys)) != len(time_event_keys):
        raise ValueError(
            "trusted_time_proofs contain duplicate authority/event identities"
        )
    ledger = _parse_ledger(root["ledger_anchor"])
    commitments = _parse_commitments(root["commitments"])
    seals = tuple(
        _parse_output_seal(item, index, target.contest_id, target.draw_close_at_utc)
        for index, item in enumerate(_array(root["output_seals"], "output_seals", minimum=2, maximum=2))
    )
    if len({item.generator_id for item in seals}) != 2:
        raise ValueError("two output seals must name distinct generators")
    if len({item.portfolio_sha256 for item in seals}) != 2:
        raise ValueError("two output seals must bind distinct portfolio bytes")
    if len({item.seal_sha256 for item in seals}) != 2:
        raise ValueError("two output seals must have distinct seal digests")
    if len({item.signature_sha256 for item in seals}) != 2:
        raise ValueError("two output seals must have distinct signature digests")
    signer_signature_digests = {item.signature_sha256 for item in signers}
    if not {item.signature_sha256 for item in seals}.issubset(signer_signature_digests):
        raise ValueError(
            "every output seal signature must reference a declared signer signature digest"
        )
    generator_ids = {item.generator_id for item in seals}
    if generator_ids.intersection(signer_subjects):
        raise ValueError("signer and generator claims must be separate")
    if generator_ids.intersection(item.subject_id for item in custodians):
        raise ValueError("generator and custodian claims must be separate")
    failure_values = _array(root["failure_codes"], "failure_codes", minimum=0, maximum=256)
    failures = tuple(_identifier(item, f"failure_codes[{index}]") for index, item in enumerate(failure_values))
    if len(set(failures)) != len(failures):
        raise ValueError("failure_codes must be unique")
    if status == "AUTHENTICATED" and failures:
        raise ValueError("AUTHENTICATED declaration cannot contain failure codes")
    if status == "REJECTED" and not failures:
        raise ValueError("REJECTED declaration must contain at least one failure code")
    attestation = _parse_attestation(root["receipt_attestation"])
    attestation_time_proof = next(
        (
            item for item in time_proofs
            if item.proof_sha256 == attestation.timestamp_proof_sha256
        ),
        None,
    )
    if attestation_time_proof is None:
        raise ValueError(
            "receipt attestation timestamp proof must reference a declared trusted time proof"
        )
    if attestation_time_proof.event_at_utc != attestation.signed_at_utc:
        raise ValueError(
            "receipt attestation signed_at_utc must match its referenced trusted time proof"
        )
    declared_participants = signer_subjects | custodian_subjects | generator_ids
    if attestation.issuer_id in declared_participants:
        raise ValueError(
            "receipt attestation issuer must be separate from signers, custodians, and generators"
        )
    signer_key_ids = {item.key_id for item in signers}
    if attestation.key_id in signer_key_ids:
        raise ValueError(
            "receipt attestation key must be separate from signer keys"
        )
    time_authority_ids = {item.authority_id for item in time_proofs}
    if time_authority_ids.intersection(declared_participants | {attestation.issuer_id}):
        raise ValueError(
            "trusted time authority IDs must be distinct from receipt issuer and all declared participants"
        )
    # The ledger is an independent trust domain, not another label for one of
    # the actors whose claims it is meant to anchor. This is structural
    # anti-aliasing only; it does not authenticate the ledger or its operator.
    if ledger.ledger_id in declared_participants | time_authority_ids | {attestation.issuer_id}:
        raise ValueError(
            "ledger ID must be distinct from receipt issuer, signers, custodians, "
            "generators, and trusted time authorities"
        )
    return UnverifiedTrustReceipt(
        declared_status=status,
        policy_version=policy_version,
        verifier_build_sha256=verifier_digest,
        artifacts=artifacts,
        signers=signers,
        custodians=custodians,
        trusted_time_proofs=time_proofs,
        ledger_anchor=ledger,
        target=target,
        commitments=commitments,
        output_seals=seals,
        failure_codes=failures,
        attestation=attestation,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
    )
