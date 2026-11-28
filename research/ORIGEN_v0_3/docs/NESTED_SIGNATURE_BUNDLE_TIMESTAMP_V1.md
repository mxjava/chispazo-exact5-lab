# ORIGEN v0.3 — detached nested-signature bundle timestamp v1

**Classification:** RESEARCH ONLY / FAIL CLOSED. This is a new diagnostic sidecar interface. It does not enable production or establish institutional provenance.

## Why a sidecar is required

The physical manifest's nested signatures cover the manifest claims. Inserting the digest of a timestamp token for those same signatures into the signed manifest would create a circular dependency: the token depends on the signatures, while the signatures would depend on the token digest.

This increment therefore constructs a separate canonical bundle after the manifest signatures exist. The bundle contains:

- the canonical manifest content with only `ledger_anchor.inclusion_proof_sha256` omitted, plus its normalized commitment SHA-256;
- the exact original signed V3 policy-envelope bytes and their SHA-256;
- every original physical artifact byte string, base64-encoded and keyed by its SHA-256;
- every declared nested signature claim; and
- every exact 64-byte Ed25519 signature, base64-encoded and keyed by its SHA-256.

An RFC 3161 token's message imprint is verified over the canonical bundle bytes. This proves, relative to the caller-supplied TSA root and clock, that the normalized manifest claims, exact policy bytes, original artifact bytes and complete nested-signature set existed no later than the token's accuracy upper bound. The exact raw manifest hash is returned separately for later ledger verification; the ledger-derived inclusion-proof digest is deliberately excluded from the timestamp bundle.

## Verification contract

The entry point is `verify_nested_signature_bundle_timestamp_v1`.

It:
1. parses the exact CLASSIC manifest and snapshots the exact artifact and signature byte maps;
2. rejects missing, extra, duplicate, substituted or mutable artifact bytes and missing, extra, substituted, mutable or non-Ed25519 signature bytes;
3. invokes the V3 physical verifier to re-check artifact digests, lengths, signature digests, nested Ed25519 signatures and signed key/role/artifact authorization;
4. verifies the exact V3 policy envelope against the supplied root pin, key ID, CLASSIC domain and minimum sequence;
5. includes every exact original artifact byte string and every exact signature byte string in the canonical timestamped bundle;
6. verifies the RFC 3161 token over the exact canonical bundle, including expected nonce, TSA root fingerprint and policy OID;
7. requires explicit accuracy and requires its upper bound to be strictly before the manifest's CLASSIC 21:00 close;
8. checks that the full timestamp accuracy interval is within policy validity and every signer's key validity interval; and
9. returns per-signature existence-by-upper-bound and key/role-at-timestamp diagnostics.

The sidecar is deliberately not injected into the manifest signature payload. There is also a ledger cycle to avoid: the manifest's inclusion-proof digest depends on a ledger entry, and that entry must later commit to the timestamp bundle. Therefore the bundle omits only `ledger_anchor.inclusion_proof_sha256`, matching the existing nested-signature payload and manifest-commitment normalization. The ledger verifier must still validate the exact raw manifest bytes and exact inclusion-proof bytes. The returned `ledger_binding_status` is currently `NOT_BOUND_TO_LEDGER_ENTRY`; a subsequent ledger-entry v2 must commit to the normalized manifest commitment, bundle SHA-256 and timestamp-token SHA-256, then be checked through inclusion, consistency, witnesses and provider CAS.

## Important non-claims

- **No exact signature creation instant is proven.** RFC 3161 proves that the exact signature bytes existed by the accuracy upper bound. It does not prove when the signer created them.
- **Key authorization at signature creation remains unproven.** A signer could create a signature before a key's validity begins and obtain its timestamp afterward. The signature payload currently has no unpredictable, provider-issued signer challenge bound into it. The result explicitly returns `UNPROVEN_NO_SIGNER_CHALLENGE_BOUND_TO_SIGNATURE`.
- **Role authorization is only a match to the root-signed V3 policy.** The supplied root is not institutionally provisioned and the signer identity/delegation is not independently authenticated.
- **TSA trust is not provisioned.** The TSA root, expected policy OID, nonce and verification clock remain caller inputs. Certificate revocation/OCSP freshness is not checked.
- **Ledger inclusion is not verified for this sidecar.** A successful token check alone does not anchor the bundle in the independently witnessed ledger.
- **Physical truth and custody are not established.** Matching bytes and valid signatures do not prove the draw machine, balls, weighing, official procedure or independent custody.
- **All tests use ephemeral synthetic keys, policies, manifests, signatures and TSA certificates.** No institutional key or official draw artifact is used.

Every successful inspection remains `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Adversarial test coverage

The isolated tests cover exact bundle imprint, proof-digest normalization (changing only the ledger inclusion-proof digest leaves the sidecar payload unchanged), complete signature set, missing/extra signatures, artifact-byte substitution, signature-byte substitution, wrong imprint, nonce mismatch, wrong TSA policy OID, and the strict CLASSIC close boundary. The tests assert that key authorization at creation remains unproven and that the sidecar is not yet ledger-bound.

## Next required integration

1. Add the exact bundle bytes and token DER to the provider CAS evidence envelope and operation identity.
2. Extend the ledger-entry schema so the signed/included ledger leaf commits to the bundle SHA-256 and timestamp-token SHA-256.
3. Verify that exact ledger entry, inclusion proof, checkpoint consistency and independent witness observations before any provider CAS.
4. Add a pre-draw signer challenge to the signed signature payload if authorization at the actual creation event is required.
5. Provision TSA roots, policy OIDs, revocation state, ledger roots and monotonic floors out of band.

No existing PR is merged or promoted by this branch. V294 and the canonical history remain untouched.
