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


## 10. Provider-backed composition with the complete physical evidence bundle

PR #96 adds `src/origen/deployment_evidence_composition_v1.py` and the
research-only API:

```python
inspect_custody_ledger_witness_with_deployment_provider_v1(
    original_receipt_bytes,
    signed_policy_envelope_bytes,
    custody_record_bytes,
    portfolio_bytes,
    custody_signature_bytes,
    custodian_key_id,
    # exact RFC 3161, manifest, artifact, ledger and witness inputs
    provider=deployment_composition_root_provider,
    # TSA, transparency-log and witness-registry pins remain explicit
)
```

The request API intentionally has no `pinned_root_public_key_bytes`,
`expected_root_key_id`, `minimum_policy_sequence`, or
`verification_time` argument. It reads the CLASSIC deployment provider once,
copies and validates the immutable snapshot, and derives the policy root,
root key ID, effective sequence floor, clock interval and normalized UTC
verification instant from that same snapshot.

The application order is:

1. Validate exact receipt/policy byte types and size bounds.
2. Read one CLASSIC provider snapshot. Verify the signed clock-sample envelope
   and its source/sample/time/lease claims against the snapshot key.
3. Verify the exact V3 policy envelope under the snapshot root and effective
   sequence floor. Verify that the root-signed policy authorizes the exact
   clock key for `TRUSTED_TIME_AUTHORITY / CLOCK_SAMPLE`.
4. Enforce the persisted trusted-time watermark and same-sequence digest rule.
5. Verify the exact receipt attestation using the verified policy; require the
   full clock uncertainty interval to fit policy and receipt-key validity and
   prove the receipt signature predates the earliest possible verification
   instant.
6. Parse the exact physical manifest and require every physical and custody
   signer key used by that bundle to be non-revoked and valid over the *whole*
   uncertainty interval, not just its midpoint.
7. Re-run the complete custody, nested-signature, both RFC 3161, manifest,
   ledger inclusion/consistency and witness composition using the root, floor
   and time from the same provider snapshot. That composition re-enters
   `verify_independent_provenance` on the exact original receipt and policy
   bytes and requires exact `BLOCKED_PROVENANCE`.
8. Only after the complete evidence composition succeeds, call the existing
   provider inspection through a private pinned-snapshot adapter. Its repeated
   policy/receipt/independent-boundary checks must match the same snapshot; its
   compare-and-advance is the only state-mutating operation.
9. Validate that the commit result binds the same exact policy digest, root
   generation, trust-configuration digest and clock-sample digest. Any CAS
   conflict or mismatched commit returns no inspection result.

The adapter delegates the final CAS to the original provider but never asks
that provider for a second snapshot. Therefore a nested-signature, timestamp,
ledger, witness or independent-boundary failure occurs before provider state
can advance. The synthetic tests assert one original snapshot read, one CAS
on success, and zero CAS for evidence failures.

The wrapper does **not** pass a caller-constructed `VerifiedTrustPolicyV3`
or receipt-verifier result into the evidence chain. It verifies raw bytes for
preflight and the lower-level evidence verifiers independently re-verify the
same raw bytes against the same root/time inputs. This preserves the exact-byte
boundary rather than treating an in-process result object as a trust token.

### Remaining external trust domains

The provider root, signed clock sample and anti-rollback state are now
integrated at the application boundary, but the provider object is still a
trusted deployment dependency whose implementation and provisioning are not
authenticated by this repository. The TSA root, transparency-log root and
witness-registry root remain caller-supplied. They must be moved behind
independently provisioned trust services before this can be described as a
complete trust composition. Institutional identity, physical artifact truth,
independent custody, revocation and the prospective statistical edge remain
unestablished.

All successful paths remain `BLOCKED_PROVENANCE`. This is not a production
provider and does not change `BLOCKED / RESEARCH_ONLY_NO_EDGE`.


## 11. Verified public institutional directory — candidate metadata only

A fresh review of the Secretaría de Economía's official PSC directory
(`https://psc.economia.gob.mx/directorio.html`) confirms that the directory
currently lists, among other providers:

- **ATEB Servicios, S.A. de C.V.** — service of digital time seals, with the
  directory linking to its DOF notice dated 23-Aug-2022;
- **INCODE PSC, S. de R.L. de C.V.** — service of digital time seals, with the
  directory linking to its DOF notice dated 22-May-2024.

The same official directory also lists other time-seal providers. This is
verifiable evidence that those entities appear in the Secretaría de Economía
PSC directory for the named service. It is **not** evidence that either entity
operated the timestamp service for a particular Chispazo draw, that Lotería
Nacional delegated draw custody to it, or that any certificate or TSA policy
is authorized for this project.

The directory's link to the Secretaría de Economía Second Certification
Authority certificate resolves to
`https://psc.economia.gob.mx/certificados/ACR2_SE.cer`, but the available web
reader rejects its `application/pkix-cert` content type and the research
runtime could not download the DER/PEM bytes. The certificate fingerprint,
chain, validity and revocation state therefore remain **NOT_CAPTURED / NOT
VERIFIED**. No certificate was installed or pinned.

The Secretaría de Economía PSC page also cautions that PSC services do not,
by themselves, confer public faith. Accreditation metadata must not be
confused with institutional authority over Lotería Nacional's draw process.

Accordingly, ATEB and INCODE remain **candidate discovery leads only**. Do not
select either as a TSA root, hardcode an OID, accept a token, or configure a
trust anchor from this directory entry alone. Required next evidence is the
exact certificate bytes and fingerprint, complete chain and current status,
live RFC 3161 response validation, the exact service policy/OID, and a
separate institutional delegation tying the service to the relevant Chispazo
records.


## 12. Distinguish the earlier two-call diagnostic join from the single-snapshot composition

The research helper `deployment_trust_physical_composition_v1.py` added on the
current PR #95 branch verifies physical evidence using a caller-supplied
`physical_verification_kwargs` mapping, then calls
`inspect_receipt_with_deployment_trust_provider`, which reads provider state
separately. It compares the exact receipt and policy byte digests, but does
not prove that the physical verifier used the provider snapshot's root bytes,
root key ID, sequence floor, signed clock sample, uncertainty interval or
trust-configuration digest. Its docstring's midpoint-equality requirement is
not enforced by that helper.

That helper remains a diagnostic join only. A matching receipt/policy digest
does not prove that two verifiers used the same trust context. Do not treat
its returned object as evidence that the physical bundle was verified under
the deployment provider's trust snapshot.

For a single-snapshot provider-backed full evidence composition, use only
`deployment_evidence_composition_v1.py` from PR #96. That API obtains the
provider snapshot first, derives root/floor/time from it, validates the clock
and receipt, checks the complete time interval for all used physical/custody
keys, runs the full physical evidence chain with the same root/floor/time, and
then performs the provider CAS through the cached snapshot adapter. The weaker
two-call helper is not a substitute for this API.

Both paths remain research-only and return `BLOCKED_PROVENANCE`; neither
authenticates the provider implementation, TSA/log/witness institutional
roots, physical origin or independent custody.
