# ORIGEN v1 signed trust-policy envelope

## Purpose

The signed envelope is a bounded, versioned distribution format for issuer keys
used by the root receipt-attestation verifier. It verifies an Ed25519 signature
over the complete policy claims using a root public key supplied separately by
the deployment trust boundary.

## Required deployment inputs

The caller MUST supply all of the following from independently reviewed,
access-controlled deployment configuration:

- The exact 32-byte Ed25519 root public key.
- The expected root key identifier.
- The minimum acceptable policy sequence, persisted outside the downloaded
  envelope and protected against rollback.
- A verification clock whose trust properties are understood by the deployment.

Never read the pinned key, key identifier, or minimum sequence from the policy
envelope itself, the receipt, an untrusted API response, or a user-controlled
file. If an attacker can replace both the envelope and the pin, signature
verification provides no authenticity.

## Envelope contract

Schema: `origen.trust-policy-envelope.v1`.

The canonical signed payload is UTF-8 JSON serialized with sorted keys,
compact separators, and ASCII escaping, with the top-level `signature` member
removed. Duplicate object keys, unknown/missing fields, non-canonical
identifiers, non-UTC timestamps, malformed/canonicality-violating base64,
oversized envelopes, duplicate issuer/key identities, and public-key reuse
are rejected.

The envelope binds:
- schema and policy version;
- monotonic policy sequence;
- policy-authority identifier and pinned root key identifier;
- issue, not-before, and expiry times;
- issuer key identities, raw Ed25519 public keys, validity intervals, and
  revocation flags;
- Ed25519 signature over all preceding claims.

The verifier enforces the externally supplied minimum sequence and the
caller-supplied verification time. The caller's clock is not independently
authenticated by this module.

## Security boundary / non-claims

A successful result means only that the envelope signature matches the
separately supplied root key, its declared key identifier matches the
deployment pin, its sequence meets the supplied floor, and its schema and
validity checks pass.

It does NOT prove:
- who provisioned the root key or whether the deployment pin is authentic;
- that the local clock is trusted or protected from rollback;
- that a key was revoked before the local verifier learned of the revocation;
- nested participant or custodian signatures;
- RFC 3161 timestamp-token validity;
- external ledger inclusion or independent custody;
- physical draw-machine identity, calibration, sphere provenance, or bias;
- prospective predictive performance or eligibility for production.

The current code is an isolated trust-policy verification primitive. It is not
wired into `verify_independent_provenance`; that path must remain fail-closed
until a real independently provisioned root, anti-rollback state, trusted time,
and authentic external evidence services are operationally supplied and
audited. Synthetic keys in tests are never production trust anchors.
