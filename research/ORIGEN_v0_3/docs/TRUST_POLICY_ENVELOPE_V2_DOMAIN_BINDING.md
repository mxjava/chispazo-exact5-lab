# ORIGEN signed trust-policy envelope V2: policy-domain binding

Status: RESEARCH ONLY / SYNTHETIC FIXTURES / NOT A DEPLOYMENT TRUST ANCHOR

## Why V2 exists

V1 signs a schema version and policy claims, but it does not carry a signed
policy-domain identifier. If an Ed25519 root is reused across deployments or
evidence domains, a valid V1 envelope can be replayed wherever that same root,
key ID and sequence floor are accepted.

V2 adds a mandatory `policy_domain` member to the canonical signed payload.
The verifier also requires an independently configured
`expected_policy_domain` and rejects any mismatch. The domain therefore
cannot be changed without invalidating the root signature, and a correctly
signed envelope for one domain is not accepted in another.

Example domain identifiers are deployment-specific labels such as
`origen.chispazo.classic.provenance` and
`origen.chispazo.de-lastres.provenance`. These strings are examples only;
they are not currently provisioned institutional domains.

## V2 envelope contract

Schema: `origen.trust-policy-envelope.v2`.

V2 preserves the V1 bounds and checks:
- exact UTF-8 bytes, canonical JSON encoding and no duplicate object keys;
- exact schema fields and bounded nesting/size;
- Ed25519 root signature over the canonical document without `signature`;
- pinned root key ID and minimum policy sequence;
- issue, not-before and expiry chronology;
- unique issuer/key identities and no public-key reuse;
- canonical base64, UTC timestamps and exact boolean revocation flags.

The signed `policy_domain` must match the verifier's separately supplied
`expected_policy_domain`. V1 is not silently upgraded or interpreted as V2.

## Composition and fail-closed behavior

`inspect_signed_root_attestation_chain_v2` verifies the original V2 policy
bytes, then verifies the original receipt bytes under the issuer key carried by
that verified policy. It calls `verify_independent_provenance` and requires
that adapter to return `BLOCKED_PROVENANCE`.

The diagnostic result explicitly labels root provisioning and anti-rollback
state as `CALLER_SUPPLIED_UNAUTHENTICATED`. It has no authenticated or
production-eligible status. Passing the synthetic tests proves only the
software behavior relative to synthetic keys and caller-supplied pins.

## What this does not solve

- The root public key, root key ID, expected domain, sequence floor and clock
  are still caller-supplied. Their out-of-band provisioning is not authenticated
  by this module.
- No persistent monotonic store, compare-and-swap transaction, rollback
  detection across restart, or split-brain protection is implemented.
- No institutional authority has been bound to either example domain.
- Key revocation freshness, OCSP/CRL validation, complete PKIX processing,
  nested physical signatures, ledger inclusion, witness quorum, and custody
  remain external blockers.
- `verify_independent_provenance` remains fail-closed and production remains
  `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Deployment requirement

The expected domain must be provisioned in the same independently reviewed
deployment trust ceremony as the root key and key ID. Do not derive it from
the envelope, receipt, request, command line, environment supplied by an
untrusted caller, or URL. If domain isolation is required, provision distinct
root keys and sequence namespaces as well; V2 domain binding is defense in
depth, not a replacement for key separation.

The synthetic test keys are generated at test time and must never be copied
into deployment configuration.
