"""V3 physical verifier: signed key-to-role-to-artifact authorization."""
from __future__ import annotations
from datetime import datetime
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from origen.physical_evidence_manifest_v1 import parse_unverified_physical_manifest
from origen.trust_policy_envelope_v3 import VerifiedTrustPolicyV3, verify_signed_trust_policy_v3
from origen.trust_verifier_v1 import TrustedIssuerKey
from origen.physical_evidence_verifier_v2 import (
 CLASSIC_PHYSICAL_POLICY_DOMAIN, PHYSICAL_SIGNATURE_REMAINING_BLOCKERS,
 NestedSignatureVerification, PhysicalEvidenceSignatureInspection,
 _utc_instant, _exact_bytes_mapping, canonical_physical_manifest_signature_payload,
)
from origen.independent_trust_adapter import ProvenanceStatus

ROLE_STATUS="SIGNED_POLICY_MATCH_ONLY_NOT_INSTITUTIONALLY_AUTHENTICATED"

def verify_physical_evidence_signatures_v3(
 raw_manifest_bytes:bytes, artifact_bytes_by_sha256:dict[str,bytes],
 signature_bytes_by_sha256:dict[str,bytes], *,
 signed_policy_envelope_bytes:bytes, pinned_root_public_key_bytes:bytes,
 expected_root_key_id:str, expected_policy_domain:str,
 minimum_policy_sequence:int, verification_time:datetime,
)->PhysicalEvidenceSignatureInspection:
 """Verify exact bytes and signed key/role/artifact authorization.

 Root, domain, sequence floor and clock remain caller-supplied. A policy role
 match is not institutional identity/delegation proof. Always BLOCKED_PROVENANCE.
 """
 if type(raw_manifest_bytes) is not bytes: raise TypeError("raw manifest must be exact bytes")
 if type(signed_policy_envelope_bytes) is not bytes: raise TypeError("policy envelope must be exact bytes")
 verified_at=_utc_instant(verification_time,"verification_time")
 manifest=parse_unverified_physical_manifest(raw_manifest_bytes)
 artifacts=_exact_bytes_mapping(artifact_bytes_by_sha256,"artifact_bytes_by_sha256")
 signatures=_exact_bytes_mapping(signature_bytes_by_sha256,"signature_bytes_by_sha256")
 by_digest={item.sha256:item for item in manifest.artifacts}
 if set(artifacts)!=set(by_digest): raise ValueError("artifact byte map must contain exactly the manifest artifact digests")
 for digest,claim in by_digest.items():
  original=artifacts[digest]
  if len(original)!=claim.byte_length: raise ValueError(f"artifact byte length mismatch for {claim.artifact_type}")
  import hashlib
  if hashlib.sha256(original).hexdigest()!=digest: raise ValueError(f"artifact SHA-256 mismatch for {claim.artifact_type}")
 expected={item.signature_sha256 for item in manifest.signatures}
 if set(signatures)!=expected: raise ValueError("signature byte map must contain exactly the manifest signature digests")
 import hashlib
 for digest,original in signatures.items():
  if hashlib.sha256(original).hexdigest()!=digest: raise ValueError("signature SHA-256 does not match manifest claim")
 policy:VerifiedTrustPolicyV3=verify_signed_trust_policy_v3(
  signed_policy_envelope_bytes,pinned_root_public_key_bytes=pinned_root_public_key_bytes,
  expected_root_key_id=expected_root_key_id,expected_policy_domain=expected_policy_domain,
  minimum_policy_sequence=minimum_policy_sequence,verification_time=verification_time)
 if type(policy) is not VerifiedTrustPolicyV3: raise TypeError("unexpected verified policy result")
 if policy.policy_domain!=CLASSIC_PHYSICAL_POLICY_DOMAIN: raise ValueError("CLASSIC manifest requires CLASSIC policy domain")
 keys={}
 for key in policy.policy.issuer_keys:
  if type(key) is not TrustedIssuerKey: raise ValueError("verified policy contains invalid issuer key")
  identity=(key.issuer_id,key.key_id)
  if identity in keys: raise ValueError("duplicate signer identity in verified policy")
  keys[identity]=key
 authorizations={}
 if type(policy.key_authorizations) is not tuple: raise ValueError("verified policy authorizations must be an exact tuple")
 for item in policy.key_authorizations:
  if type(item) is not tuple or len(item)!=4 or any(type(x) is not str for x in item[:3]) or type(item[3]) is not tuple or any(type(x) is not str for x in item[3]):
   raise ValueError("verified policy authorization has invalid shape")
  identity=(item[0],item[1])
  if identity not in keys: raise ValueError("authorization references an unknown policy key")
  role_map=authorizations.setdefault(identity,{})
  if item[2] in role_map: raise ValueError("duplicate key/role authorization")
  role_map[item[2]]=frozenset(item[3])
 payload=canonical_physical_manifest_signature_payload(raw_manifest_bytes)
 results=[]
 for index,claim in enumerate(manifest.signatures):
  if claim.algorithm!="ed25519": raise ValueError(f"signatures[{index}] uses unsupported algorithm")
  identity=(claim.subject_id,claim.key_id)
  key=keys.get(identity)
  if key is None: raise ValueError(f"signatures[{index}] signer subject/key absent from signed policy")
  if key.revoked: raise ValueError(f"signatures[{index}] signer key is revoked")
  if not key.valid_from_utc<=verified_at<=key.valid_until_utc: raise ValueError(f"signatures[{index}] signer key outside policy validity")
  artifact_type=by_digest[claim.artifact_sha256].artifact_type
  allowed=authorizations.get(identity,{}).get(claim.role)
  if allowed is None: raise ValueError(f"signatures[{index}] role is not authorized for signer subject/key")
  if artifact_type not in allowed: raise ValueError(f"signatures[{index}] artifact type is not authorized for signer role")
  try: Ed25519PublicKey.from_public_bytes(key.public_key_bytes).verify(signatures[claim.signature_sha256],payload)
  except (InvalidSignature,ValueError) as exc: raise ValueError(f"signatures[{index}] nested Ed25519 signature verification failed") from exc
  results.append(NestedSignatureVerification(claim.artifact_sha256,claim.subject_id,claim.role,claim.key_id,claim.signature_sha256,True,ROLE_STATUS))
 return PhysicalEvidenceSignatureInspection(
  manifest.raw_sha256,policy.envelope_sha256,policy.policy_domain,policy.policy_sequence,
  verified_at,len(manifest.artifacts),len(results),tuple(results),
  "CALLER_SUPPLIED_UNAUTHENTICATED","CALLER_SUPPLIED_UNAUTHENTICATED",
  "CALLER_SUPPLIED_UNAUTHENTICATED",ROLE_STATUS,
  "UNVERIFIED_RFC3161_REQUIRED","UNVERIFIED_EXTERNAL_INCLUSION_REQUIRED",
  "UNVERIFIED_INDEPENDENT_RECEIPTS_REQUIRED",ProvenanceStatus.BLOCKED_PROVENANCE,
  tuple(x for x in PHYSICAL_SIGNATURE_REMAINING_BLOCKERS if x!="SIGNER_ROLE_AUTHORIZATION_NOT_BOUND_TO_POLICY_V2")
  +("INSTITUTIONAL_SIGNER_IDENTITY_AND_ROLE_DELEGATION_NOT_AUTHENTICATED",))
