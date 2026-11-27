import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace

from origen.deployment_trust_provider_v1 import (
    CLASSIC_POLICY_DOMAIN,
    ExternalEvidenceAdvanceV1,
    ExternalEvidenceWatermarkV1,
    TrustStateRejected,
    _accepted_external_evidence_watermark_sha256,
)
from origen.sqlite_reference_external_evidence_cas_v1 import (
    ReferenceCASConflict,
    ReferenceCASCorrupt,
    ReferenceCASUnprovisioned,
    ReferenceCASUnavailable,
    SQLiteReferenceExternalEvidenceCASV1,
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _genesis(backend="synthetic-reference-cas"):
    checkpoint = b"synthetic-genesis-checkpoint"
    registry = b"synthetic-genesis-registry"
    return ExternalEvidenceWatermarkV1(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id=backend,
        log_id="synthetic-log",
        log_key_id="synthetic-log-key",
        log_public_key_sha256="1" * 64,
        ledger_tree_size=1,
        ledger_root_sha256="2" * 64,
        ledger_checkpoint_sha256=_sha(checkpoint),
        registry_id="synthetic-registry",
        registry_root_key_id="synthetic-registry-root",
        registry_root_public_key_sha256="3" * 64,
        registry_sequence=1,
        registry_sha256=_sha(registry),
    )


def _advance(watermark):
    old_checkpoint = b"synthetic-genesis-checkpoint"
    new_checkpoint = b"synthetic-next-checkpoint"
    registry = b"synthetic-registry-sequence-2"
    receipt = b"synthetic-receipt"
    policy = b"synthetic-policy-envelope"
    artifact = b"synthetic-artifact"
    signature = b"synthetic-artifact-signature"
    return ExternalEvidenceAdvanceV1(
        policy_domain=CLASSIC_POLICY_DOMAIN,
        state_backend_id=watermark.state_backend_id,
        log_id=watermark.log_id,
        log_key_id=watermark.log_key_id,
        log_public_key_sha256=watermark.log_public_key_sha256,
        old_tree_size=watermark.ledger_tree_size,
        old_root_sha256=watermark.ledger_root_sha256,
        old_checkpoint_sha256=watermark.ledger_checkpoint_sha256,
        new_tree_size=watermark.ledger_tree_size + 1,
        new_root_sha256="4" * 64,
        new_checkpoint_sha256=_sha(new_checkpoint),
        registry_id=watermark.registry_id,
        registry_root_key_id=watermark.registry_root_key_id,
        registry_root_public_key_sha256=watermark.registry_root_public_key_sha256,
        registry_sequence=watermark.registry_sequence + 1,
        registry_sha256=_sha(registry),
        raw_manifest_bytes=b"synthetic-manifest",
        raw_ledger_entry_bytes=b"synthetic-ledger-entry",
        raw_inclusion_proof_bytes=b"synthetic-inclusion-proof",
        raw_old_checkpoint_bytes=old_checkpoint,
        raw_new_checkpoint_bytes=new_checkpoint,
        raw_consistency_proof_bytes=b"synthetic-consistency-proof",
        raw_registry_bytes=registry,
        raw_witness_statement_bytes=(
            b"synthetic-witness-statement-1",
            b"synthetic-witness-statement-2",
        ),
        receipt_sha256=_sha(receipt),
        policy_envelope_sha256=_sha(policy),
        raw_receipt_bytes=receipt,
        raw_policy_envelope_bytes=policy,
        raw_custody_record_bytes=b"synthetic-custody-record",
        raw_portfolio_bytes=b"synthetic-portfolio",
        raw_custody_signature_bytes=b"synthetic-custody-signature",
        custodian_key_id="synthetic-custodian",
        raw_timestamp_token_der=b"synthetic-custody-timestamp-token",
        raw_policy_timestamp_token_der=b"synthetic-policy-timestamp-token",
        raw_artifact_bytes_by_sha256=((_sha(artifact), artifact),),
        raw_signature_bytes_by_sha256=((_sha(signature), signature),),
    )


class SQLiteReferenceExternalEvidenceCASTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tempdir.name, "reference-cas.sqlite3")
        self.backend = "synthetic-reference-cas"
        self.store = SQLiteReferenceExternalEvidenceCASV1(
            self.path, state_backend_id=self.backend
        )
        self.genesis = _genesis(self.backend)
        self.snapshot = self.store.provision_genesis(
            self.genesis, genesis_record_sha256="a" * 64
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_genesis_is_explicit_and_cannot_be_replaced(self):
        with self.assertRaises(ReferenceCASConflict):
            self.store.provision_genesis(
                self.genesis, genesis_record_sha256="b" * 64
            )
        self.assertEqual(self.store.read_watermark_snapshot(), self.snapshot)

    def test_state_and_digest_survive_close_and_reopen(self):
        advance = _advance(self.genesis)
        committed = self.store.compare_and_advance_watermark(
            expected_state_generation=self.snapshot.state_generation,
            expected_watermark_sha256=self.snapshot.watermark_sha256,
            advance=advance,
        )
        reopened = SQLiteReferenceExternalEvidenceCASV1(
            self.path, state_backend_id=self.backend
        )
        observed = reopened.read_watermark_snapshot()
        self.assertEqual(observed.state_generation, 1)
        self.assertEqual(observed.watermark_sha256, committed.watermark_sha256)
        self.assertEqual(observed.watermark.ledger_tree_size, 2)
        self.assertEqual(observed.watermark.registry_sequence, 2)

    def test_stale_generation_and_stale_digest_are_rejected(self):
        advance = _advance(self.genesis)
        self.store.compare_and_advance_watermark(
            expected_state_generation=0,
            expected_watermark_sha256=self.snapshot.watermark_sha256,
            advance=advance,
        )
        with self.assertRaises(ReferenceCASConflict):
            self.store.compare_and_advance_watermark(
                expected_state_generation=0,
                expected_watermark_sha256=self.snapshot.watermark_sha256,
                advance=advance,
            )
        current = self.store.read_watermark_snapshot()
        with self.assertRaises(ReferenceCASConflict):
            self.store.compare_and_advance_watermark(
                expected_state_generation=current.state_generation,
                expected_watermark_sha256="f" * 64,
                advance=advance,
            )

    def test_wrong_old_checkpoint_is_rejected_without_mutation(self):
        advance = _advance(self.genesis)
        wrong_old = b"not-the-accepted-checkpoint"
        bad = replace(
            advance,
            old_checkpoint_sha256=_sha(wrong_old),
            raw_old_checkpoint_bytes=wrong_old,
        )
        with self.assertRaises(TrustStateRejected):
            self.store.compare_and_advance_watermark(
                expected_state_generation=0,
                expected_watermark_sha256=self.snapshot.watermark_sha256,
                advance=bad,
            )
        self.assertEqual(self.store.read_watermark_snapshot(), self.snapshot)

    def test_sql_failure_rolls_back_generation_and_watermark(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                """
                CREATE TRIGGER reject_reference_update
                BEFORE UPDATE ON external_evidence_state
                BEGIN
                    SELECT RAISE(ABORT, 'injected transaction failure');
                END
                """
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(RuntimeError):
            self.store.compare_and_advance_watermark(
                expected_state_generation=0,
                expected_watermark_sha256=self.snapshot.watermark_sha256,
                advance=_advance(self.genesis),
            )
        self.assertEqual(self.store.read_watermark_snapshot(), self.snapshot)

    def test_concurrent_same_generation_has_exactly_one_winner(self):
        barrier = threading.Barrier(2)
        advance = _advance(self.genesis)

        def attempt():
            barrier.wait(timeout=5)
            try:
                return self.store.compare_and_advance_watermark(
                    expected_state_generation=0,
                    expected_watermark_sha256=self.snapshot.watermark_sha256,
                    advance=advance,
                )
            except ReferenceCASConflict:
                return "CONFLICT"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertEqual(sum(result != "CONFLICT" for result in results), 1)
        self.assertEqual(sum(result == "CONFLICT" for result in results), 1)
        self.assertEqual(self.store.read_watermark_snapshot().state_generation, 1)

    def test_tampered_persisted_bytes_fail_closed(self):
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "UPDATE external_evidence_state SET watermark_json=? WHERE singleton=1",
                (sqlite3.Binary(b'{"tampered":true}'),),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(ReferenceCASCorrupt):
            self.store.read_watermark_snapshot()

    def test_missing_genesis_fails_closed(self):
        path = os.path.join(self.tempdir.name, "unprovisioned.sqlite3")
        store = SQLiteReferenceExternalEvidenceCASV1(
            path, state_backend_id=self.backend
        )
        with self.assertRaises(ReferenceCASUnprovisioned):
            store.read_watermark_snapshot()

    def test_tampered_watermark_identity_fails_even_with_recomputed_digest(self):
        altered = replace(
            self.genesis,
            state_backend_id="different-reference-backend",
        )
        raw = json.dumps(
            asdict(altered),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        digest = _accepted_external_evidence_watermark_sha256(altered)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "UPDATE external_evidence_state "
                "SET watermark_json=?, watermark_sha256=? WHERE singleton=1",
                (sqlite3.Binary(raw), digest),
            )
            connection.commit()
        finally:
            connection.close()
        with self.assertRaises(ReferenceCASCorrupt):
            self.store.read_watermark_snapshot()


    def test_journal_mode_drift_fails_closed_after_initialization(self):
        connection = sqlite3.connect(self.path)
        try:
            mode = connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
            self.assertEqual(mode.lower(), "delete")
        finally:
            connection.close()

        with self.assertRaises(ReferenceCASUnavailable):
            self.store.read_watermark_snapshot()

        with self.assertRaises(ReferenceCASUnavailable):
            SQLiteReferenceExternalEvidenceCASV1(
                self.path, state_backend_id=self.backend
            )

    def _run_crash_subprocess(self, script, *arguments):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(
            part for part in (project_root, tests_dir, existing) if part
        )
        return subprocess.run(
            [sys.executable, "-c", script, *arguments],
            check=True,
            timeout=20,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_committed_advance_survives_immediate_process_exit(self):
        script = r"""
import os
import sys
from test_sqlite_reference_external_evidence_cas_v1 import _advance
from origen.sqlite_reference_external_evidence_cas_v1 import SQLiteReferenceExternalEvidenceCASV1

path, backend, generation, digest = sys.argv[1:]
store = SQLiteReferenceExternalEvidenceCASV1(path, state_backend_id=backend)
snapshot = store.read_watermark_snapshot()
if snapshot.state_generation != int(generation) or snapshot.watermark_sha256 != digest:
    raise SystemExit("unexpected pre-crash snapshot")
store.compare_and_advance_watermark(
    expected_state_generation=snapshot.state_generation,
    expected_watermark_sha256=snapshot.watermark_sha256,
    advance=_advance(snapshot.watermark),
)
os._exit(0)
"""
        self._run_crash_subprocess(
            script,
            self.path,
            self.backend,
            str(self.snapshot.state_generation),
            self.snapshot.watermark_sha256,
        )

        reopened = SQLiteReferenceExternalEvidenceCASV1(
            self.path, state_backend_id=self.backend
        )
        observed = reopened.read_watermark_snapshot()
        self.assertEqual(observed.state_generation, 1)
        self.assertEqual(observed.watermark.ledger_tree_size, 2)
        self.assertEqual(observed.watermark.registry_sequence, 2)

    def test_uncommitted_wal_update_is_rolled_back_after_process_exit(self):
        script = r"""
import os
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1], isolation_level=None)
connection.execute("PRAGMA synchronous=FULL")
mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
if type(mode) is not str or mode.lower() != "wal":
    raise SystemExit("database is not in WAL mode")
connection.execute("BEGIN IMMEDIATE")
connection.execute(
    "UPDATE external_evidence_state "
    "SET state_generation=999, watermark_json=?, watermark_sha256=? "
    "WHERE singleton=1",
    (sqlite3.Binary(b'{"uncommitted":true}'), "f" * 64),
)
os._exit(0)
"""
        self._run_crash_subprocess(script, self.path)

        reopened = SQLiteReferenceExternalEvidenceCASV1(
            self.path, state_backend_id=self.backend
        )
        observed = reopened.read_watermark_snapshot()
        self.assertEqual(observed, self.snapshot)

    def test_memory_database_is_rejected(self):
        with self.assertRaises(ValueError):
            SQLiteReferenceExternalEvidenceCASV1(
                ":memory:", state_backend_id=self.backend
            )


if __name__ == "__main__":
    unittest.main()
