# ORIGEN v0.3 — deployment trust provider and atomic sequence boundary v1

**Classification:** executable interface contract / RESEARCH ONLY. No production provider, institutional trust anchor, or authenticated clock is implemented here.

## 1. Why this increment exists

The V3 verifier at PR #81 re-verifies exact policy and receipt bytes, but still receives the root pin, key ID, minimum sequence, and clock as individual call arguments. PR #69 and PR #56 already define the out-of-band bootstrap and anti-rollback requirements. This increment turns the required handoff into an executable application interface rather than repeating the provisioning design.

New module:

- `src/origen/deployment_trust_provider_v1.py`

New adversarial suite:

- `tests/test_deployment_trust_provider_v1.py`

The module deliberately ships no file-backed, SQLite, environment-variable, or in-memory production provider.

## 2. One provider snapshot, not request-level trust inputs

The high-level function accepts exact receipt bytes, exact signed policy-envelope bytes, and one provider dependency:

```python
inspect_receipt_with_deployment_trust_provider(
    original_receipt_bytes,
    signed_policy_envelope_bytes,
    provider=deployment_composition_root_provider,
)
```

The provider returns one immutable snapshot containing:

- root public-key bytes, root key ID, and root generation;
- fixed CLASSIC policy domain;
- minimum sequence, accepted sequence, exact accepted-envelope digest, latest persisted trusted-time interval upper bound, and state generation;
- one normalized UTC time, its uncertainty, and a provisioned maximum uncertainty;
- a source-issued clock sample ID and validity deadline, plus a provisioned maximum sample age;
- the exact canonical signed clock-sample envelope bytes, its 32-byte Ed25519 verification key, and the provisioned clock-key ID;
- identifiers for the clock source and state backend;
- the provisioning-record digest;
- a locally computed canonical trust-configuration SHA-256 binding the policy domain, root-key fingerprint/ID/generation, minimum sequence, maximum clock uncertainty and maximum sample age, clock-source ID, clock-key ID/fingerprint, backend ID, and provisioning-record digest;
- a locally computed clock-sample SHA-256 over the exact signed envelope bytes; the envelope signature binds the source ID, sample ID, exact UTC instant, uncertainty, validity deadline, CLASSIC domain, and clock-key ID.

The application request cannot independently override those values. The snapshot is copied and strictly type-checked before verification. A boolean is not accepted as an integer sequence or generation.

The provider object is a trusted dependency supplied by the deployment composition root. Python Protocols and frozen dataclasses are not unforgeable capabilities; this module does not authenticate an arbitrary provider implementation.

## 3. Verification and state transition

The operation is ordered as follows:

1. Read exactly one provider snapshot for the fixed CLASSIC domain.
2. Reject malformed pins, identifiers, generations, sequence state, digest state, clock metadata, or provisioning-record digest.
3. Reject clock uncertainty above the provider's provisioned maximum.
4. Compute the closed uncertainty interval `[trusted_time - uncertainty, trusted_time + uncertainty]`.
5. Verify the exact canonical V3 policy envelope against the snapshot root pin, root key ID, CLASSIC domain, and the maximum of the provisioned floor and previously accepted sequence.
6. Reject equal-sequence/different-envelope-digest equivocation.
7. Verify the exact receipt bytes under the policy just verified.
8. Require the complete clock uncertainty interval to lie inside the signed policy validity interval and the receipt issuer-key validity interval. Require the receipt signing time to be no later than the earliest possible verification instant.
9. Re-run the exact-byte V3 policy and receipt verification at `verify_independent_provenance`. That gate must still return exactly `BLOCKED_PROVENANCE`.
10. Compute canonical trust-configuration and clock-sample digests from the validated snapshot.
11. Atomically compare-and-advance the provider state using the exact snapshot generation, both digests, root generation, policy sequence, envelope digest, accepted time, and uncertainty. The provider must recompute the configuration digest from its authoritative configuration and the sample digest from its current authenticated clock sample inside the same transaction.
12. Return a diagnostic inspection with the exact byte hashes, both digests, sample lease deadline, and before/after state generations. Its provenance status remains `BLOCKED_PROVENANCE`.

No state commit is attempted when policy signature, receipt signature, clock-sample signature, role authorization, time-window, or independent-boundary verification fails.

## 4. Required provider transaction semantics

The external implementation must provide a linearizable compare-and-advance transaction:

| Observed state vs candidate | Required outcome |
|---|---|
| Higher candidate sequence | Advance exactly one state generation |
| Same sequence + same exact envelope digest and unchanged time watermark | IDEMPOTENT; generation unchanged |
| Same sequence + same exact envelope digest and a later disjoint time interval | Persist the new time watermark; increment one generation; return TIME_ADVANCED |
| Same sequence + different digest | Reject as equivocation |
| Lower sequence | Reject as rollback |
| Snapshot generation changed before commit | Reject as conflict |
| Store unavailable, stale, restored, split-brain, or commit uncertain | Fail closed |

The provider must scope state by root generation and policy domain. A policy sequence from another domain must never satisfy the CLASSIC floor. Root rotation must be a separate, independently authorized transition and cannot reset the sequence.

For every inspection, including same-sequence/same-digest reads, the application rejects a candidate trusted-time interval whose earliest instant precedes the persisted `trusted_time_latest_utc` watermark. The provider must enforce that same floor atomically inside compare-and-advance; checking only the application snapshot is insufficient because another inspection may advance the watermark after the snapshot was read. Candidate earliest time is `accepted_at_utc - clock_uncertainty`; candidate latest time is `accepted_at_utc + clock_uncertainty`.

For a higher sequence, the provider stores the candidate sequence, exact envelope digest, and candidate latest time in one generation. For the same sequence and digest, a later disjoint interval advances only the time watermark and state generation, returning `TIME_ADVANCED`. If the candidate latest time equals the stored watermark, the provider returns `IDEMPOTENT` without changing the generation. Any interval whose earliest instant precedes the stored watermark returns `TIME_ROLLBACK`. This ensures that a later idempotent inspection cannot be followed by a clock restored to an earlier instant while remaining above only the original policy-acceptance time. The commit response must echo the exact persisted watermark. A provider that restores or regresses this clock floor must fail closed.

The application checks the returned commit shape and exact policy digest, but only the provider's independently reviewed implementation can guarantee linearizability and durable anti-rollback.

### Trust-configuration binding

The application computes `trust_configuration_sha256` as SHA-256 over canonical JSON with the fixed schema identifier `origen.deployment-trust-configuration.v1` and these fields: policy domain, SHA-256 of the exact root public-key bytes, root key ID, root generation, minimum policy sequence, maximum clock uncertainty, clock-source identifier, clock sample key ID, SHA-256 of the exact clock sample verification key, state-backend identifier, and provisioning-record digest.

The provider must independently recompute this value from its authoritative provisioned configuration and compare it atomically with the supplied expected digest and `expected_state_generation`. This detects root-key or provisioning/clock/backend configuration drift that reuses the same key ID, root generation, or state generation. The digest is a consistency binding, not proof that the provisioning record, clock, backend, or root is authentic. A provider that trusts the caller-supplied digest without recomputation does not satisfy the contract.

### Provider clock-sample binding

The `origen.clock-sample-attestation.v1` envelope is canonical ASCII JSON with exact fields for the CLASSIC domain, clock-source ID, sample ID, sampled UTC instant, uncertainty in milliseconds, lease deadline, clock-key ID, and Ed25519 signature. The application verifies the signature over the canonical claims (excluding the signature object) with the domain separator `ORIGEN_CLOCK_SAMPLE_V1\x00`. Duplicate JSON keys, unknown/missing fields, non-canonical bytes/base64, unsupported schema/domain, source/key/sample mismatch, timestamp mismatch, and invalid signatures are rejected. `clock_sample_sha256` is SHA-256 of the exact signed envelope bytes, not a reconstructed descriptor.

The provider must independently obtain the authoritative current source sample, validate its signature under its independently provisioned clock key and source policy, recompute this digest, and compare it with `expected_clock_sample_sha256` inside the same linearizable CAS transaction. It must also reject a sample whose lease has expired at commit time, whose validity deadline is older than the complete uncertainty interval, or whose lifetime exceeds the provisioned maximum sample age. A changed sample between read and commit returns conflict and must not advance sequence or time state. The sample ID must be unique within the clock source's replay domain.

This closes the application-level gap where unsigned sample metadata could be substituted without cryptographic detection. It still does not authenticate who provisioned the clock key or establish institutional identity, source freshness, or independent clock operation; all sample keys and leases in tests are synthetic.

## 5. Trusted-time uncertainty

The prior V3 verifier checked policy validity at one supplied instant. This provider interface carries the clock's stated uncertainty and requires the entire possible-time interval to fit within:

- policy issuance and activation boundaries;
- policy expiration;
- receipt issuer-key validity;
- receipt-signing-before-verification ordering.

A midpoint that is valid while either edge of the uncertainty interval crosses activation, expiry, or key validity is rejected.

This check is only as trustworthy as the provider's clock source and uncertainty claim. The code does not establish NTS, hardware clock attestation, RFC 3161, or institutional synchronization.

## 6. What is intentionally absent

No provider implementation is included. In particular, there is no:

- accepted institutional root or verified bootstrap ceremony;
- HSM/TPM/remote monotonic store;
- protection against privileged administrator rollback or restoration of provider storage;
- institutional provisioning and independent authorization of the clock verification key, a live authenticated freshness-lease service, or proof that the provider's clock source is independent of the application;
- verified OCSP/CRL client;
- root-rotation authority;
- institutional delegation for Chispazo records;
- original draw evidence or independent physical custody.

The Incode PSC material remains a public-metadata candidate only; certificate bytes, fingerprints, current revocation, live TSA response, and deployment authorization have not been verified. Do not configure its published OID or certificate names as trusted values from this repository.

## 7. Adversarial tests

All keys, receipts, envelopes, provider state, and time sources in this test module are synthetic. Tests cover:

- successful sequence advance while remaining blocked;
- exact same-sequence/digest idempotency when the persisted time watermark is unchanged;
- same-sequence/digest time-watermark advancement and subsequent clock-rollback rejection;
- same-sequence/different-digest equivocation;
- rollback below accepted sequence;
- compare-and-swap generation race;
- trusted-clock interval rollback behind the last accepted upper bound;
- missing prior accepted-time state, clock-floor race and commit-response time-bound substitution;
- provider read and durable commit outages;
- receipt tampering before state advancement;
- clock uncertainty crossing activation, expiration, and receipt-signing order;
- uncertainty exceeding the provisioned maximum;
- clock-sample signature tampering, wrong key/source/domain, duplicate JSON keys, non-canonical envelope bytes, expired/over-age or uncertainty-crossing leases;
- a sample lease that expires between snapshot read and CAS;
- clock sample ID/time/uncertainty/lease drift between snapshot read and CAS;
- boolean sequence values, wrong modality domain, noncanonical UTC and malformed provisioning digest;
- provider commit digest substitution.

These tests exercise the application contract and a synthetic reference provider only. They do not prove that any real external service meets the contract.

## 8. Non-promotion

V294 remains frozen. The canonical history file is not changed. PR #13 remains isolated and untouched. No write to `main`, merge, or production promotion is performed.

Every successful call returns `BLOCKED_PROVENANCE`. Production remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`

No `EDGE_SUPPORTED` claim is possible without the full prospective Classic sample, preregistered positive lift, Holm threshold, anytime e-value, two pre-close seals, clean hashes, and authentic independent custody.


### Root-policy authorization of the clock-signing key

The signed V3 trust-policy envelope must contain exactly one issuer-key entry matching the clock source ID and clock key ID. Its public key bytes must equal the snapshot key, the key must not be revoked, its validity interval must contain the complete trusted-time uncertainty interval, and its root-signed authorization matrix must grant role `TRUSTED_TIME_AUTHORITY` for artifact type `CLOCK_SAMPLE`. Missing, duplicate, revoked, expired, or differently pinned clock keys fail before receipt verification or CAS. This is authorization relative to the deployment root pin supplied by the provider; it does not establish that the root pin itself was provisioned institutionally. Test clock keys are synthetic.


## 9. Composition with nested physical evidence — research-only boundary

The custody/RFC 3161/Merkle-ledger/witness composition now invokes
`verify_independent_provenance` **after** the nested physical signatures,
custody signature timestamp, policy-envelope timestamp, ledger inclusion and
checkpoint continuity, and witness-batch checks have succeeded. It passes the
same exact original receipt bytes and signed V3 policy-envelope bytes, together
with the same root pin, root key ID, sequence floor and one normalized UTC
instant. The boundary re-verifies the raw policy and receipt bytes itself; no
`VerifiedTrustPolicyV3`, receipt-verifier result, or boolean is passed across
that boundary. A non-enum status, any status other than
`BLOCKED_PROVENANCE`, or a boundary verification error aborts the composition.

This closes an orchestration gap: the evidence-composition function previously
returned a hard-coded blocked enum after its sub-verifiers but did not actually
re-enter the independent provenance boundary. The returned diagnostic now
records the exact boundary status separately.

**Important limitation:** this composition-level recheck still receives its
root pin, root key ID, sequence floor and verification time as call inputs. It
does not consume the `DeploymentTrustProvider` snapshot described above, and
it does not authenticate the TSA, transparency-log or witness-registry roots.
Those pins remain research inputs. The separate
`inspect_receipt_with_deployment_trust_provider` path authenticates the V3
policy/receipt relative to a provider-supplied snapshot and checks its CAS
contract, but it does not yet orchestrate the complete physical-evidence
bundle. Neither path supplies a production provider or institutional trust.

The next integration boundary must be a single reviewed composition root that
obtains the policy root, clock, monotonic state, TSA trust, log trust and witness
registry trust from independently provisioned services; verifies the exact
receipt, physical artifact bytes, nested signatures, RFC 3161 tokens, ledger
proofs and witness observations against those same immutable trust inputs; and
performs the required atomic state transition without accepting caller-created
verification results. The deployment provisioning and anti-rollback contract
in Sections 2–4 remains mandatory. No caller-supplied root, floor, clock,
callback, verifier result or repository file is an acceptable production
substitute.

## 10. Single-snapshot composition with provider-owned physical trust context

PR #96 extends the deployment snapshot and the provider-owned
\`PhysicalTrustContextV1\` into one fail-closed composition:

\`\`\`python
inspect_custody_ledger_witness_with_deployment_provider_v1(
    original_receipt_bytes,
    signed_policy_envelope_bytes,
    custody_record_bytes,
    portfolio_bytes,
    custody_signature_bytes,
    custodian_key_id,
    timestamp_token_der,
    policy_timestamp_token_der,
    # exact manifest, artifact, ledger and witness bytes
    provider=deployment_composition_root_provider,
)
\`\`\`

The request API intentionally has no policy root, root key ID, policy sequence
floor, verification time, TSA certificate, TSA OID, transparency-log key,
witness-registry key, or external checkpoint/registry floor arguments.

The provider returns two exact immutable objects:

- \`DeploymentTrustSnapshot\`: CLASSIC policy root, root generation, policy
  bootstrap floor, accepted policy sequence/digest, signed clock sample,
  time uncertainty/watermark and state backend metadata.
- \`PhysicalTrustContextV1\`: policy-TSA root certificate and OID, custody-TSA
  root certificate, transparency-log key/IDs/minimum tree size, witness
  registry root/IDs/minimum sequence, plus the policy root/key ID/bootstrap
  floor to which that context is intended to belong.

The snapshot also carries \`physical_trust_context_generation\` and
\`physical_trust_context_sha256\`. The latter is the canonical SHA-256 of every
context pin/floor and its generation. Both fields are included in
\`_trust_configuration_sha256\`; the provider's atomic
\`compare_and_advance\` must recompute that digest from authoritative state
inside the same transaction as the policy/time CAS.

The application order is:

1. Read one CLASSIC deployment snapshot and copy/validate it.
2. Read one physical trust context. Require its exact type, positive generation
   and canonical digest to match the snapshot's context generation/digest.
3. Require the context policy root bytes, root key ID and bootstrap policy
   floor to equal the deployment snapshot. A mismatch fails before receipt or
   physical evidence processing.
4. Verify the exact V3 policy under the snapshot root and the effective floor
   \`max(minimum_policy_sequence, accepted_policy_sequence)\`. Verify the signed
   clock sample and root authorization of its exact key.
5. Enforce the persisted time watermark, verify the exact receipt attestation,
   and require the entire trusted-time uncertainty interval to fit the policy
   and receipt-key validity windows.
6. Require every physical and custody signer key used by the exact manifest to
   be non-revoked and valid throughout the full uncertainty interval.
7. Run the full custody, nested-signature, both RFC 3161, manifest, ledger
   inclusion/consistency and witness composition using the same snapshot root,
   effective policy floor and trusted-time midpoint, plus the exact
   provider-owned physical trust context.
8. Re-enter the independent receipt/provenance boundary with the same cached
   deployment snapshot. Only after the full evidence chain succeeds may the
   provider CAS execute.
9. Validate that the returned commit binds the same policy digest, root
   generation, trust-configuration digest, clock-sample digest and physical
   context generation/digest.

The provider must make the context digest/generation part of its authoritative
trust-configuration compare-and-advance. If the context changes between read
and commit, the expected configuration digest must conflict and no successful
inspection is returned. Synthetic adversarial tests cover context digest
mismatch, root mismatch, generation drift before CAS, missing context, nested
signature failure, missing witness checkpoint, clock/root failures and CAS
races.

The physical context is still provider-owned metadata, not an independently
signed institutional authorization. The provider implementation and its
provisioning remain deployment dependencies. Certificate bytes and hashes
can be checked for internal consistency, but this library does not establish
that a listed TSA was used by Lotería Nacional, that its chain is currently
unrevoked, or that the log/registry roots are institutionally delegated.

All successful results remain exact \`BLOCKED_PROVENANCE\`. This is not a
production provider and does not change \`BLOCKED / RESEARCH_ONLY_NO_EDGE\`.

## 11. Verified public institutional directory — candidate metadata only

A fresh review of the Secretaría de Economía's official PSC directory
(\`https://psc.economia.gob.mx/directorio.html\`) confirms that the directory
currently lists, among other providers:

- **ATEB Servicios, S.A. de C.V.** — service of digital time seals, with the
  directory linking to its DOF notice dated 23-Aug-2022;
- **INCODE PSC, S. de R.L. de C.V.** — service of digital time seals, with the
  directory linking to its DOF notice dated 22-May-2024.

This verifies their listing and named service in the official directory. It
does **not** establish that either provider operated the timestamp service
for a particular Chispazo draw, that Lotería Nacional delegated draw custody
to it, or that a certificate/TSA policy is authorized for this project.

The directory's link to the Secretaría de Economía Second Certification
Authority certificate resolves to
\`https://psc.economia.gob.mx/certificados/ACR2_SE.cer\`, but the available web
reader rejects its \`application/pkix-cert\` content type and the research
runtime could not download the DER/PEM bytes. The certificate fingerprint,
chain, validity and revocation state therefore remain **NOT_CAPTURED / NOT
VERIFIED**. No certificate was installed or pinned.

The PSC page also cautions that PSC services do not, by themselves, confer
public faith. Accreditation metadata must not be confused with institutional
authority over Lotería Nacional's draw process.

ATEB and INCODE remain **candidate discovery leads only**. Do not select
either as a TSA root, hardcode an OID, accept a token, or configure a trust
anchor from this directory entry alone. Required next evidence is exact
certificate bytes/fingerprint, complete chain and current status, live RFC
3161 response validation, exact service policy/OID, and separate
institutional delegation tying the service to the relevant Chispazo records.

## 12. Distinguish the earlier provider-context join from the stricter composition

The helper \`deployment_trust_physical_composition_v1.py\` added on the PR #95
branch reads a deployment snapshot and a provider-owned physical context, then
runs physical and receipt/policy verification. However, it does not enforce
that the context's policy root bytes, root key ID and bootstrap floor equal
the deployment snapshot. It also does not bind the exact physical-context
digest/generation into the deployment snapshot's trust-configuration digest
and CAS.

Consequently, that helper can still join a physical chain evaluated under a
provider-returned context with a receipt/policy inspection evaluated under a
different deployment root, or with a context that changes between read and
CAS. A provider method returning both objects is not, by itself, proof that
their trust contexts are identical or atomically versioned.

For a single-snapshot provider-backed full evidence composition, use
\`deployment_evidence_composition_v1.py\` from PR #96. It enforces root/key
ID/bootstrap-floor equality, binds the canonical physical-context digest and
generation into the deployment trust configuration, derives the effective
policy floor from the snapshot, and requires the provider CAS to compare that
same context binding atomically. The earlier helper remains research-only
and must not be treated as the same trust boundary.

Neither path authenticates the provider implementation, physical-context
provisioning, institutional draw authority, physical artifact origin or
independent custody.

## 13. Defensive copy of provider-owned physical context

The application now copies every primitive field from the exact
`PhysicalTrustContextV1` returned by the provider into a new validated
instance **before** computing its canonical digest or consuming any trust
anchor. A frozen dataclass is not a security boundary against
`object.__setattr__`; retaining the provider's original object after hashing
would permit a provider-side mutation to replace a log/TSA/registry pin after
the digest check (a time-of-check/time-of-use gap).

A synthetic adversarial regression computes the context digest and then mutates
the provider-owned source object immediately afterward. The composition must
continue using the independent copied object whose digest still matches the
deployment snapshot. This protects the application operation from mutation of
the returned Python object; it does **not** authenticate the provider or
replace the provider's atomic authoritative-state comparison at CAS.


## 14. Out-of-band trust-anchor and anti-rollback bootstrap runbook

**Status: required deployment procedure, not performed.** This section specifies the minimum bootstrap ceremony. It does not claim that Lotería Nacional, SEGOB, a TSA, a transparency-log operator, or a custodian has supplied or authorized any trust anchor for this repository.

### A. Root trust-anchor ceremony

1. Obtain the institutional root public key and its authorization statement from the institution that is legally responsible for the relevant evidence. The key package must be delivered through a channel independent of this repository, the submitting user, the receipt issuer, and the deployment host. A URL or repository commit alone is not an out-of-band trust ceremony.
2. Verify the institution's legal identity and its explicit authority for the exact purpose and scope: Chispazo **Clásico**, the applicable evidence classes, receipt-attester delegation, physical-record signer roles, and any timestamp/ledger services. A general digital-signature or PSC accreditation is not draw-specific delegation.
3. Verify the public-key fingerprint independently through two separately administered channels. Record the exact raw public-key bytes, fingerprint, key ID, algorithm, institution, authority instrument, scope, effective interval, root generation, and revocation/rollover contact. Two URLs controlled by the same publishing system do not count as independent channels.
4. Require dual control for acceptance (at least two separately identified approvers). Each approver signs the same canonical bootstrap record. The record binds the CLASSIC policy domain, root fingerprint and key ID, root generation, minimum policy sequence, policy-authority identity, clock/TSA/log/registry trust inputs, state-backend identity, and the hashes of all source instruments.
5. Store the signed bootstrap record and approvals in an independently controlled, append-only evidence store. The verifier receives only the pinned public material and its record digest. Root private keys remain under institutional offline/HSM control and must never be copied into this repository or application configuration.
6. Reconcile any root rotation as a distinct dual-authorized transition. Require explicit old-root and new-root authorization (or an independently documented institutional recovery procedure), increment root generation, preserve the prior sequence/time watermarks, and prohibit resetting the CLASSIC sequence floor.

A root is not provisioned until the signed record, both approvals, source authority, fingerprint cross-checks, and revocation/rollover process have been independently reviewed. If any item is absent or ambiguous, do not install the key.

### B. Anti-rollback state genesis and operation

1. Provision the state backend independently of the application and its repository. It must provide linearizable compare-and-advance, durable monotonic generations, access separation, tamper-evident audit, and a recovery path that can detect restoration of an older snapshot. A normal file, environment variable, caller-supplied database, or unanchored backup does not satisfy this requirement.
2. Create a signed genesis record scoped to `origen.chispazo.classic.provenance` and the pinned root generation. It must bind the trust-configuration digest, root key ID/fingerprint, bootstrap minimum sequence, state generation, backend identity, and initial policy/time watermarks. The empty initial state is explicit: accepted sequence and accepted envelope digest are unset; trusted-time watermark is unset; generation is the documented genesis generation. Never silently initialize state from a submitted receipt.
3. For each accepted signed policy, atomically compare the expected state generation, exact trust-configuration digest, exact clock-sample digest, root generation, policy sequence and envelope digest. A higher sequence advances one generation. Same sequence/same digest is idempotent except that a later non-overlapping trusted-time interval advances the time watermark and generation. Same sequence/different digest is equivocation; lower sequence is rollback; stale generation or changed configuration/sample is conflict.
4. Persist the **upper bound** of each accepted trusted-time uncertainty interval. Reject any next interval whose earliest possible instant is earlier than the persisted upper bound, including same-sequence retries. Do not compare only the midpoint or only the time of the last policy acceptance.
5. A root-generation change, backend migration, disaster recovery, or restoration must be an explicit signed transition that carries forward the last accepted sequence, exact envelope digest, time watermark and state generation. If the latest state cannot be proven against an external monotonic anchor, stop verification and require a new independently witnessed bootstrap; do not lower the floor or reconstruct it from repository history.
6. Require independent monitoring of sequence/time-watermark changes, failed CAS attempts, equivocation, clock lease expiry, configuration drift, backup restore and privileged access. Retain the signed transaction/audit evidence outside the service being monitored.

### C. Operational acceptance evidence

Before any deployment may be described as provisioned, retain and independently review:

- signed root/bootstrap record and two approval signatures;
- institution authority instrument and two-channel fingerprint verification record;
- root/key validity, revocation and rollover evidence;
- signed state-genesis record and backend control/linearizability assessment;
- externally anchored monotonic checkpoint and a demonstrated rollback/restore rejection;
- clock-source identity, signed sample, uncertainty policy, freshness lease and independent key authorization;
- provider implementation/build digest, deployment composition-root configuration digest, access-control evidence and independent security review;
- successful adversarial failover, stale snapshot, equivocation, clock rollback, root rotation and backup-restore exercises.

The current repository has none of this production provisioning evidence. The provider and all trust fixtures remain synthetic; no trust root is installed, no anti-rollback backend is deployed, and all results remain `BLOCKED_PROVENANCE`. Do not infer institutional authorization from the Secretaría de Economía PSC directory alone. In particular, PSC listing metadata does not prove that a provider was used by or delegated authority from Lotería Nacional for a specific draw.


## 15. RFC 3161 nonce challenge lifecycle — 2026-11-26

The complete evidence composition no longer accepts caller-supplied RFC 3161
request nonces. It requires the deployment provider to return an exact
`TimestampNonceChallengeV1` bound to the snapshot's state generation, root
generation, physical-trust-context generation and digest. The challenge carries
separate, distinct positive signed-64-bit nonces for the policy-envelope timestamp and
the detached custody-signature timestamp, plus a canonical issuance/expiry
window. Its complete canonical digest is passed to the provider CAS.

A conforming deployment provider must:

1. Generate both nonce values using a cryptographically secure random source.
   Never derive them from caller input, timestamps, policy sequence, or a
   predictable counter.
2. Persist the challenge as pending and bind it to the exact state/root/context
   tuple returned by the same deployment snapshot.
3. Reject a challenge whose issue/expiry interval does not cover the full
   authenticated clock-uncertainty interval, or whose expiry exceeds the
   current clock-sample lease.
4. In the same linearizable transaction that advances policy/time state, look
   up the pending challenge from authoritative storage, recompute its digest,
   verify its state/configuration binding, and consume both nonce values.
5. Reject reuse of either nonce value, even if a caller presents a fresh
   challenge ID or recomputes a public digest. Consumption also applies to an
   otherwise-idempotent successful policy inspection.
6. Leave a challenge unconsumed when evidence validation or the CAS fails;
   expire it according to provider time and never allow it to survive a state
   generation change.

The application checks the returned challenge and passes only its identifier
and digest to the CAS. It does not treat the challenge object as an
institutional capability. The provider's issuance store, randomness, atomic
consumption, persistence and recovery behavior remain deployment obligations.
The test provider's nonce ledger is synthetic and is not evidence of a
production implementation.

Remaining blocker:
`RFC3161_NONCE_CHALLENGE_ISSUANCE_AND_SINGLE_USE_NOT_INDEPENDENTLY_AUTHENTICATED_OR_DEPLOYED`.
No institutional nonce service or production provider has been provisioned.

## One registry snapshot per gossip comparison

Every observation batch in one cross-batch comparison must use the same
root-signed registry sequence and exact signed registry digest. The verifier
rejects mixed sequences rather than pooling witness statements authorized by
different registry snapshots; a newer registry may revoke a key that remains
present in an older registry. Registry rotation therefore requires a separate
comparison. This in-bundle guard does **not** provide persistent anti-rollback:
the deployment provider must still persist the accepted registry sequence and
digest under independent monotonic state before any provenance claim can be
considered.


## 15. Timestamp nonce challenge is scoped to one backend and policy domain

The V1 nonce challenge now carries both `policy_domain` and
`state_backend_id`. Both values are included in its canonical SHA-256 digest.
The application rejects a challenge unless these values exactly match the
fixed CLASSIC provenance domain and the `state_backend_id` in the same
deployment snapshot. The CAS implementation must repeat those checks against
its authoritative pending-challenge record before consuming either RFC 3161
nonce.

This closes an accidental cross-domain/cross-backend challenge-reuse gap in
the transport contract. It does not authenticate the provider, prove that
nonces are unpredictable, or establish a durable anti-rollback service. The
provider must still enforce single-use consumption atomically.

Synthetic adversarial regressions cover a challenge copied from another
backend, a challenge copied from another policy domain, and digest sensitivity
to both scope fields. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.


## 16. Atomic ledger-checkpoint and witness-registry anti-rollback watermark

The provider snapshot now carries an optional accepted external-evidence watermark
with the exact CLASSIC domain/backend, transparency-log and log-key identity,
accepted tree size/root/checkpoint digest, witness-registry/root-key identity,
accepted registry sequence and exact signed registry-byte digest. A full physical
evidence composition is rejected unless this watermark was provisioned before the
inspection; the caller cannot create genesis from the submitted bundle.

After the nested signatures, RFC 3161 tokens, ledger inclusion/consistency proof
and witness quorum have been re-verified, the application derives one bounded
advance candidate. All witness batches must expose one exact registry sequence
and one exact registry-byte digest. The candidate binds the old and new checkpoint
sizes, roots and byte digests plus the registry identity/version/digest.

The linearizable provider CAS must, in the same transaction as policy sequence,
trusted-time watermark and nonce consumption:

1. Recompute the accepted watermark digest from authoritative storage and compare
   it with the snapshot digest supplied by the application.
2. Reject a lower ledger tree size; reject same-size root/checkpoint changes as
   equivocation; for a larger tree, require the supplied old checkpoint to equal
   the exact persisted tree size, root and checkpoint digest.
3. Reject a lower witness-registry sequence and reject a different exact registry
   digest at the same sequence. A registry/log/root identity change requires a
   separate authorized transition; it is not an ordinary advance.
4. Atomically persist the new checkpoint and registry watermark with the policy,
   time and nonce state, incrementing the shared generation exactly once. Return
   the resulting watermark digest in the commit receipt.
5. Preserve the watermark unchanged for policy-only inspections. Never initialize,
   lower, restore or silently replace it during failover or backup recovery.

ExternalEvidenceWatermarkV1 and ExternalEvidenceAdvanceV1 are immutable
application contracts, not authentication capabilities. The repository contains
no production CAS implementation. The provider must repeat all comparisons under
its own transaction/lock against independently anchored durable state; the
application-side validation and synthetic provider only exercise the contract.
The initial ledger checkpoint and registry digest must be established by a
separate out-of-band, independently witnessed genesis ceremony. Until that exists,
full provider-backed physical composition remains fail-closed and production stays
BLOCKED / RESEARCH_ONLY_NO_EDGE.
