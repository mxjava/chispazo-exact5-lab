# ORIGEN — signed policy/root-attestation integration review

**Date:** 2026-11-24  
**Branch:** `research/origen-signed-root-chain-review-20261124`  
**Base:** PR #41 exact head `cf77070c7244279083b32b98e9d85c541475a57e`  
**Classification:** RESEARCH ONLY — production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## What was audited

The current primitives have deliberately separate scopes:

1. `verify_signed_trust_policy()` validates an Ed25519 policy envelope against a caller-supplied root public key, key ID, minimum sequence, and verification time. It returns `VerifiedTrustPolicy`.
2. `verify_receipt_attestation()` accepts a `TrustPolicy` and verifies the receipt's root Ed25519 attestation. It returns `CryptographicallyVerifiedReceipt`.
3. `verify_independent_provenance()` accepts only original receipt bytes and unconditionally returns `BLOCKED_PROVENANCE`. It does not call either cryptographic primitive.

The first two primitives are composable, but the caller currently has to perform the composition and can accidentally overstate the result. The third boundary correctly has no route to an authenticated state.

## Integration added in this branch

`src/origen/trust_policy_integration_v1.py` adds the research-only function
`inspect_signed_root_attestation_chain()`.

- It accepts original receipt bytes and signed policy-envelope bytes, not a caller-constructed `VerifiedTrustPolicy`.
- It re-verifies the policy envelope against the separately supplied anchor and sequence floor.
- It passes the resulting `VerifiedTrustPolicy.policy` directly to `verify_receipt_attestation()`.
- It calls the existing `verify_independent_provenance()` boundary after both signature checks.
- It returns a diagnostic object that records the two narrow signature results and the receipt/policy digests, while its provenance status remains exactly `BLOCKED_PROVENANCE`.
- The diagnostic explicitly labels the root anchor and anti-rollback floor as caller-supplied and unauthenticated.

This is not a production integration. It is an executable proof of composition and of the non-promotion invariant. No caller-provided callbacks, key maps, booleans, or pre-constructed policy objects are accepted by the inspector.

## Required out-of-band provisioning before any future activation

### 1. Institutional authority and identity

Obtain a signed designation from the competent Lotería Nacional/SEGOB authority identifying:
- the policy-root owner and its legal/operational authority;
- the independent verifier and each permitted receipt-signing role;
- the accountable key custodians and revocation authority;
- the exact document classes and draw processes within each role's scope.

Verify the designation through an independently obtained institutional contact channel. A name, email, PDF logo, web page, or self-declared issuer ID is not proof of authority.

### 2. Root-key ceremony and publication

The institutional authority—not this repository or the model operator—must generate and retain the Ed25519 root private key under documented dual control. Preserve signed ceremony minutes, custody identities, device/HSM evidence, key fingerprint, key ID, algorithm, activation time, expiry, permitted roles, and emergency-revocation procedure.

Publish the root public key and its fingerprint through at least two independently authenticated institutional channels. A key delivered only inside the policy envelope, in a Git commit, or by the same operator who supplies the receipt is not an external trust anchor.

The deployment must pin the exact 32-byte public key and key ID in reviewed, access-controlled configuration separate from the downloaded envelope and receipt. Pin changes require independent approval and an auditable change record.

### 3. Anti-rollback state

The minimum accepted policy sequence must come from durable monotonic state outside the envelope and outside the caller's request. Suitable deployment candidates require a separate security review; examples include a hardware-backed monotonic facility or an independently administered append-only service with authenticated head anchoring.

Required semantics:
- read the last accepted sequence from the protected store at verification time;
- reject if the store is unavailable, corrupt, rolled back, or inconsistent across verifier replicas;
- require the candidate sequence to be at least the stored floor;
- persist the newly accepted sequence with an atomic compare-and-swap before reporting policy acceptance;
- never lower the floor during restore, failover, backup recovery, or key rotation;
- record the envelope hash, old/new sequence, verifier identity, and approval trail.

An environment variable, command-line flag, local JSON file, database snapshot without rollback protection, or caller argument is not an anti-rollback mechanism.

### 4. Time and revocation freshness

The current APIs receive `verification_time` from the caller. It is not trusted time. Production needs an independently authenticated time source and verification of the actual RFC 3161 token, TSA certificate chain, policy, imprint, nonce (where required), and token chronology. A local wall clock or an unverified timestamp string cannot establish pre-close timing.

Policy expiry does not solve revocation freshness. Define a bounded refresh interval, authenticated revocation distribution, emergency revocation path, and fail-closed behavior when freshness cannot be established.

### 5. Rotation and incident handling

Use an independently witnessed root-rotation ceremony. Require an authenticated transition linking old and new roots, overlap windows, explicit sequence advancement, and a rollback-resistant deployment update. Emergency compromise must invalidate the affected root and subordinate keys through an independently distributed revocation event. Retain prior policies and revocation evidence for historical verification without allowing their reuse for new receipts.

## Future end-to-end gate order

No single root signature is sufficient. A future independently reviewed adapter must, in order:

1. obtain original bytes from independently controlled, immutable acquisition storage;
2. obtain the pinned institutional root and monotonic sequence state from the deployment trust boundary;
3. verify the signed policy envelope and its freshness;
4. verify the root receipt attestation under that verified policy;
5. verify every nested signer and custodian signature, role, identity, key validity and revocation state;
6. verify actual RFC 3161 tokens and the official draw-close reference;
7. verify external ledger inclusion and independently anchored ledger-head continuity;
8. hash and validate the original physical artifacts (including signed weighing strip, 28 sphere identities/masses, mapping, calibration, act, incident record and original audiovisual evidence);
9. independently verify two distinct pre-close output seals and their custody receipts;
10. only then evaluate the separately preregistered prospective statistical protocol.

Any missing, stale, ambiguous, unavailable, or contradictory dependency must remain blocked. A valid signature over a claim does not prove that the claimed physical event occurred.

## Adversarial test coverage added

`tests/test_trust_policy_integration_v1.py` uses generated synthetic Ed25519 keys only. It checks:
- valid policy signature followed by valid receipt signature;
- tampered receipt claims rejected at the receipt-signature layer;
- wrong root anchor rejected;
- external minimum sequence rejects rollback;
- expired policy rejected before receipt verification;
- a caller-constructed policy object is not an accepted input;
- successful cryptographic composition still leaves `verify_independent_provenance()` at `BLOCKED_PROVENANCE`.

Synthetic fixtures are not institutional identities, production roots, trusted clocks, TSA tokens, or custody evidence.

## Institutional-source check (2026-11-24)

The public Lotería Nacional Normateca exposes `SGVO-PRO-05`, revision 39. It is an institutional procedure source and describes the draw recording process from sphere weighing through the electronic draw. It is relevant to the physical evidence inventory, but it does not publish an Ed25519 trust root, a policy-root key ID, an authenticated issuer-key registry, or an external anti-rollback service:

- https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

The official text of Mexico's Ley de Firma Electrónica Avanzada describes certificate fields and issuance/revocation procedures. That establishes a legal framework for digital certificates, not a specific Lotería Nacional certificate or authorization binding the ORIGEN receipt-signing roles. No certificate chain or public key for the required draw-evidence issuer was found in this check:

- https://sidof.segob.gob.mx/notas/docFuente/5228864

Therefore no institutional trust anchor was provisioned or embedded. The synthetic test root must never be reused.

## Official Chispazo status check (2026-11-24 17:55 America/Mexico_City)

- The dedicated official results page publishes draw 12393 dated 24-Nov-2026 as `01 07 08 09 12`.
- The official game page defines De las Tres at 15:00 and Clásico at 21:00. Draw 12393 is schedule-consistent with the 15:00 De las Tres slot, but the current public mask index does not yet list a 24-Nov mask; retain modality as schedule-derived until a mask explicitly labels it.
- The official home index advertises draw 12394 for 24-Nov-2026 at 21:00; the official results extract still shows its winning-number field blank at this observation time. Do not infer or backfill a Classic result.
- The public mask index's newest listed date is 23-Nov-2026. No original 24-Nov PDF bytes or SHA-256 were acquired in this check.
- No signed act, CS-11, original weighing strip, 28 individual sphere masses, calibration certificate, machine/set identity package, original recording, independent custodian receipt, trusted timestamp token, or pre-close seal was obtained.

Official public pages checked:
- https://www.loterianacional.gob.mx/Chispazo/Resultados
- https://www.loterianacional.gob.mx/Chispazo/Chispazo
- https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- https://www.loterianacional.gob.mx/Home/Resultados
- https://www.loterianacional.gob.mx/home/index

This is a public-result/status reconciliation, not new primary physical evidence. It is not eligible for physical provenance, prospective OOS scoring, or edge claims.

## Invariants

- PR #13 remains separate and untouched by this branch.
- PR #40 and #41 remain draft; no merge or promotion.
- No writes to `main`.
- V294 remains frozen.
- `data/history/Chispazo_through_12249.csv` is not modified.
- Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
