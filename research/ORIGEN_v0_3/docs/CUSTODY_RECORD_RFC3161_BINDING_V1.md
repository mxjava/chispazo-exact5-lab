# ORIGEN — non-circular RFC 3161 custody-record binding v1

**Classification:** research-only diagnostic. No production enablement, institutional trust, or predictive edge is implied.

## Purpose and non-circular construction

This adapter composes the existing V3 receipt/custody verifier with the bounded
RFC 3161 token verifier. It timestamps the **exact canonical custody-record
bytes**, not the detached custodian signature.

That distinction avoids a circular dependency in the current V3 format:

1. The detached V3 custody signature covers the receipt digest.
2. The root-signed receipt carries the digest of each declared timestamp token.
3. If that token timestamped the detached signature, changing the receipt to
   include the token digest would change the receipt digest, which changes the
   detached signature, which changes the timestamped bytes and token digest.

The v1 adapter therefore binds a timestamp to the record bytes, whose digest is
already referenced by the receipt's custodian claim. The receipt then binds the
token digest and event identity. It does **not** timestamp the detached
signature and must not be described as proof that the signature existed before
the draw close.

A future pre-close signature timestamp requires a new non-circular signature
payload/version that does not itself depend on the final receipt digest, or a
separate independently anchored evidence object with a reviewed binding design.

## Verification contract

The adapter requires:

1. The existing V3 receipt-attestation and detached custody signature checks
   to succeed, while their independent provenance result remains
   `BLOCKED_PROVENANCE`.
2. The RFC 3161 message imprint to match the exact original custody-record
   bytes, not a reserialized object or reconstructed digest.
3. The token SHA-256 to match exactly one `trusted_time_proofs` claim in the
   root-signed receipt.
4. The proof authority to match the caller's expected TSA authority identifier.
5. The event ID to equal
   `custody-record-sha256:<SHA256 of exact custody-record bytes>`.
6. The receipt proof event time to equal the token's `genTime`.
7. A present RFC 3161 accuracy field. An absent accuracy field cannot establish
   a bounded interval for this adapter.
8. The complete accuracy interval `[genTime - accuracy, genTime + accuracy]`
   to start at or after the custody record's claimed `received_at_utc` and end
   strictly before its declared Classic draw close.
9. The RFC 3161 nonce, token imprint, TSA certificate path, and caller-supplied
   root fingerprint checks to succeed.

The wrapper normalizes the caller's verification time once and supplies that
stable UTC instant to both the custody and TSA verifiers.

## Explicit limits

A successful result means only that the exact record bytes have a cryptographic
RFC 3161 token match relative to the caller-supplied TSA root, fingerprint,
authority ID, nonce, and verification clock. It does not prove:

- that the TSA is designated or operated by Lotería Nacional, SEGOB, or another
  institution;
- that the caller-supplied root fingerprint or clock is authentic;
- that the detached custodian signature itself existed before draw close;
- certificate revocation freshness, complete RFC 5280 path validation, or
  authorization of the TSA policy OID;
- the custodian's legal identity, institutional delegation, or administrative
  independence;
- original acquisition, storage controls, physical-event truth, or independent
  custody;
- ledger inclusion/consistency/witness quorum, nested physical signatures, or
  two independently sealed pre-close outputs;
- any predictive edge or production eligibility.

The result preserves `BLOCKED_PROVENANCE` and retains the existing custody
signature trusted-time blocker. It additionally reports that the detached
signature itself is not timestamped. The adapter does not call or modify the
independent provenance gate; the V3 custody verifier already invokes it and
requires the exact blocked status.

## RFC 3161 accuracy syntax

RFC 3161 §2.4.2 permits `millis` and `micros` only in the range 1..999 when
present. Absence means zero; explicit zero is invalid. The underlying token
verifier now rejects explicit zero and has synthetic boundary tests.

## Synthetic validation

`test_custody_record_timestamp_integration_v1.py` uses generated Ed25519
custody/policy keys, generated RSA TSA keys and certificates, synthetic
receipts, records, portfolios and RFC 3161 tokens. It covers exact-byte
imprint binding, receipt proof digest and event identity binding, authority
and genTime mismatches, nonce/root mismatch, missing accuracy, both accuracy
interval boundaries, and a stateful caller timezone.

No test fixture is an institutional artifact or real Chispazo physical record.
