# ORIGEN — signed policy, receipt and RFC 3161 output-seal integration v1

**Classification:** research-only diagnostic. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Implemented composition

The integration verifies, in order:

1. the canonical signed trust-policy envelope against a separately supplied Ed25519 root;
2. the receipt root attestation using the resulting `VerifiedTrustPolicy.policy`;
3. the existing independent-provenance adapter, which must still return exactly `BLOCKED_PROVENANCE`;
4. a root-signed timestamp-authority policy bound to the exact trust-policy envelope digest and sequence;
5. both RFC 3161 tokens against the exact output-seal signature bytes.

The new `timestamp_authority_policy_v1.py` envelope binds:
- the authority ID declared by both output-seal time proofs;
- the SHA-256 fingerprint of the TSA root certificate;
- the allowed RFC 3161 policy OIDs;
- the authority validity interval and a signed revocation flag;
- the exact trust-policy envelope SHA-256, root key ID and policy sequence.

The TSA policy must be signed by the same Ed25519 root as the trust-policy envelope. Its trust-policy digest and sequence must match the policy that was just verified. This prevents a valid but unrelated TSA policy from being mixed with a different issuer policy.

For each output seal, the integration requires:
- the exact DER token SHA-256 to equal both the signed receipt's `trusted_time_proofs[].proof_sha256` and the seal's `timestamp_proof_sha256`;
- the event ID to match the signed receipt;
- both output-seal proofs to name the same TSA authority, and that authority to exist, be unrevoked, and be valid in the root-signed TSA policy;
- the caller-supplied TSA root certificate SHA-256 to match the root-signed authority binding;
- the RFC 3161 policy OID to be explicitly allowed for that authority;
- the SHA-256 of the exact supplied signature bytes to equal the signed receipt's `signature_sha256`;
- the RFC 3161 message imprint to match those exact signature bytes;
- `genTime` to match the signed event time and declared seal creation time;
- the token nonce to match the supplied request nonce;
- RFC 3161 accuracy to be present and its upper time bound to be strictly before the receipt's declared Classic close.

The two tokens are matched by signed proof digest and event identity, not array order. Missing, duplicate, extra, mismatched, stale, future, unauthorized, or ambiguous evidence fails closed.

## Deliberate limitation: receipt-attestation timestamp remains unresolved

The V1 receipt schema places `receipt_attestation.timestamp_proof_sha256` and its matching `trusted_time_proofs` entry inside the receipt payload covered by the root Ed25519 signature. If the timestamp token imprints the root signature bytes, the root signature depends on the token digest while the token digest depends on the root signature bytes. That is a self-referential construction.

This branch does not weaken the receipt signature, omit fields from the signed payload, or pretend the token is verified. It leaves `RECEIPT_ATTESTATION_RFC3161_TIMESTAMP_TOKEN_NOT_VERIFIED` as an explicit blocker. The correct future interface is a versioned detached outer proof envelope, or a two-stage signed object with a formally specified non-circular commitment.

## Trust boundary still not established

The following remain caller-supplied or incomplete:
- deployment root public key, root key ID, minimum policy sequence and verification clock;
- TSA root certificate bytes, expected request nonces and the out-of-band provisioning of the root-signed TSA policy;
- legal/institutional designation of the policy root and TSA, and authenticated role authorization;
- CRL/OCSP and revocation freshness;
- complete RFC 5280 path validation (the standalone verifier implements a bounded subset);
- nested signer and custodian signatures, identities and role authorization;
- actual original physical records, physical sphere identity/number mapping, 28 individual masses, calibration, machine/set assignment and incident history;
- independently controlled immutable acquisition, custody receipts, ledger-head anchoring and split-view-resistant witnesses;
- two independently sealed prospective Classic outputs and all statistical edge gates.

The returned result is diagnostic only. It does not authenticate a TSA institution, establish real-world time, prove that a draw record is true, or change the independent adapter's status. All keys, certificates, CMS tokens and signature bytes in tests are generated synthetic fixtures.

## Out-of-band provisioning contract

Before any future use, an independent deployment authority—not the receipt submitter, repository maintainer, model operator, or this code—must perform and document:

1. **Root-key ceremony:** generate and retain the Ed25519 root private key under dual control; record the key ID, public-key fingerprint, activation/expiry, authorized scope, custodians, revocation authority and recovery procedure.
2. **Independent publication:** publish the root public key and fingerprint through at least two independently authenticated institutional channels. A key embedded in the envelope, Git repository, receipt, or supplied by the same evidence uploader is not an external trust anchor.
3. **Immutable deployment pin:** provision the exact 32-byte root public key and key ID into reviewed, access-controlled deployment configuration. Root replacement requires independent approval and a signed transition.
4. **Monotonic policy state:** store the minimum accepted sequence outside the caller and outside the downloaded envelope, using a separately reviewed rollback-resistant facility. Reject unavailable, corrupt, rolled-back or inconsistent state. Persist the accepted sequence atomically with compare-and-swap; never lower it during restore or failover.
5. **TSA authorization:** obtain the TSA certificate root fingerprint, permitted policy OIDs, legal authority, validity and revocation channel from an independently authenticated institutional source; sign these bindings under the same provisioned policy root and bind them to the exact trust-policy envelope digest and sequence.
6. **Time and revocation:** provision an independently authenticated verification clock, authenticated CRL/OCSP or equivalent revocation freshness, and emergency revocation behavior. A caller clock, local JSON file, environment variable, command-line floor, or self-declared authority ID is not sufficient.
7. **Custody and audit:** retain signed ceremony records, root/TSA policy envelope bytes, approval identities, sequence transitions, fingerprints, revocation evidence and original source bytes under independently controlled custody.

No institutionally authenticated Ed25519 root, TSA certificate, or authorized TSA policy OID was obtained in this run. The policy envelope implemented here is a testable interface, not an assertion that Lotería Nacional or SEGOB has issued such a trust root.

## Synthetic adversarial validation

The integration tests use ephemeral keys, certificates and CMS tokens generated during the test run. They cover:
- valid root-policy/receipt/TSA-policy composition while provenance remains blocked;
- TSA authority ID absent from the signed authorization;
- signed revocation flag;
- caller-supplied TSA root fingerprint mismatch;
- unapproved RFC 3161 policy OID;
- TSA policy bound to the wrong trust-policy digest or sequence;
- TSA policy signature tampering;
- token digest and exact-signature imprint mismatch;
- event-time mismatch, missing accuracy and accuracy interval crossing the declared close;
- missing and duplicate output-seal evidence and order independence.

Synthetic fixtures are not institutional identities, production roots, trusted clocks, TSA tokens, original draw records or custody evidence.

## Validation and guardrails

- Parent of this integration stack: PR #49 exact head `c0c98d0843aaa53c7d8ec078ccf0a3b14a916e29`.
- PR #50 supplied the separately tested RFC 3161 CMS verifier; this branch binds its returned root fingerprint and policy OID to a root-signed authorization envelope.
- The independent provenance adapter remains unchanged and returns only `BLOCKED_PROVENANCE`.
- PR #13 remains separate, OPEN/DRAFT and untouched.
- No writes to `main`, no merge or promotion, no V294 change, no canonical-history modification, no model retuning, and no prospective ledger writes.
