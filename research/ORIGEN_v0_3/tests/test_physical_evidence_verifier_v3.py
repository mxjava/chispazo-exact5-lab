from __future__ import annotations
import base64, copy, json
from datetime import datetime, timezone
import unittest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from origen.independent_trust_adapter import ProvenanceStatus
from origen.physical_evidence_verifier_v3 import ROLE_STATUS, verify_physical_evidence_signatures_v3
from origen.trust_policy_envelope_v3 import SCHEMA_VERSION_V3, verify_signed_trust_policy_v3
from test_physical_evidence_manifest_v1 import encode
from test_physical_evidence_verifier_v2 import (
 fixture as v2_fixture, ROOT_KEY_ID, POLICY_SEQUENCE, POLICY_DOMAIN, NOW,
 _raw_public_key,
)

def signed_v3_policy(data, *, wrong_role=False, wrong_artifact=False, duplicate_role=False):
 doc=data["document"]
 artifact_types={a["sha256"]:a["artifact_type"] for a in doc["artifacts"]}
 grouped={}
 for claim in doc["signatures"]:
  identity=(claim["subject_id"],claim["key_id"])
  role=claim["role"]
  artifact_type=artifact_types[claim["artifact_sha256"]]
  grouped.setdefault(identity,{}).setdefault(role,set()).add(artifact_type)
 identities=sorted(grouped)
 issuer_keys=[]
 for index,identity in enumerate(identities):
  private=data["private_by_identity"][identity]
  role_map=grouped[identity]
  auth=[]
  for role,types in sorted(role_map.items()):
   if index==0 and wrong_role: role="UNAUTHORIZED-ROLE"
   if index==0 and wrong_artifact:
    all_types=sorted(set(artifact_types.values()))
    types={next(x for x in all_types if x not in types)}
   auth.append({"role":role,"artifact_types":sorted(types)})
  if index==0 and duplicate_role: auth.append(copy.deepcopy(auth[0]))
  issuer_keys.append({
   "issuer_id":identity[0],"key_id":identity[1],
   "public_key_b64":base64.b64encode(_raw_public_key(private)).decode("ascii"),
   "valid_from_utc":"2026-01-01T00:00:00Z",
   "valid_until_utc":"2027-01-01T00:00:00Z",
   "revoked":False,"authorizations":auth,
  })
 root=Ed25519PrivateKey.generate()
 document={
  "schema_version":SCHEMA_VERSION_V3,"policy_domain":POLICY_DOMAIN,
  "policy_version":"physical-policy-v3-test","policy_sequence":POLICY_SEQUENCE,
  "issuer_id":"synthetic-policy-root","root_key_id":ROOT_KEY_ID,
  "issued_at_utc":"2026-11-24T00:00:00Z",
  "not_before_utc":"2026-11-24T00:00:00Z",
  "expires_at_utc":"2026-12-01T00:00:00Z",
  "issuer_keys":issuer_keys,
  "signature":{"algorithm":"ed25519","signature_b64":""},
 }
 unsigned=copy.deepcopy(document); unsigned.pop("signature")
 sig=root.sign(json.dumps(unsigned,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode("ascii"))
 document["signature"]["signature_b64"]=base64.b64encode(sig).decode("ascii")
 return encode(document),_raw_public_key(root),document

def inspect(data, policy, root_public):
 return verify_physical_evidence_signatures_v3(
  data["raw_manifest_bytes"],data["artifact_bytes_by_sha256"],
  data["signature_bytes_by_sha256"],signed_policy_envelope_bytes=policy,
  pinned_root_public_key_bytes=root_public,expected_root_key_id=ROOT_KEY_ID,
  expected_policy_domain=POLICY_DOMAIN,minimum_policy_sequence=POLICY_SEQUENCE,
  verification_time=NOW)

class PhysicalEvidenceSignatureVerifierV3Tests(unittest.TestCase):
 def test_signed_key_role_artifact_matrix_verifies_but_provenance_stays_blocked(self):
  data=v2_fixture(); policy,root,_=signed_v3_policy(data)
  result=inspect(data,policy,root)
  self.assertEqual(result.signatures_verified,len(data["signature_bytes_by_sha256"]))
  self.assertEqual(result.role_authorization_status,ROLE_STATUS)
  self.assertTrue(all(x.role_authorization_status==ROLE_STATUS for x in result.signature_results))
  self.assertIs(result.provenance_status,ProvenanceStatus.BLOCKED_PROVENANCE)
  self.assertIn("INSTITUTIONAL_SIGNER_IDENTITY_AND_ROLE_DELEGATION_NOT_AUTHENTICATED",result.remaining_blockers)

 def test_correct_signature_with_unsigned_role_claim_not_in_signed_matrix_is_rejected(self):
  data=v2_fixture(); policy,root,_=signed_v3_policy(data,wrong_role=True)
  with self.assertRaisesRegex(ValueError,"role is not authorized"):
   inspect(data,policy,root)

 def test_role_authorized_for_different_artifact_type_is_rejected(self):
  data=v2_fixture(); policy,root,_=signed_v3_policy(data,wrong_artifact=True)
  with self.assertRaisesRegex(ValueError,"artifact type is not authorized"):
   inspect(data,policy,root)

 def test_duplicate_role_authorization_is_rejected_even_when_root_signed(self):
  data=v2_fixture(); policy,root,_=signed_v3_policy(data,duplicate_role=True)
  with self.assertRaisesRegex(ValueError,"duplicate role authorization"):
   verify_signed_trust_policy_v3(
    policy,pinned_root_public_key_bytes=root,expected_root_key_id=ROOT_KEY_ID,
    expected_policy_domain=POLICY_DOMAIN,minimum_policy_sequence=POLICY_SEQUENCE,
    verification_time=NOW)

 def test_v2_policy_cannot_be_silently_upgraded_to_v3(self):
  data=v2_fixture()
  with self.assertRaisesRegex(ValueError,"fields mismatch|unsupported trust-policy"):
   inspect(data,data["signed_policy_envelope_bytes"],data["pinned_root_public_key_bytes"])

if __name__=="__main__":
 unittest.main()


from datetime import timedelta, tzinfo

class _StatefulOffsetTimezone(tzinfo):
    """Adversarial tzinfo that changes its answer after the first snapshot."""
    def __init__(self):
        self.calls = 0

    def utcoffset(self, dt):
        self.calls += 1
        return timedelta(hours=-2 if self.calls == 1 else 2)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "stateful-test-offset"


class PhysicalEvidenceVerifierV3ClockSnapshotTests(unittest.TestCase):
    def test_custom_timezone_offset_is_snapshotted_once_for_entire_verification(self):
        data = v2_fixture()
        policy, root_public, _ = signed_v3_policy(data)
        tz = _StatefulOffsetTimezone()
        supplied_time = datetime(2026, 11, 24, 12, 0, tzinfo=tz)

        result = verify_physical_evidence_signatures_v3(
            data["raw_manifest_bytes"],
            data["artifact_bytes_by_sha256"],
            data["signature_bytes_by_sha256"],
            signed_policy_envelope_bytes=policy,
            pinned_root_public_key_bytes=root_public,
            expected_root_key_id=ROOT_KEY_ID,
            expected_policy_domain=POLICY_DOMAIN,
            minimum_policy_sequence=POLICY_SEQUENCE,
            verification_time=supplied_time,
        )

        self.assertEqual(tz.calls, 1)
        self.assertEqual(
            result.verification_time_utc,
            datetime(2026, 11, 24, 14, 0, tzinfo=timezone.utc),
        )
        self.assertIs(result.provenance_status, ProvenanceStatus.BLOCKED_PROVENANCE)
