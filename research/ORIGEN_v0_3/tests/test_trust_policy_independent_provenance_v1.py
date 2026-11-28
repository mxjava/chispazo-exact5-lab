"""Synthetic tests for policy-bound composition with the blocked provenance gate."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import test_trust_policy_receipt_chain_v1 as chain_fixtures
from origen.independent_trust_adapter import (
    ProvenanceStatus,
    verify_independent_provenance,
)
from origen.trust_policy_independent_provenance_v1 import (
    verify_policy_bound_independent_provenance,
)
from origen.trust_policy_receipt_chain_v1 import (
    verify_policy_bound_receipt_attestation,
)


class TestPolicyBoundIndependentProvenanceV1(unittest.TestCase):
    def setUp(self):
        self.receipt, _, issuer_public = chain_fixtures.signed_receipt()
        self.policy, _, self.root_public = chain_fixtures.signed_policy(issuer_public)
        self.now = chain_fixtures.NOW

    def verify(self, receipt=None, policy=None, **overrides):
        args = {
            "pinned_root_public_key_bytes": self.root_public,
            "expected_root_key_id": chain_fixtures.ROOT_KEY_ID,
            "minimum_policy_sequence": 7,
            "verification_time": self.now,
        }
        args.update(overrides)
        return verify_policy_bound_independent_provenance(
            self.receipt if receipt is None else receipt,
            self.policy if policy is None else policy,
            **args,
        )

    def test_valid_policy_and_receipt_chain_still_returns_blocked_provenance(self):
        events = []

        def chain(*args, **kwargs):
            result = verify_policy_bound_receipt_attestation(*args, **kwargs)
            events.append("policy-and-receipt-verified")
            return result

        def gate(raw):
            events.append("independent-gate-called")
            self.assertIs(raw, self.receipt)
            return verify_independent_provenance(raw)

        with (
            patch(
                "origen.trust_policy_independent_provenance_v1.verify_policy_bound_receipt_attestation",
                side_effect=chain,
            ),
            patch(
                "origen.trust_policy_independent_provenance_v1.verify_independent_provenance",
                side_effect=gate,
            ),
        ):
            result = self.verify()

        self.assertEqual(events, ["policy-and-receipt-verified", "independent-gate-called"])
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
        self.assertEqual(result.scope, "ROOT_ATTESTATION_VERIFIED_PROVENANCE_BLOCKED")
        self.assertEqual(result.policy_sequence, 7)
        self.assertEqual(result.root_key_id, chain_fixtures.ROOT_KEY_ID)
        self.assertEqual(result.receipt_issuer_id, "independent-verifier")
        self.assertEqual(result.receipt_key_id, "verifier-key-1")
        self.assertEqual(len(result.policy_envelope_sha256), 64)
        self.assertEqual(len(result.receipt_signed_payload_sha256), 64)

    def test_tampered_policy_never_reaches_independent_gate(self):
        document = json.loads(self.policy)
        document["issuer_id"] = "attacker-controlled"
        tampered = chain_fixtures.canonical(document)
        with patch(
            "origen.trust_policy_independent_provenance_v1.verify_independent_provenance",
            wraps=verify_independent_provenance,
        ) as gate:
            with self.assertRaisesRegex(ValueError, "root signature verification failed"):
                self.verify(policy=tampered)
        gate.assert_not_called()

    def test_tampered_receipt_never_reaches_independent_gate(self):
        document = json.loads(self.receipt)
        document["commitments"]["candidate_sha256"] = "f" * 64
        tampered = chain_fixtures.canonical(document)
        with patch(
            "origen.trust_policy_independent_provenance_v1.verify_independent_provenance",
            wraps=verify_independent_provenance,
        ) as gate:
            with self.assertRaisesRegex(ValueError, "signature verification failed"):
                self.verify(receipt=tampered)
        gate.assert_not_called()

    def test_wrong_root_never_reaches_independent_gate(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization

        attacker = Ed25519PrivateKey.generate()
        attacker_public = attacker.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        with patch(
            "origen.trust_policy_independent_provenance_v1.verify_independent_provenance",
            wraps=verify_independent_provenance,
        ) as gate:
            with self.assertRaisesRegex(ValueError, "root signature verification failed"):
                self.verify(pinned_root_public_key_bytes=attacker_public)
        gate.assert_not_called()

    def test_non_blocked_or_unexpected_gate_result_is_a_contract_failure(self):
        with patch(
            "origen.trust_policy_independent_provenance_v1.verify_independent_provenance",
            return_value="AUTHENTICATED",
        ):
            with self.assertRaisesRegex(RuntimeError, "violated its fail-closed contract"):
                self.verify()

    def test_gate_exception_is_not_swallowed_or_relabelled(self):
        with patch(
            "origen.trust_policy_independent_provenance_v1.verify_independent_provenance",
            side_effect=OSError("synthetic provider unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "provider unavailable"):
                self.verify()

    def test_preconstructed_verified_policy_is_not_accepted(self):
        from origen.trust_policy_envelope_v1 import verify_signed_trust_policy

        verified = verify_signed_trust_policy(
            self.policy,
            pinned_root_public_key_bytes=self.root_public,
            expected_root_key_id=chain_fixtures.ROOT_KEY_ID,
            minimum_policy_sequence=7,
            verification_time=self.now,
        )
        with self.assertRaisesRegex(ValueError, "exact bytes"):
            self.verify(policy=verified)

    def test_gate_has_no_authenticated_enum_member(self):
        self.assertEqual(
            list(ProvenanceStatus),
            [ProvenanceStatus.BLOCKED_PROVENANCE],
        )
        result = self.verify()
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)


if __name__ == "__main__":
    unittest.main()
