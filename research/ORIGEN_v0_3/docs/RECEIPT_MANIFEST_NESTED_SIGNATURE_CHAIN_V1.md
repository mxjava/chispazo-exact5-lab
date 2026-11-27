# ORIGEN v0.3 — receipt/manifest/nested-signature composition v1

**Classification:** RESEARCH ONLY / FAIL CLOSED. This composition does not authenticate provenance and cannot enable production.

## Scope

This increment extends the receipt-to-manifest binding from the parent research line. It consumes:

- the exact original root-signed receipt bytes;
- the exact canonical physical-evidence manifest bytes;
- the exact original bytes for all 17 manifest artifacts plus the manifest itself;
- the exact detached signature bytes declared by the manifest;
- a VerifiedTrustPolicy produced by the signed policy-envelope verifier;
- an explicit verification instant.

The public entry point is verify_independent_provenance_with_nested_signatures.

## Verification order

1. The existing verify_independent_provenance_with_physical_manifest composition verifies the supplied policy/receipt root-attestation layer, requires the policy's exact 18-artifact set, binds the receipt to the exact manifest bytes, checks the Classic target identity and close, and verifies every original artifact byte length and SHA-256.
2. The new layer requires the exact detached-signature digest set declared by the manifest. Missing and extra signatures are rejected.
3. It re-hashes each detached signature byte string and rejects digest mismatch.
4. It builds a unique (subject_id, key_id) index from the issuer keys in the already-verified policy. Unknown identities, duplicate identities, duplicate public-key material, revoked keys, invalid validity intervals, and keys outside validity at the supplied verification instant are rejected.
5. Each declared algorithm must be Ed25519. Every detached signature is verified over the domain-separated canonical manifest-claims payload using origen.physical-evidence-signature.v1.

The signed payload covers the complete manifest claim set. Only signature_sha256 fields are omitted to avoid a circular dependency; the exact signature bytes are separately bound by those digest claims. Since the manifest commits to the artifact digests and the parent composition binds the manifest and all artifact bytes to the root-signed receipt, the nested signatures cover those declarations transitively.

## Explicit non-claims

A successful result means only that the receipt/manifest/artifact byte chain is internally consistent and that every declared nested Ed25519 signature verifies relative to the supplied policy.

- **Signer roles are not authorized.** Policy v1 binds issuer/key identities but contains no key-to-role-to-artifact authorization. The manifest role remains UNVERIFIED_CLAIM_ONLY, even though the role string is covered by the signature.
- **Signature creation time is not proven.** The manifest has no per-signature RFC 3161 proof binding. Key validity at verification time does not prove that a signature existed before the 21:00 Classic sales close.
- **Trusted time is not authenticated.** The verification instant is caller-supplied. No TSA root provisioning, revocation freshness, or trusted clock is established.
- **Ledger is not verified.** This increment does not verify inclusion, signed checkpoint continuity, witness quorum, independent ledger operation, or monotonic head persistence.
- **Custody is not verified.** It does not verify detached custodian signatures, custodian identity, transfer events, storage immutability, or independent retention.
- **Physical truth is not established.** Valid signatures and matching bytes do not prove that the declared records describe the actual machine, ball set, weighing process, or draw.
- **Deployment trust is not provisioned.** The root key, key ID, minimum policy sequence, and clock remain caller/deployment inputs. VerifiedTrustPolicy is an application-level misuse guard, not an unforgeable capability against arbitrary code in the same Python process.

Every successful inspection remains exactly BLOCKED_PROVENANCE. The result contains digest/identity diagnostics, not source artifact or signature payload bytes.

## Adversarial fixture separation

The tests generate ephemeral Ed25519 keys, receipts, physical manifests, artifact payloads, and detached signatures in memory. These are synthetic fixtures only. They are not Lotería Nacional, SEGOB, OIC, TSA, custodian, or other institutional identities and must never be reused outside tests. No real institutional key or draw-specific original evidence is included.

Coverage includes valid composition, signature digest mismatch, missing/extra signature bytes, re-hashed invalid signatures, role-claim tampering, unknown signer identity, revoked signer keys, unsupported algorithms, exact container types, and key validity at verification time.

## Next interfaces

The next substantive work should compose, on exact original bytes and the same Classic target:

1. a signed policy that authorizes signer roles and artifact classes;
2. RFC 3161 tokens that bind the relevant signed records and signature bytes, with independently provisioned TSA trust and revocation;
3. the manifest-bound RFC 6962 ledger inclusion proof, checkpoint consistency, and independent witness observations;
4. detached custody receipts, authorized custodian identities, and transfer/retention continuity;
5. an independently provisioned root anchor, rollback-resistant policy/ledger state, and authenticated time.

These interfaces must consume original proof bytes, reject missing/extra/aliased inputs, and keep synthetic fixtures segregated. No layer may change the provenance status until independent deployment and institutional evidence are actually established.

## Protections

V294 remains frozen. The canonical historical file data/history/Chispazo_through_12249.csv is not changed. No write to main, no merge, no promotion, and no model retuning occur in this branch. Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
