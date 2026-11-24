# ORIGEN v0.3 — Independent Trust Adapter Specification

Status: RESEARCH SPECIFICATION / NOT IMPLEMENTED  
Date: 2026-11-21  
Parent baseline: `eb08acdb6a50ab3b5159348864f52bba075b480b`  
Scope: bridge structural intake/custody validation to independently authenticated evidence.

## 1. Security objective

ORIGEN may classify a contest as prospectively eligible only when every provenance assertion is verified against independently controlled trust roots and original evidence bytes. A self-consistent CSV, caller-supplied reference set, URL, timestamp string, or re-hashed seal is not authentication.

This specification does not claim that any physical evidence has been received, that any signature infrastructure exists, or that the adapter is implemented. Until implementation and independent review, the system state remains `BLOCKED_PROVENANCE / RESEARCH_ONLY_NO_EDGE`.

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
- two pre-close output-seal digests, each structurally linked to exactly one signer claim by a unique signature digest;
- explicit failure codes for every missing or invalid assertion.

The structural parser requires each output-seal signature digest to resolve to a declared signer signature digest, and signer signature digests must be unique. This only removes ambiguous/unbound references; it does not verify signature bytes, key ownership, signer role authorization, or institutional identity.

Each output seal must also carry `timestamp_proof_sha256`, resolving to exactly one declared trusted-time proof whose `event_at_utc` exactly equals that seal's `created_at_utc`. The two output seals must reference distinct proof digests. The receipt attestation continues to reference its own trusted-time proof. This is structural binding only: the parser does not authenticate the timestamp token, its authority, its signature, or its claimed event time.

The parser also rejects literal identifier aliasing between trusted-time authority IDs and the receipt issuer, signers, custodians, or generators. This is only a structural collision guard: distinct strings do not establish distinct legal entities, independent services, or authenticated time authority. It also rejects a ledger anchor whose resulting head digest equals its previous head digest: a claimed append must advance the committed ledger state. This is a structural transition check only; it does not verify the ledger, entry, or inclusion proof.

The downstream evaluator accepts only an `AUTHENTICATED` receipt whose digests exactly match the run inputs. It must not accept caller-created booleans or arbitrary string sets as a substitute.

## 6. Mandatory adversarial tests

| Attack / defect | Expected result |
|---|---|
| Caller supplies arbitrary strings in verified-reference sets | Reject; no authenticated eligibility |
| CSV contains valid-looking URL and 64-hex digest but source bytes absent | Reject |
| Source bytes differ by one byte from signed digest | Reject |
| Self-signed or unknown signer | Reject |
| Expired or revoked signing key | Reject |
| Timestamp string predates close but lacks trusted timestamp proof | Reject |
| Timestamp proof is after close | Reject |
| Custodian equals generator where separation is required | Reject |
| Custody chain is internally re-hashed but has no independent ledger anchor | Reject |
| External ledger head does not match receipt | Reject |
| Ledger entry claims the same previous and resulting head digest | Reject |
| Target list changed after preregistration | Reject |
| Target outcomes were already observed before commitment | Reject |
| Candidate, code or preregistration digest mismatch | Reject |
| One or both Exact5 seals missing or created after close | Reject |
| Two seals are byte-identical when independent generation is required | Reject |
| Historical replay has positive synthetic lift and favorable p-family | Statistical screen may pass; `research_edge` must remain false |
| Trusted-time authority reuses a declared issuer/signer/custodian/generator ID | Reject |
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

A. Define typed receipt schema and strict parser.  
B. Implement byte-level source verifier and signature verification.  
C. Implement trusted-time and external-ledger verification.  
D. Implement identity/role/separation-of-duties policy.  
E. Bind preregistration, target list, code and candidate commitments.  
F. Bind both pre-close Exact5 seals.  
G. Remove public/caller control of authenticated reference sets.  
H. Add adversarial tests above and run full CI.  
I. Obtain independent security review and real institutional evidence before changing provenance status.

Acceptance requires all tests passing, negative tests demonstrating fail-closed behavior, reproducible verifier build, and an independent review. Passing software tests alone does not authenticate any real-world evidence.
