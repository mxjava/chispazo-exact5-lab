"""Adversarial tests for exact evidence-byte snapshotting across verification and CAS."""

from __future__ import annotations

import hashlib
import unittest
from dataclasses import replace
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




class TestWitnessBatchSnapshotBinding(unittest.TestCase):
    def test_witness_statement_bytes_sent_to_cas_are_the_exact_bytes_verified(self):
        data, ledger, batches, _ = _build_case()
        provider = _provider_for(data, ledger)
        mutable_batches = list(batches)
        verified_statements = tuple(
            statement
            for batch in mutable_batches
            for statement in batch.raw_witness_statement_bytes
        )
        arguments = _arguments(data, ledger, batches)
        arguments["witness_observation_batches"] = mutable_batches
        original_verifier = composition.verify_custody_timestamp_ledger_witness_v1

        def verify_then_mutate(*args, **kwargs):
            verified = original_verifier(*args, **kwargs)
            # The lower-level verifier accepts a list and has already checked
            # the original batches. Replace one item before the outer CAS
            # envelope is assembled to simulate a caller-owned list race.
            mutable_batches[0] = replace(
                mutable_batches[0],
                raw_witness_statement_bytes=(b"mutated-after-verification",),
            )
            return verified

        with patch.object(
            composition,
            "verify_custody_timestamp_ledger_witness_v1",
            side_effect=verify_then_mutate,
        ):
            composition._inspect_custody_ledger_witness_with_deployment_provider_v1_using_provider(
                **arguments,
                provider=provider,
            )

        advance = provider.last_commit_arguments["external_evidence_advance"]
        self.assertEqual(advance.raw_witness_statement_bytes, verified_statements)


if __name__ == "__main__":
    unittest.main()
