# ORIGEN v0.3 — Independent Trust Adapter Specification

Status: PARTIAL IMPLEMENTATION — SIGNATURE AND BYTE-BINDING UNIT ONLY; FULL TRUST ADAPTER NOT IMPLEMENTED  
Date: 2026-11-21  
Parent baseline: `eb08acdb6a50ab3b5159348864f52bba075b480b`  
Scope: bridge structural intake/custody validation to independently authenticated evidence.

## 1. Security objective

ORIGEN may classify a contest as prospectively eligible only when every provenance assertion is verified against independently controlled trust roots and original evidence bytes. A self-consistent CSV, caller-supplied reference set, URL, timestamp string, or re-hashed seal is not authentication.

A research-only Ed25519 verifier now exists at `src/origen/trust_adapter.py`. It verifies detached signatures against caller-supplied pinned-key material, explicit role lists, strict root-field/boolean policy, enabled/revoked flags, canonical `not_before_utc`/`not_after_utc` key-validity bounds, attestation validity, and the SHA-256 of exact original bytes. The key must be valid at both the supplied verification time and attestation issuance time. These checks use caller-supplied `verification_time_utc`; they do not establish trusted time. Malformed external inputs fail closed. Unit tests cover signature tampering, byte substitution, malformed roles/root policy, disabled/revoked roots, and expired/not-yet-valid keys. The verifier now requires an independently issued `expected_nonce` challenge and rejects any signed envelope whose nonce differs; both values must use strict URL-safe ASCII syntax. The caller must obtain the expected challenge from an independently controlled challenge issuer. This comparison does not prove challenge origin, single use, or replay prevention; the verifier explicitly reports replay protection as not checked because no durable nonce ledger exists. This is only a partial cryptographic primitive: trust-root provisioning, identity proof, authoritative revocation feeds, trusted timestamps, external ledger/custody, receipt issuance, end-to-end eligibility integration and independent review remain unimplemented. No physical evidence or real institutional trust roots have been received. System state remains `BLOCKED_PROVENANCE / RESEARCH_ONLY_NO_EDGE`.

## 2. Required trust boundary

The current structural layer may continue to validate schema, internal consistency, chronology declarations, hashes, and custody-chain shape. Its outputs must be named and typed as declarations, e.g. `STRUCTURAL_ONLY`; they must never be accepted as authenticated verification receipts.

Only one adapter boundary may construct authenticated reference sets consumed by temporal eligibility. No public CLI option, CSV column, environment variable, or caller argument may directly populate those sets.

Required flow:

1. Read original source artifacts as bytes from a controlled intake store.
2. Compute SHA-256 locally; compare with the digest in a signed source manifest.
3. Verify detached signatures against pinned trust roots and a versioned trust policy.
4. Verify signer identity, role authorization, validity interval, key status/revocation and separation of duties.
5. Verify timestamp tokens or trusted ledger inclusion proofs; do not trust timestamps merely because they parse or precede the draw close.
6. Verify custodian receipt and externally anchored append-only ledger head.
7. Verify candidate/code/preregistration hashes and exact target-contest list against a pre-outcome commitment.
8. Verify two independent Exact5 output seals created before the relevant close, including portfolio bytes and generator identity.
9. Produce a machine-verifiable receipt binding all verified artifacts and policy version.
10. Only the receipt may authorize authenticated eligibility.

## 3. Evidence envelope

Each artifact envelope must bind at minimum:

- artifact type and schema version;
- original byte SHA-256 and byte length;
- contest ID, modality, draw date and local close time with explicit timezone/offset;
- source identifier and immutable source-object identifier;
- measurement, mapping, assignment and receipt event times as distinct fields;
- device/equipment ID, sphere set ID and calibration certificate digest where applicable;
- signer subject, signer role, key ID and signature algorithm;
- signature bytes and timestamp/ledger proof references;
- custody event ID, prior ledger-head digest and resulting ledger-head digest;
- preregistration, candidate, code, environment and target-list commitment digests.

A URL is a locator, not evidence. A digest is an integrity check, not proof of origin. A claimed timestamp is data, not proof of time.

## 4. Independent trust policy

Trust roots must be configured outside the evidence bundle and outside the submitting user's control. The policy must define:
- accepted signature and digest algorithms;
- authorized institutions, signer identities and roles;
- key validity, revocation and rollover handling;
- timestamp authority or independent ledger requirements;
- custodian identity and independence from model generation;
- quorum or dual-control requirements for critical events;
- timezone normalization and trusted-clock policy;
- policy version and effective dates.

A verifier must fail closed for unknown, expired, revoked, ambiguous or self-signed identities. Do not silently downgrade to unsigned verification.

## 5. Receipt contract

The adapter returns a signed/attested verification receipt with:
- `status`: `AUTHENTICATED` or `REJECTED`;
- policy version and verifier build digest;
- exact artifact digests verified;
- signer/custodian identities and roles;
- trusted time proofs and ledger anchor;
- exact contest IDs and target-list digest;
- preregistration/candidate/code digests;
- two pre-close output-seal digests;
- explicit failure codes for every missing or invalid assertion.

The downstream evaluator accepts only an `AUTHENTICATED` receipt whose digests exactly match the run inputs. It must not accept caller-created booleans or arbitrary string sets as a substitute.

## 6. Mandatory adversarial tests

| Attack / defect | Expected result |
|---|---|
| Caller supplies arbitrary strings in verified-reference sets | Reject; no authenticated eligibility |
| CSV contains valid-looking URL and 64-hex digest but source bytes absent | Reject |
| Source bytes differ by one byte from signed digest | Reject |
| Self-signed or unknown signer | Reject |
| Expired or revoked signing key | Reject |
| Pinned key is not yet valid or is past `not_after_utc` | Reject |
| Pinned key validity interval is malformed, reversed, or empty | Reject |
| Attestation issuance time is outside the pinned key validity interval | Reject |
| Timestamp string predates close but lacks trusted timestamp proof | Reject |
| Timestamp proof is after close | Reject |
| Custodian equals generator where separation is required | Reject |
| Custody chain is internally re-hashed but has no independent ledger anchor | Reject |
| External ledger head does not match receipt | Reject |
| Target list changed after preregistration | Reject |
| Target outcomes were already observed before commitment | Reject |
| Candidate, code or preregistration digest mismatch | Reject |
| One or both Exact5 seals missing or created after close | Reject |
| Two seals are byte-identical when independent generation is required | Reject |
| Historical replay has positive synthetic lift and favorable p-family | Statistical screen may pass; `research_edge` must remain false |
| Signed nonce differs from the independently issued expected challenge | Reject |
| Expected nonce is missing, malformed, or caller-controlled | Reject at verifier boundary; independent issuance remains an external requirement |
| Valid envelope but any one evidence gate missing | `BLOCKED_PROVENANCE` |

Tests must include both unit-level signature/proof fixtures and end-to-end CLI tests. Fixtures must use explicitly synthetic test keys and must never be mistaken for real institutional trust roots.

## 7. Classification contract

Separate these concepts:
- `statistical_screen_passed`: numerical screen on supplied data; never implies provenance.
- `structural_intake_passed`: schema and internal consistency only.
- `authenticated_provenance_passed`: only from the independent adapter receipt.
- `prospective_protocol_passed`: preregistration, untouched target sequence, and two pre-close seals all verified.
- `research_edge`: false by default; may become true only after authenticated provenance, prospective protocol, at least 100 consecutive eligible Classic contests, preregistered positive mean log-lift, Holm-adjusted p < 0.05, anytime e-value >= 20, and no integrity/calibration failure.

No classification in this document authorizes betting or production use. V294 remains frozen and production remains blocked.

## 8. Implementation sequence and acceptance gates

A. Define typed receipt schema and strict parser — NOT STARTED. The primitive now requires and compares a caller-supplied expected nonce challenge, but does not establish its independent issuance or one-time consumption. Replay protection and nonce uniqueness still require a durable, independently controlled ledger; the current primitive does not prevent replay.  
B. Implement byte-level source verifier and signature verification — PARTIAL: Ed25519 detached-signature and exact-byte SHA-256 binding primitive exists; manifest schema and controlled intake integration remain.  
C. Implement trusted-time and external-ledger verification — NOT STARTED.  
D. Implement identity/role/separation-of-duties policy — PARTIAL: role allow-list and key enabled/revoked flags are checked; identity proof, authoritative revocation and separation-of-duties remain.  
E. Bind preregistration, target list, code and candidate commitments.  
F. Bind both pre-close Exact5 seals.  
G. Remove public/caller control of authenticated reference sets.  
H. Add adversarial tests above and run full CI.  
I. Obtain independent security review and real institutional evidence before changing provenance status.

Acceptance requires all tests passing, negative tests demonstrating fail-closed behavior, reproducible verifier build, and an independent review. Passing software tests alone does not authenticate any real-world evidence.
