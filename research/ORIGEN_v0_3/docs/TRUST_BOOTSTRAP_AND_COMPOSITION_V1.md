# ORIGEN v1 — deployment trust bootstrap and root-receipt composition

**Status: RESEARCH ONLY / NO AUTHENTIC DEPLOYMENT BOOTSTRAP PROVISIONED / PRODUCTION BLOCKED**

## What changed

The adapter now has one private composition path:

1. Load one deployment-owned bootstrap snapshot.
2. Verify the signed policy envelope against its separately pinned Ed25519 root key, expected root key ID, minimum accepted policy sequence and supplied verification time.
3. Pass the resulting `VerifiedTrustPolicy.policy` directly to `verify_receipt_attestation` in the same call path.
4. Return no public authenticated status. Even a valid root attestation is insufficient to establish physical provenance.

The public `verify_independent_provenance(original_receipt_bytes)` accepts no caller-provided keys, policy objects, clocks, callbacks or reference sets. Its bootstrap loader currently returns `None`, so it returns `BLOCKED_PROVENANCE`. If a future deployment provisions the first cryptographic layer, the public adapter still returns `BLOCKED_PROVENANCE` until all downstream verifiers are independently deployed and reviewed.

The helper's `CryptographicallyVerifiedReceipt` result means only that the receipt's root Ed25519 signature verified against a policy that was itself signed by the pinned root. It does not authenticate any embedded claim. Python dataclasses and private function names are not unforgeable capabilities; the trust boundary is the controlled deployment process and its immutable code/configuration.

## Out-of-band provisioning contract

No institutional root key, key identifier, policy sequence store, trusted clock, TSA, ledger or custodian has been authenticated for this repository. Do not invent or reuse a test key. Before provisioning:

1. **Identify the policy authority independently.** Establish its legal identity and authority through an independently obtained institutional channel. The policy signer must not be the model operator or evidence submitter. A Lotería Nacional result page is not, by itself, a trust-root publication.
2. **Pin the root outside the repository.** Obtain the 32-byte Ed25519 public key and key ID through a two-person, out-of-band ceremony. Compare the full SHA-256 fingerprint through a second independent channel. Install the pin in an immutable deployment image or OS-protected configuration owned by the deployment administrator (read-only to the application submitter). Do not source it from the receipt, policy envelope, request, repository file, user-writable environment variable, CI variable or downloaded metadata.
3. **Persist anti-rollback state independently.** The minimum policy sequence must live outside the downloaded envelope and outside the same replaceable filesystem snapshot. Preferred options are a TPM/HSM monotonic NV counter or an independently witnessed append-only ledger checkpoint. A file-only fallback is acceptable only if its owner, ACL, integrity and backup/restore behavior are independently controlled and rollback is detected; otherwise provisioning is not complete and the adapter stays blocked.
4. **Advance sequence atomically.** Verify the envelope signature and chronology first; require `policy_sequence >= stored_minimum`; reject lower values. Commit a higher accepted sequence with compare-and-swap/transactional semantics and durable flush. A failed write, ambiguous state, restore from older backup, counter mismatch or unavailable witness must fail closed. Never update the floor from an unverified envelope.
5. **Provision time separately.** The current functions receive a caller-supplied datetime; this is not trusted time. A deployment must bind policy/receipt checks to an independently authenticated clock or validated RFC 3161 token, with TSA chain, policy, nonce/imprint, generation time and revocation checks. Clock rollback or unavailable time must block.
6. **Define rollover and revocation.** Root rollover requires a documented dual-control ceremony, old-root authorization of the new root (or equivalent independently verified ceremony), new fingerprint confirmation, monotonically increasing sequence and explicit overlap/revocation windows. Emergency revocation must be independently distributed and recorded.
7. **Separate roles.** Policy authority, root-attestation issuer, artifact signers, SEGOB/Lotería representatives, generator and external custodian must be authenticated as distinct authorized roles; different strings or keys alone do not prove different legal entities.

## Full evidence chain still required

The root-policy/receipt composition is only layer 1. Before any authenticated provenance result could be considered, a separately reviewed pipeline must also verify:

- original source bytes from controlled intake, byte length and local SHA-256 against a signed manifest;
- nested signer signatures and role authorization against the verified policy, including revocation and separation of duties;
- RFC 3161 tokens cryptographically, not just timestamp strings or proof digests;
- external append-only ledger entry, inclusion proof, independently witnessed head and non-rollback checkpoint;
- custody receipt, custodian identity and independence from generator/model operator;
- official physical records and source bytes, including modality/contest binding;
- two independently generated Exact5 output seals with complete bytes, signer bindings and trusted pre-close time proofs;
- preregistration, candidate/code/environment hashes and untouched target list.

No caller-created booleans, strings, status labels or `VerifiedTrustPolicy` object may substitute for this chain. The signed envelope must be verified inside the trusted call path from the out-of-band root pin.

## Test scope

`test_trust_policy_receipt_composition.py` generates synthetic Ed25519 root and issuer keys in process and tests successful composition, wrong root, sequence rollback, receipt tampering, type substitution, no caller injection and the invariant that the public adapter remains blocked even when a synthetic root chain verifies. These fixtures are software tests only and are not institutional evidence.

## Acceptance state

- `verify_independent_provenance`: `BLOCKED_PROVENANCE`.
- `research_edge`: false.
- Production: `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
- V294: frozen.
- Canonical history `data/history/Chispazo_through_12249.csv`: unchanged; expected Git blob SHA-1 remains `2f5ff5bfbd779fe505736398e417b7211955958e`.
- No main write, merge or production promotion.


## Research implementation: signed external ledger inclusion (2026-11-26)

`external_ledger_v1.py` adds a bounded RFC 6962-style Merkle inclusion verifier and Ed25519-signed tree-head verification. It checks the exact leaf bytes, domain-separated leaf/node hashes, inclusion path, signed root, log identity, and a caller-supplied minimum tree size. Adversarial tests cover all leaf positions in trees of sizes 1–9, non-power-of-two trees, leaf/path tampering, wrong log key/identity, rollback floor, boolean-as-integer substitution, overlong paths, and signed-head tampering.

**This is a verification primitive, not an authenticated ledger deployment.** The log public-key pin, expected log identity and minimum tree size are still inputs to the function. No persistent monotonic checkpoint, independent witness, consistency-proof verification, log-operator identity, or custody is provisioned. The primitive is not wired into `verify_independent_provenance`; public provenance remains `BLOCKED_PROVENANCE`. Fixtures use generated in-process Ed25519 keys and are synthetic only.
