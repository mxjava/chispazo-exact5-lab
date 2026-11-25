"""Regression tests for V1 receipt modality to V2 policy-domain binding.

All signing keys and receipts are synthetic. These tests do not provision
institutional trust anchors or establish physical provenance.
"""
from __future__ import annotations

import unittest

from test_trust_policy_envelope_v2 import (
    NOW,
    POLICY_DOMAIN,
    ROOT_KEY_ID,
    fixture,
)
from origen.trust_policy_integration_v2 import (
    CLASSIC_RECEIPT_POLICY_DOMAIN_V1,
    inspect_signed_root_attestation_chain_v2,
)


DE_LAS_TRES_DOMAIN = "origen.chispazo.de-lastres.provenance"


class TestV2ReceiptModalityDomainBinding(unittest.TestCase):
    def inspect(self, receipt, policy, root, domain):
        return inspect_signed_root_attestation_chain_v2(
            receipt,
            policy,
            pinned_root_public_key_bytes=root,
            expected_root_key_id=ROOT_KEY_ID,
            expected_policy_domain=domain,
            minimum_policy_sequence=7,
            verification_time=NOW,
        )

    def test_classic_receipt_requires_classic_policy_domain(self):
        receipt, policy, root, _ = fixture(domain=POLICY_DOMAIN)
        result = self.inspect(receipt, policy, root, POLICY_DOMAIN)
        self.assertEqual(result.policy_domain, CLASSIC_RECEIPT_POLICY_DOMAIN_V1)
        self.assertEqual(result.provenance_status.value, "BLOCKED_PROVENANCE")

    def test_classic_receipt_cannot_be_verified_under_signed_de_las_tres_domain(self):
        # The envelope is validly signed for De las Tres and the caller's
        # expected domain agrees. The receipt fixture remains CLASSIC. The
        # composition must reject this cross-modality namespace mismatch.
        receipt, policy, root, _ = fixture(domain=DE_LAS_TRES_DOMAIN)
        with self.assertRaisesRegex(
            ValueError,
            "V1 trust receipt modality CLASSIC requires policy domain",
        ):
            self.inspect(receipt, policy, root, DE_LAS_TRES_DOMAIN)

    def test_classic_receipt_rejects_other_matching_signed_domains(self):
        receipt, policy, root, _ = fixture(domain="origen.chispazo.experimental.provenance")
        with self.assertRaisesRegex(
            ValueError,
            "V1 trust receipt modality CLASSIC requires policy domain",
        ):
            self.inspect(
                receipt, policy, root, "origen.chispazo.experimental.provenance"
            )


if __name__ == "__main__":
    unittest.main()
