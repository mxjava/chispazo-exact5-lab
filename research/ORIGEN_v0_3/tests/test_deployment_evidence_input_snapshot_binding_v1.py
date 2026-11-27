"""Adversarial tests for exact evidence-byte snapshotting across verification and CAS."""

from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from origen import deployment_evidence_composition_v1 as composition
from test_deployment_evidence_composition_v1 import (
    _arguments,
    _provider_for,
)
from test_custody_ledger_witness_integration_v1 import _build_case


class TestEvidenceInputSnapshotBinding(unittest.TestCase):
    def _run_with_post_verification_mutation(self, field: str):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        arguments = _arguments(data, ledger, batches)
        original_mapping = dict(arguments[field])
        original_verifier = composition.verify_custody_timestamp_ledger_witness_v1

        def verify_then_mutate(*args, **kwargs):
            verified = original_verifier(*args, **kwargs)
            # The lower-level verifier has returned after taking and verifying
            # its own mapping snapshot. Simulate a concurrent caller mutation
            # before the outer composition serializes the provider CAS envelope.
            target = data[field]
            old_digest = next(iter(target))
            replacement = (b"mutated-after-verification:" + field.encode("ascii"))
            del target[old_digest]
            target[hashlib.sha256(replacement).hexdigest()] = replacement
            return verified

        with patch.object(
            composition,
            "verify_custody_timestamp_ledger_witness_v1",
            side_effect=verify_then_mutate,
        ):
            result = composition._inspect_custody_ledger_witness_with_deployment_provider_v1_using_provider(
                **arguments,
                provider=provider,
            )

        advance = provider.last_commit_arguments["external_evidence_advance"]
        return result, original_mapping, dict(
            getattr(advance, "raw_artifact_bytes_by_sha256")
            if field == "artifact_bytes_by_sha256"
            else getattr(advance, "raw_signature_bytes_by_sha256")
        )

    def test_artifact_bytes_sent_to_cas_are_the_exact_bytes_verified(self):
        _, verified_mapping, cas_mapping = self._run_with_post_verification_mutation(
            "artifact_bytes_by_sha256"
        )
        self.assertEqual(cas_mapping, verified_mapping)

    def test_signature_bytes_sent_to_cas_are_the_exact_bytes_verified(self):
        _, verified_mapping, cas_mapping = self._run_with_post_verification_mutation(
            "signature_bytes_by_sha256"
        )
        self.assertEqual(cas_mapping, verified_mapping)




class TestWitnessBatchInputImmutability(unittest.TestCase):
    def test_mutable_witness_batch_list_is_rejected_before_provider_cas(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        arguments = _arguments(data, ledger, batches)
        arguments["witness_observation_batches"] = list(batches)

        with self.assertRaisesRegex(TypeError, "exact tuple"):
            composition._inspect_custody_ledger_witness_with_deployment_provider_v1_using_provider(
                **arguments,
                provider=provider,
            )

        self.assertEqual(provider.read_count, 1)
        self.assertEqual(provider.commit_count, 0)


    def test_cas_envelope_uses_same_witness_batch_bytes_verified_before_caller_mutation(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        expected_registry_bytes = tuple(batch.raw_registry_bytes for batch in batches)
        expected_witness_statements = tuple(
            statement
            for batch in batches
            for statement in batch.raw_witness_statement_bytes
        )
        self.assertGreaterEqual(len(batches), 2)
        arguments = _arguments(data, ledger, batches)
        original_verifier = composition.verify_custody_timestamp_ledger_witness_v1
        replacement_registry = b"caller-mutated-after-verification-registry"

        def verify_then_mutate_batches(*args, **kwargs):
            result = original_verifier(*args, **kwargs)
            for batch_index, batch in enumerate(batches):
                object.__setattr__(batch, "raw_registry_bytes", replacement_registry)
                object.__setattr__(
                    batch,
                    "raw_witness_statement_bytes",
                    tuple(
                        f"caller-mutated-witness-{batch_index}-{statement_index}".encode("ascii")
                        for statement_index, _ in enumerate(batch.raw_witness_statement_bytes)
                    ),
                )
            return result

        with patch.object(
            composition,
            "verify_custody_timestamp_ledger_witness_v1",
            side_effect=verify_then_mutate_batches,
        ):
            composition._inspect_custody_ledger_witness_with_deployment_provider_v1_using_provider(
                **arguments,
                provider=provider,
            )

        advance = provider.last_commit_arguments["external_evidence_advance"]
        self.assertTrue(all(batch.raw_registry_bytes == replacement_registry for batch in batches))
        self.assertNotEqual(
            tuple(statement for batch in batches for statement in batch.raw_witness_statement_bytes),
            expected_witness_statements,
        )
        self.assertEqual(advance.raw_registry_bytes, expected_registry_bytes[0])
        self.assertEqual(advance.raw_witness_statement_bytes, expected_witness_statements)

if __name__ == "__main__":
    unittest.main()
