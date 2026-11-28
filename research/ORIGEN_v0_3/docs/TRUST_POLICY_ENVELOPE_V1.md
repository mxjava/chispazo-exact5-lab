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

The complete received envelope MUST itself be byte-for-byte equal to UTF-8
JSON serialization of the parsed object using sorted keys, compact separators,
and ASCII escaping, including the `signature` member. The Ed25519 signed payload
is the same canonical serialization with the top-level `signature` member
removed. Noncanonical whitespace, key ordering, or alternate UTF-8 spellings
are rejected even if the canonicalized claims carry a valid signature. Duplicate
object keys, unknown/missing fields, non-canonical identifiers, non-UTC
timestamps, malformed/canonicality-violating base64, oversized envelopes,
duplicate issuer/key identities, and public-key reuse are also rejected.

The envelope binds:
- schema and policy version;
- monotonic policy sequence;
- policy-authority identifier and pinned root key identifier;
- issue, not-before, and expiry times;
- issuer key identities, raw Ed25519 public keys, validity intervals, and
  revocation flags;
- Ed25519 signature over all preceding claims.

The verifier enforces the externally supplied minimum sequence as an exact
positive signed 64-bit integer (1..`MAX_POLICY_SEQUENCE`) and the
caller-supplied verification time. An out-of-domain sequence floor is rejected
at the API boundary before the envelope is evaluated. The caller's clock is
not independently authenticated by this module.

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
