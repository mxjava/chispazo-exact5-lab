# ORIGEN v0.3 — out-of-band trust-anchor provisioning and anti-rollback contract v1

**Status:** DESIGN CONTRACT ONLY — NOT DEPLOYED. The current V3 verifier still accepts the root public key, expected root key ID, minimum policy sequence and verification clock as caller-supplied arguments. This document does not claim those inputs are authenticated.

## 1. Security objective

A signed policy envelope is meaningful only relative to a trust anchor and freshness state that the same untrusted caller cannot replace. The deployment boundary must supply those values from independently administered, integrity-protected sources. A Python object, environment variable, command-line flag, repository file, JSON field, or callback provided by the invoking process is not an independent trust anchor.

The future integration must not expose an API shaped like:

`verify(raw, pinned_root=caller_value, minimum_sequence=caller_value, now=caller_value)`

to an untrusted caller. The public entry point should accept only the original policy/receipt bytes and a deployment identifier; it must resolve trust context internally through a separately reviewed provider.

## 2. Root-anchor bootstrap ceremony

1. Generate the policy-root Ed25519 key in an HSM or equivalent non-exportable key service controlled by the institution responsible for policy issuance. The repository and CI must never contain the private key.
2. Provision the 32-byte public key, canonical key ID, policy domain and deployment identifier through an authenticated administrative channel independent of the repository, application image and evidence submitter.
3. Verify the public-key fingerprint out of band using two independently administered channels and a two-person approval record. A fingerprint copied from the same Git commit, PR, container image or receipt being evaluated is not an independent confirmation.
4. Store the anchor in a protected deployment trust store (for example, an HSM-backed configuration service or a TPM-sealed, access-controlled deployment record). Record who approved it, when, under which change ticket, and the prior anchor/fingerprint.
5. Refuse bootstrap if the deployment ID, key ID, domain, fingerprint, approvers or provenance of the provisioning record are missing or ambiguous.

Root rotation requires a separately approved transition: old-root authorization of the new root, confirmation through the independent administrative channel, an explicit activation time, a new key ID and a strictly increasing policy sequence. Emergency replacement without a verifiable transition must remain blocked and require an audited recovery ceremony.

## 3. Anti-rollback state

The minimum accepted policy sequence must come from durable monotonic state outside the caller and outside the repository checkout. Acceptable deployment designs include an HSM/TPM monotonic counter or a remote append-only control ledger with authenticated compare-and-swap semantics and independently witnessed checkpoints. A plain local file, environment variable, database row controlled by the same application identity, Git ref, or caller parameter is not sufficient by itself.

Required transaction:

1. Read the current deployment floor and its authenticated version/checkpoint.
2. Verify the signed policy against the provisioned root, expected key ID, fixed policy domain, trusted time and the current floor.
3. Reject any sequence below the floor. Reject equal sequence with a different policy digest. An exact same-sequence/same-digest replay may be treated as idempotent only if the deployment protocol explicitly permits it.
4. After all signature, schema, role, artifact-type and chronology checks succeed, atomically compare-and-swap the floor from the observed value to the new policy sequence and envelope digest.
5. If persistence, checkpoint witnessing, compare-and-swap or read-back verification fails, return blocked. Never accept a policy merely because the signature verified before the anti-rollback update failed.
6. On restart, re-read the monotonic state and verify the last committed envelope digest/checkpoint. A missing, stale, forked or unverifiable state blocks the deployment.

The policy sequence and envelope digest must be bound together. A sequence number alone cannot detect two different valid envelopes at the same sequence.

## 4. Time and revocation

The current caller-supplied `verification_time` is not trusted time. The deployment provider must obtain time from an independently controlled source and record its identity, synchronization state and uncertainty. Where the decision concerns when a signature existed, use a verified RFC 3161 token and enforce the complete accuracy interval against policy and delegated-key validity, as the V3 custody timestamp path now does. The signed policy's `issued_at_utc` and `not_before_utc` values are still root-authored claims: comparing receipt/custody signature time to them prevents an internally inconsistent retroactive authorization, but does not prove that the policy bytes existed at that time. Before deployment, timestamp the exact signed policy-envelope bytes with a separately provisioned TSA and anchor that token digest in the independently witnessed ledger. Until then, retain the explicit blocker `SIGNED_POLICY_ENVELOPE_EXISTENCE_TIME_NOT_INDEPENDENTLY_AUTHENTICATED`.

TSA validation still requires an authenticated TSA root, policy-OID authorization, certificate path validation and current/historical revocation evidence. A self-supplied TSA root or a successful synthetic token test does not meet this requirement. If time uncertainty overlaps a policy/key boundary, reject rather than select the favorable endpoint.

## 5. Target API boundary (not yet implemented)

A separately reviewed deployment provider should return an immutable, process-internal context containing at minimum:

- deployment ID and fixed policy domain;
- provisioned root public key and root key ID;
- authenticated monotonic sequence floor and last accepted envelope digest;
- authenticated time value, source identity and uncertainty;
- revocation snapshot/version and source;
- provenance metadata for the provisioning transaction.

The verifier should consume this context only through a trusted internal control path. It must not accept an arbitrary context object from the evidence submitter, nor treat a public Python dataclass as unforgeable. The provider must own the protected reads and atomic state transition; its implementation and administrative controls require independent security review.

Until that provider exists, keep the current caller-parameter APIs explicitly research-only and keep `verify_independent_provenance` returning only `BLOCKED_PROVENANCE`.

## 5.1 Implemented fail-closed API separation (research only)

The V3 diagnostic API has been separated from the public provenance entry point:

- Public `verify_independent_provenance(original_receipt_bytes)` accepts only exact receipt bytes. It rejects caller-supplied policy bytes, root pins, key IDs, sequence floors, clocks, verifier callbacks, and provider objects as unexpected keyword arguments, and it always returns `BLOCKED_PROVENANCE`.
- Public `inspect_receipt_with_deployment_trust_provider` and `inspect_custody_ledger_witness_with_deployment_provider_v1` accept no provider object, provider snapshot, root pin, key ID, sequence floor, or clock. They resolve the provider only through `_load_deployment_trust_provider()` in `deployment_trust_provider_bootstrap.py`. That repository loader returns `None`, so both public facades fail closed until an independently reviewed deployment package/image supplies a provider. The provider-taking implementations are private helpers used by the facades and synthetic tests; Python private names are not unforgeable capabilities. Never replace the loader from request input, environment variables, repository data, CI variables, or a downloaded envelope. The deployment image, provider service identity, access controls, immutable build provenance and external CAS require independent review. The receipt-only facade also accepts no `external_evidence_advance`; it cannot update the external ledger/witness watermark. Only the complete custody + RFC 3161 + ledger + independent-witness composition may construct an advance after verifying the exact evidence bytes. The external provider CAS must independently re-verify the manifest, ledger entry, inclusion proof, signed checkpoints, consistency proof, registry and witness statements against provider-owned log/registry pins, revocation state and quorum policy as part of its serialized transition; it must not trust the application's prior verification or caller-computed digests alone.
- The deployment-provider composition path invokes a private re-verification helper only after obtaining and validating one `DeploymentTrustSnapshot`. That path supplies the exact signed policy-envelope bytes and receipt bytes plus snapshot-derived root pin, key ID, sequence floor and normalized UTC instant; it re-verifies both cryptographic layers and still returns only `BLOCKED_PROVENANCE`.
- The lower-level `verify_receipt_attestation_with_policy_v3` and custody/ledger diagnostic bridges also use the private helper, but their explicit root pin, key ID, sequence floor and clock remain caller-supplied. They are not provisioning paths and cannot establish independent trust.
- The private helper is an API-discipline boundary, not an unforgeable Python capability. The provider object and its implementation remain untrusted until a real independently administered provider is provisioned and reviewed.

This change prevents accidental use of request-level trust inputs at the public provenance API. It does **not** authenticate the provider, root provisioning, trusted time, anti-rollback storage, institutional identity, physical records or custody. No production trust anchor is added.

## 5.2 Exact-byte provider CAS and provider-owned time

Every provider CAS call now carries the original `raw_policy_envelope_bytes` and `raw_receipt_bytes`, including receipt-only inspections where no full physical evidence advance is supplied. The provider must independently parse and verify those exact bytes against its authoritative root, policy domain, key ID, durable sequence floor and signed current time. It recomputes the policy digest/sequence, verifies the receipt signature and full uncertainty interval, and rejects any mismatch before durable state mutation. If a full `ExternalEvidenceAdvanceV1` is also supplied, its embedded policy and receipt bytes must equal these separate required inputs; the provider must additionally re-verify the complete nested signature, custody, RFC 3161, ledger, inclusion/consistency and witness-registry envelope inside the same transaction.

The CAS API intentionally does not accept caller-supplied accepted time or uncertainty. The provider derives those values from its own authenticated signed clock sample, rechecks the sample digest and lease, and serializes those checks with state advancement. Successful commits must return the exact receipt SHA-256 as well as the policy and external-evidence watermark digests; the application rejects a response that does not bind the receipt bytes it supplied.

The synthetic provider tests exercise the receipt/policy/time contract only. They are not an independent provider implementation. No institutional CAS, clock, root provisioning or custody is installed.

## 6. Required adversarial deployment tests

Before any deployment can leave the blocked state, tests must cover:

- wrong root fingerprint, key ID, deployment ID and policy domain;
- policy sequence rollback;
- same sequence with a different envelope digest;
- concurrent updates racing the monotonic compare-and-swap;
- failure after signature verification but before durable floor commit;
- restart with a stale, missing or forked monotonic record;
- root rotation with missing or invalid dual-control authorization;
- compromised caller attempting to inject its own clock, root, floor or revocation map;
- TSA accuracy intervals crossing policy/key validity or revocation boundaries;
- provider outage and partial reads, all of which must fail closed.

Synthetic provider tests validate code paths only. They do not prove HSM/TPM provisioning, administrative separation, legal identity, institutional independence or operational custody.

## 7. Current disposition

No institution-controlled root, monotonic state provider, trusted clock, revocation feed, witnessed control ledger or two-person provisioning evidence has been verified for this repository. This contract is a design target, not an implementation claim.

Production remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`

V294, the canonical history, PR #13 and the prospective statistical gate remain unchanged.
