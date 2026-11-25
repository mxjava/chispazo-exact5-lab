# ORIGEN — RFC 3161 timestamp-token verifier v1

**Classification:** research-only diagnostic. This verifier cannot authenticate physical provenance or change the production gate.

## Purpose

Add a bounded verifier for a real RFC 3161 Time-Stamp Token (TST) encoded as CMS SignedData. The caller supplies the exact artifact bytes and a separately pinned TSA root certificate. The result reports what the token cryptographically binds while keeping all deployment trust inputs explicitly unauthenticated.

The module is standalone. It is not yet wired into trust_receipt_v1, the physical-evidence manifest, or verify_independent_provenance. A manifest claim containing a proof digest is not itself proof verification.

## Verified by this module

- Bounded exact-byte DER parsing of ContentInfo, TSTInfo, certificates and CMS structures.
- Exactly one CMS signer, using issuer-and-serial-number signer identification.
- CMS signed attributes restricted to one contentType=tst_info and one messageDigest; the message digest must match the encapsulated TSTInfo bytes.
- Exact artifact binding: TSTInfo message imprint is recomputed over the exact supplied data bytes. SHA-256, SHA-384 and SHA-512 are accepted; weaker/unknown digests are rejected.
- Optional request nonce equality, when the caller supplies an expected nonce.
- TSA leaf certificate must contain a critical EKU consisting only of id-kp-timeStamping, and KeyUsage must allow digital signatures.
- Certificate signatures are checked along an unambiguous chain to the separately pinned root. Certificate validity is checked at genTime; CA BasicConstraints and KeyUsage must be critical and authorize certificate signing; path-length limits are enforced; the root must verify as self-signed.
- genTime, serial number, policy OID, accuracy (microseconds) and ordering are returned for downstream chronology checks.

The implementation currently supports CMS RSA PKCS#1 v1.5, ECDSA, Ed25519 and Ed448 signatures. It accepts only SHA-256/384/512 for the CMS digest and certificate-signature digest. RSA-PSS CMS signer signatures and subject-key-identifier CMS signer IDs are rejected rather than guessed.

## Fail-closed handling of unsupported RFC 5280 path semantics

The verifier now rejects a certificate path when it encounters any of the
following unsupported path-processing extensions, whether marked critical or
non-critical:

- Name Constraints;
- Certificate Policies;
- Policy Mappings;
- Policy Constraints;
- Inhibit Any-Policy.

It also rejects every critical certificate extension that the verifier does
not explicitly process. For CA certificates, the handled critical extensions
are Basic Constraints and Key Usage. CA Extended Key Usage is rejected because
its path restriction semantics are not implemented. For the TSA signer
certificate, Basic Constraints, Key Usage, and the critical timeStamping-only
Extended Key Usage are checked; a signer certificate marked CA is rejected.

This is intentionally restrictive. It prevents the diagnostic verifier from
silently accepting a path whose constraints it does not understand. It does
not make the implementation a complete RFC 5280 validator: revocation and
freshness, certificate-policy processing, name-constraint evaluation, policy
mappings, and institutional designation remain unavailable. A real chain
containing one of the unsupported extensions will be rejected rather than
treated as valid.

Synthetic adversarial tests cover an unhandled critical extension on the TSA
leaf and pinned root, plus Name Constraints and non-critical Certificate
Policies on the root. These fixtures are generated test certificates only.

## Explicit non-guarantees

This is not a complete RFC 5280 path-validation engine. It does not evaluate name constraints, certificate policies, policy mappings, CRL distribution points, OCSP, revocation freshness, or every critical extension. It does not authenticate the TSA's institutional identity or authorize the returned policy OID.

The root certificate bytes and expected SHA-256 fingerprint are caller-supplied. The verification clock is caller-supplied. Neither input is authenticated by this module. It does not establish trusted time merely because a syntactically valid TST contains genTime. It also does not establish original-byte acquisition, independent custody, the truth of physical records, or pre-close timing relative to a Chispazo contest.

accuracy_microseconds is exposed, not silently treated as zero. A future close-time gate must compare the timestamp interval implied by genTime and accuracy with the independently established contest close. ordering is preserved but is not a substitute for a trusted sequence or ledger.

Every successful diagnostic returns:
- trust_anchor_source = CALLER_SUPPLIED_UNAUTHENTICATED
- verification_clock_source = CALLER_SUPPLIED_UNAUTHENTICATED
- revocation_status = NOT_CHECKED
- provenance_status = BLOCKED_PROVENANCE

## Synthetic validation

The tests generate an ephemeral RSA TSA key, a synthetic self-signed root, a synthetic TSA leaf certificate, and CMS/TSTInfo bytes at test time. No institutional key, live TSA, production timestamp, Lotería Nacional record, or physical artifact is included.

Adversarial cases cover exact artifact imprint mismatch, nonce mismatch and omission, wrong root fingerprint, invalid CMS signature, non-critical TSA EKU, trailing bytes/non-DER input, verification time before genTime, root certificate included in the CMS certificate set, and preservation of timestamp accuracy.

## Deployment prerequisites before any real use

1. Obtain the TSA root certificate and fingerprint through an independently authenticated institutional channel, not from the token or the same uploader.
2. Record the authority's legal designation, permitted TSA policy OIDs, key ownership, rotation and revocation procedure under independent review.
3. Add authenticated revocation checking and full PKIX path validation.
4. Obtain actual RFC 3161 tokens over archived original artifact bytes; preserve token, certificate chain, request nonce, TSA policy OID, accuracy and original-byte hashes under independent custody.
5. Bind the token digest and event identity to the physical manifest/receipt, then verify contest modality and close-time chronology independently.
6. Keep the adapter fail-closed until independent custody, institutional provisioning and all prospective Exact5 gates are satisfied.

No production status, predictive edge, or betting authorization is implied by this verifier.
