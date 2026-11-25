# ORIGEN v1 — policy-envelope / receipt-attestation composition

**Status:** research-only cryptographic composition; not an independent-provenance verifier  
**Date:** 2026-11-25  
**Parent:** PR #41 head cf77070c7244279083b32b98e9d85c541475a57e

## What was added

The new trust_chain_v1.py composes the two existing primitives in one ordered path:

1. Verify the signed trust-policy envelope against the deployment-supplied Ed25519 root key, expected root key ID, minimum policy sequence, and verification time.
2. Pass only the resulting VerifiedTrustPolicy.policy into verify_receipt_attestation.
3. Return a scoped VerifiedReceiptTrustChain that binds the exact policy-envelope and receipt byte digests.

The composition snapshots the caller-supplied timezone offset exactly once and passes one normalized UTC instant to both verifiers. Without that boundary, a stateful tzinfo object could return one offset to the policy verifier and a different offset to the receipt verifier. The new adversarial test demonstrates the attack and verifies the single-snapshot behavior.

## What this does not prove

The caller still supplies the root public key, root key ID, minimum sequence, and clock. The code cannot prove who provisioned those values or that the minimum sequence is stored durably outside the caller's control. A valid result means only that:

- the policy envelope signature matches the supplied root key;
- the envelope key ID matches the supplied expected key ID;
- the policy sequence meets the supplied floor;
- the envelope validity checks pass at the supplied time;
- the receipt root attestation verifies under the issuer key contained in that verified policy;
- the policy version in the receipt matches the signed policy envelope.

It does **not** authenticate the physical artifact bytes referenced by the receipt, nested signer or custodian signatures, institutional roles, certificate status, RFC 3161 timestamp tokens, external ledger inclusion/consistency, legal identity, machine/sphere continuity, or independent custody.

VerifiedReceiptTrustChain is a diagnostic result, not an authorization capability. Python objects are not unforgeable security tokens. No downstream eligibility code may rely on the type alone.

## Fail-closed adapter boundary

verify_independent_provenance(original_receipt_bytes) is deliberately unchanged. It still accepts only the original receipt bytes and always returns BLOCKED_PROVENANCE while the independent trust backend is unprovisioned. It does not accept a caller-provided VerifiedTrustPolicy, policy object, key map, callback, or verification result.

A valid synthetic policy/receipt chain is explicitly tested to leave the adapter blocked. No AUTHENTICATED status was added. This composition is not wired into production eligibility and does not change BLOCKED / RESEARCH_ONLY_NO_EDGE.

## Provisioning contract required before any future adapter integration

### 1. Root trust anchor

The 32-byte Ed25519 root public key and key identifier must be obtained through an independently controlled key ceremony, not from the policy envelope or the evidence submitter. The deployment record should include:

- the exact public-key bytes and independently computed fingerprint;
- the key identifier, purpose, validity, and approved trust domain;
- the ceremony record, approvers, dual-control evidence, and effective time;
- the source and integrity of the immutable deployment configuration;
- the authorized rollover/revocation procedure.

A suitable design is an offline root whose public-key pin is delivered through a reviewed, signed deployment artifact or measured immutable configuration, with two-person approval for initial provisioning and rotation. The repository contains no real institutional root and no verified Lotería Nacional or SEGOB public-key pin. Do not substitute a synthetic test key.

### 2. Anti-rollback state

The minimum accepted policy sequence must be read from durable state outside the downloaded envelope and outside the submitting caller's control. The state record should bind at least:

- trust-domain identifier and root-key identifier;
- highest accepted policy sequence;
- exact accepted envelope SHA-256;
- acceptance event identifier and trusted acceptance time;
- previous state digest or append-only ledger position.

Acceptance must use an atomic compare-and-swap or equivalent monotonic transaction. A process restart, local cache deletion, restored VM snapshot, stale backup, or repository checkout must not lower the floor. Recovery and root rollover require dual control and an auditable transition. No such store is currently provisioned by this repository.

### 3. Time

The composition accepts a caller-supplied datetime. Normalizing it to UTC does not authenticate it. A production verifier needs a trusted time source or verified RFC 3161 token bytes, including TSA signature/path validation, policy constraints, message-imprint equality to the exact artifact bytes, certificate validity/revocation checks, and the TSA's genTime. A parseable timestamp string or local wall clock is insufficient.

## External evidence interfaces still required

The official Lotería Nacional Normateca's current “Normas Sustantivas Vigentes” index lists SGVO-PRO-05, Procedimiento Sorteos Electrónicos, with last update 20-Mar-2026. The linked current PDF identifies itself as revision 38. Separately, the Normateca's “Proyectos Normativos” historical index lists a project file `sgvo_pro_05p.pdf` for 23-Feb-2026 to 04-Mar-2026; a project listing is not evidence that revision 39 became effective. Therefore this repository treats revision 38 as the currently published procedure and revision 39 as unconfirmed / project-only unless Lotería Nacional publishes an effective version. The existing OFFICIAL_PROCEDURE_RECONCILIATION_20261123_1451.md records the draw-specific artifact matrix and the 15:00 / 21:00 modality separation; its revision-specific measurements and policies must be revalidated against the current revision-38 PDF before operational use. The procedure identifies electronic signatures, signed reports, Acta, CS-11, Sumario, Tira de Pesaje, participation/cancellation files, and OIC custody. It does not publish a cryptographic algorithm, public verification key, certificate chain, or public trust-anchor provisioning procedure. Therefore its reference to “Firma Electrónica” must not be treated as an Ed25519 signature or as a verifiable public PKI root.

The next external interfaces must consume original bytes, not URLs or caller-declared hashes:

1. **Institutional detached signatures:** exact source bytes, exact detached signature bytes, signer certificate/key material, signature algorithm and parameters, signer role authorization, key validity/revocation evidence, and the authoritative trust chain. Reject if the institution cannot supply the verification material or the cryptographic semantics.
2. **RFC 3161:** original DER token bytes; exact SHA-256 message imprint; verified TSA signature and certificate path; accepted policy OID; genTime; and revocation status. Bind each token to one exact artifact digest and one event.
3. **External ledger:** signed checkpoint/head, inclusion proof, consistency proof from a previously pinned head, monotonic sequence, and independent key. A ledger ID, entry ID, or proof digest string alone is not verification.
4. **Custody:** original signed hand-off/receipt bytes, stable event IDs, predecessor linkage, item digest and byte length, named legal entities, role authority, trusted event time, and independent evidence that the custodian is not the generator or submitter.
5. **Physical source package:** original Acta and annex bytes; CS-11; Sumario/cierre de venta; original Tira de Pesaje and 28 readings; scale and calibration records; machine/set/sphere identifiers; official recording; and the original signed participation/cancellation archive with its pre-draw custody trail.

Each interface needs synthetic adversarial fixtures clearly labelled TEST ONLY, plus at least one real independently supplied verification vector before any claim of institutional verification. A synthetic signature that verifies under a test key proves only the software path.

## Validation

The isolated workflow runs:

    python -m unittest discover -s tests -v

The repository workflow also runs python -m compileall -q src and pytest -q.

The tests use newly generated synthetic Ed25519 root and issuer keys. They cover policy tampering, wrong root, rollback floor, receipt tampering, policy-version mismatch, stateful timezone behavior, exact-byte boundaries, and the invariant that a valid chain does not unblock verify_independent_provenance.

## Decision

The composition is a research-only cryptographic link, not a completed trust boundary. Keep PRs draft and unmerged. Keep V294 frozen, canonical history byte-identical, main untouched, and production BLOCKED / RESEARCH_ONLY_NO_EDGE.
