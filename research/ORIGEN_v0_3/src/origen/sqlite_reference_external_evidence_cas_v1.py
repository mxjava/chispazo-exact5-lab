"""Research-only SQLite reference CAS for external-evidence watermarks.

This is a durable local conformance primitive, NOT a DeploymentTrustProvider,
production backend, independent trust anchor, or rollback-resistant service.
Restoring an older database/WAL snapshot is outside its threat model.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from dataclasses import asdict, dataclass
from types import SimpleNamespace

from .deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    ExternalEvidenceAdvanceV1,
    ExternalEvidenceWatermarkV1,
    TrustStateRejected,
    _accepted_external_evidence_watermark_sha256,
    _external_evidence_watermark_copy,
    _validated_external_evidence_watermark,
)

_APPLICATION_ID = 0x4F524731  # ASCII "ORG1"
_SCHEMA_VERSION = 1
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}\Z")
_WATERMARK_FIELDS = {
    "policy_domain",
    "state_backend_id",
    "log_id",
    "log_key_id",
    "log_public_key_sha256",
    "ledger_tree_size",
    "ledger_root_sha256",
    "ledger_checkpoint_sha256",
    "registry_id",
    "registry_root_key_id",
    "registry_root_public_key_sha256",
    "registry_sequence",
    "registry_sha256",
}


class ReferenceCASUnavailable(RuntimeError):
    """The local reference database could not complete an operation."""


class ReferenceCASConflict(TrustStateRejected):
    """The expected generation or watermark no longer matches durable state."""


class ReferenceCASUnprovisioned(TrustStateRejected):
    """No explicit research genesis record exists."""


class ReferenceCASCorrupt(TrustStateRejected):
    """Persisted bytes, schema, identity, or digest failed validation."""


@dataclass(frozen=True, slots=True)
class ReferenceWatermarkSnapshot:
    policy_domain: str
    state_backend_id: str
    state_generation: int
    watermark: ExternalEvidenceWatermarkV1
    watermark_sha256: str
    genesis_record_sha256: str


@dataclass(frozen=True, slots=True)
class ReferenceWatermarkCommit:
    state_generation: int
    watermark_sha256: str
    outcome: str = "EVIDENCE_ADVANCED"


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _require_sha256(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_identifier(value: object, field: str) -> str:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field} must be a canonical identifier")
    return value


def _watermark_bytes(value: ExternalEvidenceWatermarkV1) -> bytes:
    copied = _external_evidence_watermark_copy(value)
    if copied is None:
        raise ValueError("a provisioned watermark cannot be empty")
    return _canonical_json(asdict(copied))


class SQLiteReferenceExternalEvidenceCASV1:
    """Local SQLite reference for durable, linearizable watermark transitions.

    The class deliberately does not implement DeploymentTrustProvider. Its
    methods are named separately so it cannot be passed accidentally to the
    full deployment composition. Genesis is a research fixture supplied by
    the caller; this class does not authenticate the genesis authority.
    """

    def __init__(
        self,
        database_path: str,
        *,
        state_backend_id: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        if type(database_path) is not str or not database_path:
            raise ValueError("database_path must be a non-empty exact string")
        if database_path == ":memory:" or database_path.startswith("file:"):
            raise ValueError("a durable filesystem database path is required")
        if type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds):
            raise ValueError("timeout_seconds must be a finite positive number")
        if not 0 < timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be in (0, 60]")
        _require_identifier(state_backend_id, "state_backend_id")
        absolute_path = os.path.abspath(database_path)
        if not os.path.isdir(os.path.dirname(absolute_path)):
            raise ValueError("database parent directory must already exist")
        if os.path.islink(absolute_path):
            raise ValueError("database path must not be a symbolic link")

        self.database_path = absolute_path
        self.state_backend_id = state_backend_id
        self.timeout_seconds = float(timeout_seconds)
        self._initialize_schema()

    def _connect(self, *, allow_non_wal: bool = False) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA trusted_schema=OFF")
            connection.execute(f"PRAGMA busy_timeout={int(self.timeout_seconds * 1000)}")
            connection.execute("PRAGMA synchronous=FULL")
            synchronous = connection.execute("PRAGMA synchronous").fetchone()[0]
            if type(synchronous) is not int or synchronous != 2:
                raise ReferenceCASUnavailable(
                    "SQLite connection did not retain synchronous=FULL"
                )
            if not allow_non_wal:
                journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
                if type(journal_mode) is not str or journal_mode.lower() != "wal":
                    raise ReferenceCASUnavailable(
                        "SQLite journal mode drifted from the required WAL mode"
                    )
            return connection
        except Exception:
            connection.close()
            raise

    def _initialize_schema(self) -> None:
        connection = self._connect(allow_non_wal=True)
        try:
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            application_id = connection.execute("PRAGMA application_id").fetchone()[0]
            user_version = connection.execute("PRAGMA user_version").fetchone()[0]
            if user_version == 0:
                existing_tables = connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if existing_tables:
                    raise ReferenceCASCorrupt(
                        "unversioned database already contains user tables"
                    )
                if application_id not in (0, _APPLICATION_ID):
                    raise ReferenceCASCorrupt("SQLite application_id belongs to another application")
                journal_mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if type(journal_mode) is not str or journal_mode.lower() != "wal":
                    raise ReferenceCASUnavailable("SQLite WAL mode could not be enabled")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    CREATE TABLE external_evidence_state (
                        singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                        schema_version INTEGER NOT NULL CHECK(schema_version = 1),
                        policy_domain TEXT NOT NULL,
                        state_backend_id TEXT NOT NULL,
                        state_generation INTEGER NOT NULL CHECK(state_generation >= 0),
                        watermark_json BLOB NOT NULL,
                        watermark_sha256 TEXT NOT NULL CHECK(length(watermark_sha256) = 64),
                        genesis_record_sha256 TEXT NOT NULL CHECK(length(genesis_record_sha256) = 64)
                    )
                    """
                )
                connection.execute(f"PRAGMA application_id={_APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
                connection.commit()
            elif user_version != _SCHEMA_VERSION or application_id != _APPLICATION_ID:
                raise ReferenceCASCorrupt("SQLite application or schema version is unsupported")
            else:
                if type(journal_mode) is not str or journal_mode.lower() != "wal":
                    raise ReferenceCASUnavailable(
                        "versioned SQLite database journal mode drifted from WAL"
                    )
                row = connection.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='external_evidence_state'"
                ).fetchone()
                if row is None:
                    raise ReferenceCASCorrupt("versioned database is missing its state table")
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def provision_genesis(
        self,
        watermark: ExternalEvidenceWatermarkV1,
        *,
        genesis_record_sha256: str,
    ) -> ReferenceWatermarkSnapshot:
        """Install one explicit research genesis; this does not authenticate it."""
        genesis_digest = _require_sha256(genesis_record_sha256, "genesis_record_sha256")
        copied = _external_evidence_watermark_copy(watermark)
        if copied is None:
            raise ValueError("genesis watermark is required")
        if (
            copied.policy_domain != CLASSIC_POLICY_DOMAIN
            or copied.state_backend_id != self.state_backend_id
        ):
            raise ValueError("genesis watermark does not match this fixed domain/backend")
        raw = _watermark_bytes(copied)
        digest = _accepted_external_evidence_watermark_sha256(copied)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT singleton FROM external_evidence_state WHERE singleton=1"
            ).fetchone()
            if existing is not None:
                raise ReferenceCASConflict("genesis is already provisioned and cannot be replaced")
            connection.execute(
                """
                INSERT INTO external_evidence_state (
                    singleton, schema_version, policy_domain, state_backend_id,
                    state_generation, watermark_json, watermark_sha256,
                    genesis_record_sha256
                ) VALUES (1, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    _SCHEMA_VERSION,
                    CLASSIC_POLICY_DOMAIN,
                    self.state_backend_id,
                    sqlite3.Binary(raw),
                    digest,
                    genesis_digest,
                ),
            )
            connection.commit()
        except Exception as exc:
            if connection.in_transaction:
                connection.rollback()
            if isinstance(exc, sqlite3.Error):
                raise ReferenceCASUnavailable("SQLite genesis transaction failed") from exc
            raise
        finally:
            connection.close()
        return self.read_watermark_snapshot()

    def _decode_row(self, row: sqlite3.Row) -> ReferenceWatermarkSnapshot:
        if (
            row["schema_version"] != _SCHEMA_VERSION
            or row["policy_domain"] != CLASSIC_POLICY_DOMAIN
            or row["state_backend_id"] != self.state_backend_id
        ):
            raise ReferenceCASCorrupt("persisted state identity or schema does not match")
        generation = row["state_generation"]
        if type(generation) is not int or not 0 <= generation <= 2**63 - 1:
            raise ReferenceCASCorrupt("persisted generation is outside the signed-64-bit range")
        raw = row["watermark_json"]
        if type(raw) is not bytes or not raw:
            raise ReferenceCASCorrupt("persisted watermark must be non-empty exact bytes")
        try:
            document = json.loads(
                raw.decode("ascii"),
                object_pairs_hook=_reject_duplicate_pairs,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ReferenceCASCorrupt("persisted watermark JSON is invalid") from exc
        if type(document) is not dict or set(document) != _WATERMARK_FIELDS:
            raise ReferenceCASCorrupt("persisted watermark fields do not match the exact schema")
        if _canonical_json(document) != raw:
            raise ReferenceCASCorrupt("persisted watermark JSON is not canonical")
        try:
            watermark = _external_evidence_watermark_copy(
                ExternalEvidenceWatermarkV1(**document)
            )
            stored_digest = _require_sha256(row["watermark_sha256"], "watermark_sha256")
            genesis_digest = _require_sha256(
                row["genesis_record_sha256"], "genesis_record_sha256"
            )
        except (TypeError, ValueError) as exc:
            raise ReferenceCASCorrupt("persisted watermark fields failed validation") from exc
        if watermark is None:
            raise ReferenceCASCorrupt("persisted watermark is empty")
        if (
            watermark.policy_domain != CLASSIC_POLICY_DOMAIN
            or watermark.state_backend_id != self.state_backend_id
        ):
            raise ReferenceCASCorrupt(
                "persisted watermark identity does not match its row and fixed domain/backend"
            )
        calculated = _accepted_external_evidence_watermark_sha256(watermark)
        if calculated != stored_digest:
            raise ReferenceCASCorrupt("persisted watermark digest does not match its exact bytes")
        return ReferenceWatermarkSnapshot(
            policy_domain=CLASSIC_POLICY_DOMAIN,
            state_backend_id=self.state_backend_id,
            state_generation=generation,
            watermark=watermark,
            watermark_sha256=stored_digest,
            genesis_record_sha256=genesis_digest,
        )

    def read_watermark_snapshot(self) -> ReferenceWatermarkSnapshot:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM external_evidence_state WHERE singleton=1"
            ).fetchone()
            if row is None:
                raise ReferenceCASUnprovisioned(
                    "external-evidence genesis has not been provisioned"
                )
            return self._decode_row(row)
        except sqlite3.Error as exc:
            raise ReferenceCASUnavailable("SQLite watermark read failed") from exc
        finally:
            connection.close()

    def compare_and_advance_watermark(
        self,
        *,
        expected_state_generation: int,
        expected_watermark_sha256: str,
        advance: ExternalEvidenceAdvanceV1,
    ) -> ReferenceWatermarkCommit:
        if (
            type(expected_state_generation) is not int
            or not 0 <= expected_state_generation <= 2**63 - 2
        ):
            raise ValueError("expected_state_generation is outside the permitted range")
        expected_digest = _require_sha256(
            expected_watermark_sha256, "expected_watermark_sha256"
        )
        if type(advance) is not ExternalEvidenceAdvanceV1:
            raise TypeError("advance must be an exact ExternalEvidenceAdvanceV1")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM external_evidence_state WHERE singleton=1"
            ).fetchone()
            if row is None:
                raise ReferenceCASUnprovisioned(
                    "external-evidence genesis has not been provisioned"
                )
            current = self._decode_row(row)
            if current.state_generation != expected_state_generation:
                raise ReferenceCASConflict("expected state generation is stale")
            if current.watermark_sha256 != expected_digest:
                raise ReferenceCASConflict("expected watermark digest is stale")

            next_watermark = _validated_external_evidence_watermark(
                SimpleNamespace(
                    policy_domain=current.policy_domain,
                    state_backend_id=current.state_backend_id,
                    accepted_external_evidence_watermark=current.watermark,
                ),
                expected_digest,
                advance,
            )
            if next_watermark is None:
                raise ReferenceCASCorrupt("validated evidence advance unexpectedly produced no watermark")
            next_digest = _accepted_external_evidence_watermark_sha256(next_watermark)
            next_raw = _watermark_bytes(next_watermark)
            next_generation = current.state_generation + 1
            cursor = connection.execute(
                """
                UPDATE external_evidence_state
                SET state_generation=?, watermark_json=?, watermark_sha256=?
                WHERE singleton=1 AND state_generation=? AND watermark_sha256=?
                """,
                (
                    next_generation,
                    sqlite3.Binary(next_raw),
                    next_digest,
                    expected_state_generation,
                    expected_digest,
                ),
            )
            if cursor.rowcount != 1:
                raise ReferenceCASConflict("conditional watermark update lost its compare-and-swap")
            connection.commit()
            return ReferenceWatermarkCommit(
                state_generation=next_generation,
                watermark_sha256=next_digest,
            )
        except Exception as exc:
            if connection.in_transaction:
                connection.rollback()
            if isinstance(exc, sqlite3.Error):
                raise ReferenceCASUnavailable("SQLite watermark transaction failed") from exc
            raise
        finally:
            connection.close()
