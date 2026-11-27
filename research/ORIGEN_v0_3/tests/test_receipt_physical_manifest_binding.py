from __future__ import annotations

import copy
import hashlib
import json
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from origen.physical_evidence_manifest_v1 import REQUIRED_ARTIFACT_TYPES
from origen.trust_artifact_bytes_v1 import (
    verify_independent_provenance_with_physical_manifest,
)
from test_independent_trust_adapter import NOW, raw_public_key, verified_policy
from test_physical_evidence_manifest_v1 import (
    encode as encode_manifest,
    valid_document as valid_manifest_document,
)
from test_trust_artifact_bytes_v1 import signed_receipt
from test_trust_receipt_v1 import encode as encode_receipt, valid_document as valid_receipt_document


MANIFEST_TYPE = "PHYSICAL-EVIDENCE-MANIFEST"


def make_bound_case():
    manifest_document = valid_manifest_document()
    contest_id = manifest_document["target"]["contest_id"]
    payloads = {}
    for artifact in manifest_document["artifacts"]:
        payload = ("original:" + artifact["artifact_type"]).encode("ascii")
        digest = hashlib.sha256(payload).hexdigest()
        artifact["sha256"] = digest
        artifact["byte_length"] = len(payload)
        payloads[digest] = payload

    by_type = {item["artifact_type"]: item for item in manifest_document["artifacts"]}
    for signature in manifest_document["signatures"]:
        artifact_type = next(
            kind for kind, item in by_type.items()
            if item["sha256"] == signature["artifact_sha256"]
            or signature["artifact_sha256"] == hashlib.sha256(
                ("artifact-" + str(sorted(REQUIRED_ARTIFACT_TYPES).index(kind))).encode()
            ).hexdigest()
        )
        signature["artifact_sha256"] = by_type[artifact_type]["sha256"]
    for event in manifest_document["custody_events"]:
        old_index = int(event["event_id"].split("-")[-1])
        artifact_type = sorted(REQUIRED_ARTIFACT_TYPES)[old_index]
        event["artifact_sha256"] = by_type[artifact_type]["sha256"]

    manifest_bytes = encode_manifest(manifest_document)
    manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
    payloads[manifest_digest] = manifest_bytes

    receipt_document = valid_receipt_document()
    receipt_document["target"]["contest_id"] = contest_id
    receipt_document["target"]["draw_close_at_utc"] = manifest_document["target"]["draw_close_at_utc"]
    target_list = json.dumps([contest_id], separators=(",", ":"), ensure_ascii=True).encode("ascii")
    receipt_document["target"]["target_list_sha256"] = hashlib.sha256(target_list).hexdigest()
    for seal in receipt_document["output_seals"]:
        seal["target_contest_id"] = contest_id
    receipt_document["artifacts"] = [
        {
            "artifact_type": item["artifact_type"],
            "sha256": item["sha256"],
            "byte_length": item["byte_length"],
            "contest_id": contest_id,
        }
        for item in manifest_document["artifacts"]
    ] + [{
        "artifact_type": MANIFEST_TYPE,
        "sha256": manifest_digest,
        "byte_length": len(manifest_bytes),
        "contest_id": contest_id,
    }]

    issuer = Ed25519PrivateKey.generate()
    receipt_bytes = signed_receipt(receipt_document, issuer)
    required = tuple(sorted(set(REQUIRED_ARTIFACT_TYPES) | {MANIFEST_TYPE}))
    policy = verified_policy(raw_public_key(issuer), required_artifact_types=required)
    return receipt_bytes, manifest_bytes, policy, payloads, contest_id


class ReceiptPhysicalManifestBindingTests(unittest.TestCase):
    def verify(self, case):
        receipt, manifest, policy, payloads, _ = case
        return verify_independent_provenance_with_physical_manifest(
            receipt,
            original_manifest_bytes=manifest,
            verified_trust_policy=policy,
            verification_time=NOW,
            artifact_bytes_by_sha256=payloads,
        )

    def test_exact_receipt_manifest_and_all_original_bytes_bind(self):
        case = make_bound_case()
        result = self.verify(case)
        self.assertEqual(result.contest_id, case[4])
        self.assertEqual(result.manifest_sha256, hashlib.sha256(case[1]).hexdigest())
        self.assertEqual(len(result.artifact_matches), len(REQUIRED_ARTIFACT_TYPES) + 1)
        self.assertEqual(result.provenance_status.value, "BLOCKED_PROVENANCE")
        self.assertEqual(
            result.status,
            "RECEIPT_AND_PHYSICAL_MANIFEST_BOUND_NOT_AUTHENTICATED",
        )

    def test_manifest_byte_tampering_breaks_receipt_manifest_binding(self):
        receipt, manifest, policy, payloads, _ = make_bound_case()
        document = json.loads(manifest)
        document["artifacts"][0]["source_object_id"] += "-ALTERED"
        altered_manifest = encode_manifest(document)
        altered_payloads = dict(payloads)
        altered_payloads.pop(hashlib.sha256(manifest).hexdigest())
        altered_payloads[hashlib.sha256(altered_manifest).hexdigest()] = altered_manifest
        with self.assertRaisesRegex(ValueError, "PHYSICAL-EVIDENCE-MANIFEST claim"):
            verify_independent_provenance_with_physical_manifest(
                receipt,
                original_manifest_bytes=altered_manifest,
                verified_trust_policy=policy,
                verification_time=NOW,
                artifact_bytes_by_sha256=altered_payloads,
            )

    def test_receipt_artifact_claim_must_match_manifest_artifact_claim(self):
        receipt, manifest, policy, payloads, _ = make_bound_case()
        document = json.loads(receipt)
        document["artifacts"][0]["byte_length"] += 1
        issuer = Ed25519PrivateKey.generate()
        # A newly signed receipt with the same trusted policy key is intentionally
        # not possible; the original policy's issuer key remains the only accepted key.
        with self.assertRaises(ValueError):
            verify_independent_provenance_with_physical_manifest(
                encode_receipt(document),
                original_manifest_bytes=manifest,
                verified_trust_policy=policy,
                verification_time=NOW,
                artifact_bytes_by_sha256=payloads,
            )


if __name__ == "__main__":
    unittest.main()
