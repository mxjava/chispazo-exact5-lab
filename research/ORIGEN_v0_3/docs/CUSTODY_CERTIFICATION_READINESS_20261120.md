# Exact5 — Custody certification readiness dossier

Date: 2026-11-20  
Scope: Chispazo Clásico prospective prediction custody  
Status: **NOT CERTIFIED — EXTERNAL CUSTODIAN REQUIRED**  
Branch: `fix/origen-v03-integrity-guards-20261120`

## Executive determination

The repository contains a custody design and local integrity controls, but it does not contain evidence of an independently operated custody event. No claim of independent certification, trusted timestamping, external immutable retention, or a sealed prospective target is authorized by the current artifacts.

A local SHA-256, Git commit timestamp, self-entered timestamp, CI pass, or JSON field naming a custodian is not independent custody. The generator must not self-certify.

## Evidence reviewed

- `research/ORIGEN_v0_3/PROSPECTIVE_CUSTODY_SPEC_V1.md`
- `research/ORIGEN_v0_3/docs/PROSPECTIVE_CUSTODY_PROTOCOL_V1.md`
- `research/ORIGEN_v0_3/docs/PHYSICAL_EVIDENCE_ACQUISITION_PROTOCOL.md`
- `src/pipeline/freeze_prediction.py`
- `src/pipeline/evaluate_registration.py`

The prospective specification itself marks the process DESIGN / NOT YET OPERATIONAL. The protocol says it is not operationally certified.

## Gap assessment

| Control | Current evidence | Determination |
|---|---|---|
| Frozen candidate and source identity | Git commit binding and frozen-model constraints exist | Partial; must be bound into each sealed manifest |
| Input history cutoff and hash | Local preflight validates history cutoff/hash | Local integrity only |
| Prediction payload hash | Local registration computes a SHA-256 | Local integrity only |
| Independent recipient | No independently identified custodian or receipt is present | **BLOCKER** |
| Trusted time before official close | Local system timestamp is recorded; no independent timestamp token/clock evidence | **BLOCKER** |
| Custodian recomputation and attestation | No externally verifiable signature/attestation evidence | **BLOCKER** |
| Separate immutable retention | No independently controlled retention receipt/location is evidenced | **BLOCKER** |
| Append-only external anchor | Local hash chain alone has no trusted external head anchor | **BLOCKER** |
| Two witnessed dry runs | No external witness evidence supplied | **BLOCKER** |
| Prospective target ledger | No independently sealed target evidence established | **BLOCKER** |
| Predictive edge | No qualifying prospective sample | **NOT ESTABLISHED** |

## Mandatory independent custodian

Before any target can be counted, appoint a person or organization that:
1. Is not the generator and did not select or tune the candidate.
2. Has a verifiable identity and an independently controlled email/account or signing identity.
3. Receives the exact payload and manifest before the official sales close.
4. Recomputes the payload and manifest SHA-256 independently.
5. Records receipt using a trusted timestamp source independent of the generator's machine.
6. Retains byte-identical originals in storage controlled separately from the generator.
7. Issues a signed or otherwise independently verifiable receipt binding contest ID, modality, payload hash, receipt time, and custodian identity.
8. Makes the receipt and retention evidence available to an independent reviewer.

A second account controlled by the generator, a GitHub Actions job under the same owner, or a second local machine controlled by the generator does not satisfy independence.

## Required per-target custodian receipt

The custodian's signed receipt must bind at least:
- schema version;
- contest ID and `CLASSIC` modality;
- scheduled sales close, local timezone, and authoritative schedule source;
- candidate ID/version and source commit SHA;
- input history SHA-256 and maximum included contest;
- exact payload SHA-256 (and ciphertext SHA-256 if encrypted);
- generator identity;
- custodian identity;
- custodian receipt timestamp and trusted timestamp reference;
- custodian's independently recomputed hash;
- separate-retention object/version identifier;
- signature or attestation reference;
- explicit result: `ACCEPTED_PRE_CLOSE` or a specific rejection/failure code.

The signed receipt, trusted timestamp evidence, and retained payload must be independently retrievable. A string typed into the JSON by the generator is not an attestation.

## Certification acceptance sequence

1. Freeze the preregistration, candidate, dependencies, environment, score, hypothesis family, stopping rule, and failure/retry policy.
2. Appoint and verify the independent custodian and reviewer.
3. Agree on a trusted timestamp mechanism and separate append-only/version-locked retention.
4. Run two non-scored end-to-end dry runs with the actual custodian.
5. Demonstrate rejection of a one-byte mutation, late receipt, missing receipt, wrong contest/modality, duplicate registration, and invalid chain/head anchor.
6. Obtain reviewer sign-off on the dry-run evidence bundle.
7. Only then begin the prospective clock. Each target must be received and attested before its official close.
8. Keep failures and misses in the ledger; never backfill or replace a post-close prediction.

## Required evidence bundle for sign-off

- Custodian identity and independence declaration.
- Custody service/storage description and access-control evidence.
- Trusted timestamp provider/method and validation evidence.
- Two dry-run payloads, manifests, independent hash recomputations, timestamp receipts, and retention identifiers.
- Mutation/late/missing-receipt negative-test results.
- Reviewer sign-off identifying the exact commit and hashes reviewed.
- External anchor for the final append-only ledger head.

## Sign-off form (to be completed by the external parties)

- Independent custodian legal/name identity:
- Organization (if applicable):
- Independence/conflict declaration:
- Trusted timestamp method/provider:
- Separate retention system and object identifiers:
- Dry-run 1 receipt ID and payload SHA-256:
- Dry-run 2 receipt ID and payload SHA-256:
- Negative-test evidence location:
- Reviewer identity:
- Reviewed repository commit SHA:
- Reviewed protocol/spec SHA-256:
- Decision: `CERTIFIED_FOR_PROSPECTIVE_CUSTODY` / `REJECTED`
- Signature/attestation reference and timestamp:

## Current classification

**`BLOCKED_PROVENANCE` for independent prospective custody.**  
**`NO_EDGE_EVIDENCE` for predictive performance.**

This dossier closes the internal gap analysis; it does not itself certify custody. Do not mark a prediction `SEALED`, start the prospective sample counter, or claim an edge until external evidence above is obtained and independently checked.

## Scope protections

- V294 remains frozen.
- Canonical historical CSV remains byte-for-byte untouched.
- No writes to `main`, no merge, and no candidate promotion.
- Historical V325/V326 results remain exploratory and are not prospective evidence.
