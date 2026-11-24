# ORIGEN v0.3 — physical provenance trust-boundary gap
Date: 2026-11-24
Audited branch: `research/origen-exact-decimal-metrology-20261124`
Scope: read-only architecture audit; no change to acceptance semantics.

## Verified code facts

1. `physical_intake.py` validates the presence/shape of `source_document_sha256` and `source_document_ref`, checks the digest's lowercase SHA-256 syntax, and groups records by contest. It does not open the referenced source document, recompute its digest, or verify a source-document signature.
2. `signed_envelope.py` implements detached Ed25519 verification against a trust-store byte string and a caller-supplied SHA-256 pin. Its module contract requires the pin and verification time to come from deployment-controlled configuration/services, not submitted evidence.
3. `trust_receipt_v2.py` enforces structural digest/time-proof bindings. Its module contract expressly does not authenticate signer signatures, key ownership, identity, or physical provenance.
4. `crypto_primitives.py` verifies a raw Ed25519 signature only; it does not decide trust, role authorization, timestamping, or custody.
5. The current physical intake path does not invoke the detached envelope verifier or the V2 receipt parser as a mandatory provenance gate.

## Security consequence

A structurally valid intake row can pass source-digest syntax checks without proving that the referenced bytes exist, that their bytes hash to the declared digest, that a recognized institution signed them, or that the signer had authority over the relevant physical record. Likewise, a structurally consistent V2 receipt is not proof that its asserted time authority or signer is authentic.

Do not interpret `usable` in the structural intake report as authenticated physical evidence. It means only that the implemented structural/time/mapping/metrology checks did not quarantine those rows.

## Integration prerequisites — all fail closed

1. **Canonical source package contract:** define an exact, versioned signed-manifest payload that binds contest ID, modality (`CLASSIC` versus `TRES`), draw date/time, source-document digest(s), calibration-document digest(s), weighing-record digest(s), and the referenced immutable byte objects. Reject duplicate keys, unknown fields, noncanonical encoding, ambiguous references, and digest/byte mismatches.
2. **External trust governance:** identify the independent institution(s) authorized to sign each evidence class; establish key issuance, identity proofing, rotation, revocation, validity windows, compromise response, and separation of duties. Role names and key owners must come from that governance process, not be invented in code.
3. **Out-of-band trust-store pin:** provision the trust-store bytes and expected digest through deployment-controlled configuration with an independently controlled change/audit path. Never accept a trust-store pin from the evidence package itself.
4. **Trusted time:** define the accepted timestamp authority, verification-time source, timestamp-token format, revocation behavior, and the exact signed subject bytes. A timestamp string or a digest link alone is not trusted time.
5. **Mandatory adapter:** add one fail-closed intake entry point that receives immutable source bytes plus deployment-supplied trust configuration, verifies envelope role/signature/time/key status, binds the signed manifest to every source byte digest, and only then invokes structural row validation. The current CSV-only function must not silently imply authentication.
6. **Independent custody:** obtain actual original records and custody attestations for specific Classic draws, including signed official result/report, signed weighing strip, instrument/calibration evidence, and independently retained pre-close outputs. Hashes must be computed from captured original bytes and independently reproduced.
7. **Adversarial tests:** wrong pin, untrusted/aliased/revoked key, wrong role, future issuance, expired key, signature mutation, payload substitution, byte/digest mismatch, wrong modality/contest binding, missing source bytes, replayed evidence, duplicate references, and compromised/rotated key scenarios must all fail closed.

## Explicit non-claims

This audit does not claim that any authority, signer, trust-store pin, source PDF, calibration certificate, physical weighing strip, or independent custody record has been obtained. No real-world signer identity or key is provisioned by this repository change.

## Disposition

The Ed25519 and V2 primitives are useful components, but wiring them into production eligibility before external trust governance exists would create false assurance. Keep physical provenance blocked until prerequisites 1–6 are met and independently evidenced. No changes to V294, model parameters, historical canonical CSV, `main`, merge status, or production status are authorized by this audit.
