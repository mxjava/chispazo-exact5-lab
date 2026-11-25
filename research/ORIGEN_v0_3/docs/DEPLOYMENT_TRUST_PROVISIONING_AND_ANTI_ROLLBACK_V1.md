# ORIGEN v0.3 — Deployment trust-anchor and anti-rollback provisioning contract v1

**Classification:** architecture specification only; not an implemented deployment backend. The independent provenance adapter MUST remain fail-closed.

## 1. Current verified boundary

The research implementation has these deliberately separate layers:

- `verify_signed_trust_policy(raw, pinned_root_public_key_bytes, expected_root_key_id, minimum_policy_sequence, verification_time)` verifies canonical policy bytes and an Ed25519 signature relative to the values supplied to that call.
- `inspect_signed_root_attestation_chain(...)` re-verifies the raw signed policy envelope, then passes the resulting immutable policy snapshot to `verify_receipt_attestation(...)`.
- `verify_independent_provenance(original_receipt_bytes)` is a separate kill switch. It currently returns only `BLOCKED_PROVENANCE`; a successful policy and receipt signature inspection cannot override it.
- Nested physical-signature, TSA, ledger, checkpoint and witness verifiers also label their root keys, sequence floors and clocks as caller-supplied and unauthenticated.

A `VerifiedTrustPolicy` instance is a diagnostic value, not an unforgeable capability. Security boundaries must re-verify original signed bytes using deployment-provisioned inputs. They must not accept a caller-constructed result object as proof.

## 2. Trust-anchor bootstrap: out-of-band ceremony

The first root public key cannot authenticate itself. The initial trust anchor MUST be established independently of the repository, policy envelope, TSA token, evidence uploader and the network path used to retrieve those objects.

Required bootstrap record:

- exact 32-byte Ed25519 public key (or the exact DER certificate for an X.509 root);
- canonical key identifier and cryptographic algorithm;
- SHA-256 fingerprint calculated from the captured bytes;
- declared purpose and permitted policy domains (receipt policy, TSA policy, log registry, witness registry); keys MUST NOT be silently reused across these roles;
- issuing organization, accountable key custodians, validity/activation time and revocation/rotation process;
- source URI or physical source reference, acquisition time, acquisition operator, independent witness and original-byte digest;
- two-person approval record and a separately archived copy of the pin.

The two approvers MUST compare the fingerprint through a second channel controlled by a different administrative domain (for example, a signed institutional publication plus a separately authenticated confirmation). A TLS download from the same host is useful transport protection but is not an independent bootstrap channel.

Deployment MUST install the approved pin into integrity-protected configuration whose update path is separate from the application repository. Acceptable implementation candidates include measured/verified boot with a signed deployment manifest, an HSM-backed configuration service, or a read-only deployment image whose digest is itself checked by the platform. A normal environment variable, command-line argument, mutable JSON file in the application directory, Git branch, or value supplied by the evidence caller is NOT an acceptable production root source.

Root rotation requires a new two-person ceremony. The old root must authorize the successor while still trusted, and the new fingerprint must also be confirmed out of band. Emergency recovery from a compromised root requires a separately governed recovery authority; it must not be inferred from a policy signed by the compromised root.

## 3. Anti-rollback state: monotonic external persistence

A minimum sequence number passed by a caller is not anti-rollback protection. Production requires durable state outside the repository and outside the evidence request.

The deployment state record MUST bind at least:

```text
root_key_id
policy_domain
policy_sequence
policy_envelope_sha256
accepted_at_utc
state_generation
```

The state backend MUST provide linearizable compare-and-swap (or an equivalent single-writer transaction) and must detect rollback, reset, snapshot restoration and split-brain replicas. Suitable implementation candidates are a TPM 2.0 NV monotonic counter with a protected journal, an HSM-backed monotonic state service, or a quorum-controlled remote state service with authenticated audit history. A local file, SQLite database, container volume, cache, process memory, or Git commit is not sufficient by itself.

Acceptance transaction:

1. Read the current protected state and its generation.
2. Verify the raw policy envelope against the independently pinned root and trusted time.
3. Reject a lower sequence.
4. For the same sequence, allow only the exact same envelope digest (idempotent re-read); reject a different digest as equivocation.
5. For a higher sequence, require the expected prior generation and atomically commit the new sequence and envelope digest.
6. Only after the commit succeeds may the verified policy be used for the current operation.

If the backend is unavailable, stale, rolled back, reset, inconsistent, or cannot commit atomically, the operation MUST fail closed. A crash after committing but before using the policy is safe: a retry with the same sequence and digest is idempotent. Concurrent updates must not let a lower sequence overwrite a higher one.

Separate sequence domains are required for receipt policy, TSA policy, witness registry and log-key registry. A sequence from one domain must never satisfy another domain's floor.

**Current implementation gap:** `trust-policy-envelope.v1` does not contain an explicit `policy_domain` field. Domain separation is therefore not established by the V1 envelope itself. Before a production adapter exists, either introduce a new signed envelope version that includes the domain in the signature preimage, or provision distinct root/key namespaces and independent monotonic state per schema/domain. A caller-supplied label must not be treated as authenticated domain binding.

## 4. Verification time and revocation

The current `verification_time` parameter is caller-supplied. Production time MUST come from a separately operated, authenticated time service with monitored synchronization and bounded uncertainty. Wall-clock rollback, unavailable time, leap-second ambiguity, or uncertainty outside the policy limit is a hard failure. A monotonic clock may measure elapsed durations but cannot replace an authenticated UTC instant.

Certificate validation must include current, authenticated revocation status (OCSP and/or CRL), responder authorization, signature validation, freshness bounds, and failure behavior for unknown/stale status. Missing revocation data is not equivalent to “not revoked”. A historical RFC 3161 token can prove that bytes were timestamped under a TSA key; it does not by itself prove that the key was unrevoked or institutionally authorized for this use.

## 5. Institutional source assessment: ACR2-SE / PSC directory

The Secretaría de Economía's official PSC site states that it accredits and supervises Prestadores de Servicios de Certificación and lists accredited services including digital certificates, data-message preservation and digital time stamps:

- https://psc.economia.gob.mx/directorio.html
- https://psc.economia.gob.mx/docs_l/Politica_ACR2SE.pdf

The official directory exposes a link labelled “Certificado Digital de la Segunda Autoridad Certificadora de la Secretaría de Economía” and lists PSC providers with service-specific accreditation dates. The ACR2-SE certificate policy describes the CA hierarchy and its intended community, including subordinate CAs for PSCs.

This is a legitimate institutional lead, NOT a production trust decision. The ACR2-SE certificate DER bytes and independently checked fingerprint have not been captured in this repository. A PSC's listing for “sellos digitales de tiempo” establishes a published accreditation claim for that service; it does not establish that the PSC is authorized by Lotería Nacional or SEGOB to certify Chispazo draw records, sphere measurements, machine assignment or custody. No such delegation has been verified.

Before considering any PSC for this project, independently acquire and preserve:
- the current root and issuing/subordinate certificates as exact DER bytes;
- their SHA-256 fingerprints through an independent channel;
- current certificate policy, CPS, scope, service accreditation and effective dates;
- signed CRL/OCSP evidence and revocation freshness;
- the PSC's explicit written authority and service scope for the specific Chispazo evidence use case;
- a real RFC 3161 token over an archived original artifact, with its request nonce, policy OID, certificate chain and custody record.

The official policy PDF is version 1.1 dated July 2018. Its publication is evidence of a policy document, not proof that a particular certificate is current or that a specific PSC currently operates a Chispazo-authorized service.

## 6. Required deployment separation

Production deployment must separate administrative and cryptographic roles:

| Role | Required separation |
|---|---|
| Deployment root custodian | Does not generate draw evidence or run the Exact5 model |
| Policy signer | Cannot modify the monotonic state backend |
| Receipt issuer | Cannot provision its own root key or policy floor |
| TSA operator | Cannot supply the application trust pin or choose the expected nonce after seeing the artifact |
| Log operator | Cannot act as the sole witness to its own checkpoints |
| Witness operators | Distinct legal/administrative operators, not merely different key IDs |
| Physical signers and custodians | Role identity and authority independently verified; no self-attestation |
| Exact5 generator | Cannot alter or replace sealed pre-close outputs |

Every external artifact must be acquired as original bytes, hashed before parsing, and transferred with signed custody receipts and trusted timestamps. Re-serialized JSON, screenshots, web-page renderings and repository metadata are not substitutes for original source bytes.

## 7. Integration gate

The future deployment adapter MUST be a separately reviewed platform boundary, not a caller callback or a public API that accepts arbitrary trust booleans, key maps, `VerifiedTrustPolicy` objects, minimum sequences or clocks.

At minimum it must:

1. Load the root pin and role/domain restrictions from integrity-protected deployment configuration.
2. Obtain the monotonic policy floor and generation from the protected external state service.
3. Obtain a trusted UTC instant and uncertainty bound.
4. Re-verify canonical signed policy bytes at the security boundary.
5. Atomically advance anti-rollback state before policy use.
6. Pass only the resulting immutable policy snapshot to receipt and evidence verifiers.
7. Call the independent provenance gate, which remains closed until all external evidence layers are independently provisioned and reviewed.
8. Emit an auditable decision record containing exact input hashes, state generation, policy sequence, clock source, revocation evidence and all blockers.

The existing `inspect_signed_root_attestation_chain` composition is suitable for research diagnostics only. It does not satisfy items 1–3 or 5, and `verify_independent_provenance` remains `BLOCKED_PROVENANCE`.

## 8. Acceptance tests before any production implementation

A future platform adapter must include integration tests against a real isolated monotonic-state backend and authenticated time source. Required adversarial cases include:

- substituted root key, root key ID or policy domain;
- restored old disk/container snapshot and counter reset;
- lower policy sequence and same-sequence/different-digest equivocation;
- concurrent policy updates and compare-and-swap conflict;
- backend outage, stale replica, split brain and interrupted commit;
- clock rollback, future policy, expired policy and uncertainty overflow;
- revoked, unknown and stale OCSP/CRL status;
- root rollover, emergency recovery and compromised-root procedures;
- caller attempts to pass a fabricated `VerifiedTrustPolicy`, boolean or callback;
- all failures leave `verify_independent_provenance` at `BLOCKED_PROVENANCE`.

Synthetic unit fixtures must remain in a clearly segregated test namespace. They cannot be counted as institutional evidence or live prospective draws.

## 9. Non-promotion status

This document does not implement a trust-anchor provider, anti-rollback backend, trusted clock, revocation client, institutional delegation, or custody system. No ACR2-SE certificate bytes or fingerprint are claimed as captured. The adapter remains fail-closed:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`

No production promotion is authorized by this specification.
