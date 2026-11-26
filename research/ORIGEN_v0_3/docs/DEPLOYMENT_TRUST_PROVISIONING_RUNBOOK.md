# ORIGEN v0.3 — Deployment Trust Provisioning Runbook

Status: DESIGN / NOT EXECUTED  
Classification: RESEARCH_ONLY_NO_EDGE  
Owner: deployment operator and independent security custodian (must be named by the deploying organization)

This runbook defines the external work required before ORIGEN can move beyond
`BLOCKED_PROVENANCE`. It deliberately contains no keys, credentials, fabricated
institutional identities, or synthetic trust anchors. Completing software tests
does not complete this ceremony.

## 1. Required independent roles

The deploying organization must appoint and record, by legal/organizational
identity and verified contact channel:

1. **Trust-root authority** — controls the offline Ed25519 root key and signs
   policy envelopes.
2. **Deployment operator** — installs the pinned root public key and bootstrap
   snapshot into a deployment-controlled trust store.
3. **Independent witness** — verifies the root fingerprint through a second
   independently obtained channel and co-signs the ceremony record.
4. **Evidence custodian** — receives original physical/digital source artifacts
   and issues custody receipts. Must not be the same person who generated the
   prediction portfolio.
5. **Time-stamping authority** — supplies independently verifiable RFC 3161
   tokens, where available and contractually accepted.

No role may be filled by a test fixture, GitHub branch, CI secret controlled by
the submitting user, application request, environment variable, or receipt
claim.

## 2. Out-of-band root enrollment

Before accepting any signed policy:

- Generate the production root key in an approved offline HSM or equivalent
  controlled ceremony. Never generate it in this repository or CI.
- Record algorithm, key identifier, public-key bytes, SHA-256 fingerprint,
  creation ceremony, custody location, backup/recovery procedure, revocation
  procedure, and authorized signers.
- Have the independent witness compare the full fingerprint over a second
  authenticated channel obtained independently of the deployment operator.
- Have the deployment operator install the public-key pin into a protected
  deployment image/configuration or hardware-backed trust store inaccessible
  to the submitting user.
- Produce a signed ceremony record and preserve it with the independent
  custodian. Do not put private material in Git, issue comments, CI variables,
  or this runbook.

**Acceptance evidence:** signed enrollment record, independent fingerprint
attestation, operator installation record, key custody record, and successful
verification against a separately generated test policy that is not used as a
production trust anchor.

## 3. Policy anti-rollback state

The trust policy envelope must be signed by the enrolled root. The deployment
must persist the highest accepted policy sequence in storage that survives
process restarts and is protected from the submitting user.

- First enrollment: initialize the sequence from the witnessed ceremony record.
- Policy update: require a strictly increasing sequence and verify the root
  signature before atomically advancing the checkpoint.
- Rollback/recovery: require a separately witnessed recovery procedure; never
  lower the sequence automatically.
- Backup: replicate the checkpoint to an independently controlled recovery
  location and test restoration.

A caller-supplied integer, repository file, environment variable, process
memory, or unprotected local JSON file is not an anti-rollback control.

**Acceptance evidence:** storage threat model, access-control proof, atomic
update test, restart test, rollback rejection test, recovery drill, and witness
sign-off.

## 4. Ledger trust and consistency

For an external append-only ledger, independently enroll:

- log operator legal identity and contact;
- log ID and Ed25519 public-key fingerprint;
- signed tree-head schema/version and signature domain;
- independent witness or monitor identity and monitoring cadence;
- initial signed tree head and independently retained checkpoint;
- consistency-proof verification between every accepted checkpoint and the
  next signed tree head.

The inclusion verifier and consistency verifier in this repository are
mathematical primitives. Their Python result objects are forgeable and are not
authorization capabilities. Production control flow must verify both signed
tree heads under the externally pinned key, verify inclusion and consistency,
then atomically persist the newer checkpoint before treating the event as
accepted. A witness must independently monitor for split views.

**Acceptance evidence:** operator contract/identity, out-of-band key pin,
initial checkpoint, witness monitoring receipt, signed heads, inclusion proofs,
consistency proofs, persistent checkpoint tests, and split-view incident plan.

## 5. Trusted time

Where RFC 3161 is required:

- select a TSA whose identity, certificate chain, policy OID, revocation
  handling, and accepted algorithms have been independently reviewed;
- validate the complete timestamp token and message imprint against the exact
  artifact digest;
- validate certificate path, EKU, policy, validity interval, revocation status,
  and trusted time source;
- preserve original token bytes and validation evidence;
- reject caller-supplied timestamps as a substitute for TSA evidence.

**Acceptance evidence:** TSA policy and identity, original RFC 3161 token bytes,
validation report, certificate/revocation material, and independent review.

## 6. Physical evidence and custody

For each Chispazo contest, preserve original bytes and metadata for available
primary records, including as applicable. The intake record must bind the
contest ID, local draw date, modality, scheduled sales-close slot and actual
draw-event time separately:

- official draw act/minutes and signed result records;
- original recording and acquisition metadata;
- signed machine/ball inventory, weighing and calibration records, if made
  available by the responsible authority;
- signed participation, cancellation, incident and exception records;
- acquisition time, source identity, chain-of-custody transfers and storage
  receipts.

Do not infer missing documents, substitute a screenshot for an original when
the original is required, or describe a public result page as physical evidence.
Keep the official modalities separate:
- **De las Tres** is the 15:00 Mexico City slot.
- **Clásico** is the 21:00 Mexico City slot and is the only modality eligible
  for the preregistered prospective EDGE_SUPPORTED sample.
- The V2 structural manifest requires the nightly MJF transaction file and
  printed signature form for Clásico only. Do not demand or fabricate those
  nightly artifacts for De las Tres; preserve its daytime participation /
  cancellation signature-reconciliation records instead.
- Never infer modality from contest-number order alone. Bind each artifact to
  the exact contest ID and corroborate the modality from the official schedule
  and draw-specific official record.
The official product schedule and SGVO-PRO-05 Rev. 39 are the current public
sources for this separation; their procedural text does not prove that any
specific draw's primary records were actually produced or preserved.

**Acceptance evidence:** original source bytes, cryptographic digests computed
at acquisition, signed custodian receipt, independent acquisition witness,
contest binding, and discrepancy log.

## 7. Two pre-close output seals

Before any target draw closes, freeze the preregistration, code/environment
commitments, candidate portfolio, and output format. Produce two independently
controlled pre-close seals with:

- target contest ID and explicit Clásico modality;
- portfolio bytes and SHA-256;
- generator identity/build commitment;
- creation time backed by validated trusted-time evidence;
- independent signature and timestamp token;
- independent custody/ledger inclusion.

The seals must be demonstrably created before the official sales close. For
the prospective edge study, the target must be an explicitly identified
21:00 Clásico contest; a 15:00 De las Tres result cannot count toward the
100-draw Classic threshold. A later reconstruction, edited timestamp, or
post-result upload does not qualify.

## 8. Go/no-go gates

All gates are conjunctive. Missing or failed evidence leaves the public adapter
at `BLOCKED_PROVENANCE`:

- [ ] Named and independently authenticated trust-root authority
- [ ] Offline root enrollment and independent fingerprint witness
- [ ] Deployment-owned protected key pin
- [ ] Persistent monotonic policy sequence with rollback/recovery tests
- [ ] Authenticated ledger operator and externally pinned log key
- [ ] Two signed tree heads, inclusion proofs, consistency proof and persistent
      checkpoint, independently witnessed
- [ ] Validated RFC 3161 TSA tokens
- [ ] Original physical evidence and independent custody receipt
- [ ] Two sealed pre-close outputs for each scored target
- [ ] Exact contest/modality binding and intact hashes; only 21:00 Clásico
      contests count toward the prospective edge acceptance sample
- [ ] Independent security review and signed go/no-go decision

Passing these gates only establishes provenance readiness. It does not establish
predictive edge. `EDGE_SUPPORTED` still requires at least 100 intact prospective
Classic draws, preregistered positive lift, Holm-adjusted p < 0.05, anytime
e-value >= 20, two sealed pre-close outputs, clean hashes, and authentic
independent custody.

## 9. Current state

As of 2026-11-26, this ceremony has **not** been executed. No institutional
root, TSA, ledger operator, witness, custodian, physical primary record, or
deployment-owned monotonic store is claimed as provisioned. This runbook is an
execution specification, not evidence of completion.
