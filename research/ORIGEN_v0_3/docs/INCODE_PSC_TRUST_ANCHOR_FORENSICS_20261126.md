# ORIGEN v0.3 — Incode PSC trust-anchor forensics (2026-11-26)

**Classification:** public-source reconnaissance; no certificate is pinned; no provider is provisioned; RESEARCH ONLY.

## Primary-source findings

1. Secretaría de Economía's PSC directory lists **INCODE PSC, S. de R.L. de C.V.** with accreditation for digital time stamps and conservation of data messages, dated 22 May 2024. The corresponding DOF notice identifies the accreditation and points interested parties to Incode's public repository.
2. Incode's Mexican PSC public repository lists the second root certificate of Secretaría de Economía (`ACR2_SE.cer`) and two time-stamping authority certificates (`SDT_Frankfurt.cer`, `SDT_Milan.cer`).
3. Incode's public-document repository lists:
   - Time-stamp policy v1.1, effective 2024-06-03, OID `2.16.484.101.10.316.100.12.1.3.1.1.1.0`.
   - Time-stamp practice statement v1.1, effective 2024-06-03, OID `2.16.484.101.10.316.100.12.1.3.2.1.1.0`.
4. The published practice statement describes RFC 3161 time-stamp tokens, identifies the policy OID, and states precision of one second or better. These statements are claims in the published practice document; they do not independently prove the operational state of a particular token or service response.

## Retrieval and verification outcome

The primary pages and document metadata were readable. Attempts to retrieve the linked DER certificates and policy PDFs from the linked S3 object URLs returned HTTP 403 in this execution environment. Therefore this run did **not** obtain exact DER bytes, compute certificate SHA-256 fingerprints, validate the certificate path, inspect EKU/Key Usage, check CRL/OCSP revocation, or verify a live RFC 3161 response.

A separate Incode-branded "Trusted Repository" page describes an Incode Czech Republic s.r.o. hierarchy (F25/M25). It is not treated as the Mexican PSC trust chain and must not be substituted for `ACR2_SE.cer` / `SDT_Frankfurt.cer` / `SDT_Milan.cer` without explicit institutional proof of cross-entity authorization.

## Security and scope conclusions

- The public PSC directory and DOF notice support the fact of accreditation for time-stamp services; they do not establish that Incode is authorized to certify the truth of Chispazo draw operations, weighing, physical origin, or custody.
- RFC 3161 can bind a digest to a time assertion. It does not by itself establish that the submitted source document is true, complete, official, or independently witnessed.
- No Incode certificate fingerprint, root key, TSA endpoint, CRL/OCSP responder, or policy pin is added to application defaults by this audit.
- The production provider must provision a verified certificate chain, revocation state, policy OID, authorized service scope, and rollback-resistant trust configuration out-of-band. The provider CAS must bind that exact configuration.

## Next evidence actions

1. Retrieve the three Mexican PSC DER certificates and policy/practice PDFs through an authenticated or otherwise accessible official distribution channel; preserve original bytes and retrieval metadata.
2. Verify the chain from the published `ACR2_SE.cer` root to the selected SDT certificate; check certificate constraints, EKU, Key Usage, validity and revocation at the token's relevant time.
3. Obtain written confirmation of the correct TSA endpoint and subscription/authorization scope; request a nonce-bound RFC 3161 token and independently validate it.
4. Keep the Chispazo institutional-origin and physical-custody problem separate: obtain official draw acts, CS-11, weighing strips, equipment calibration records, signatures and independent custody evidence.
5. Only after independent review may exact fingerprints and configuration enter the protected provider trust store.

## Public primary references

- Secretaría de Economía PSC directory: https://psc.economia.gob.mx/directorio.html
- DOF accreditation notice (22 May 2024): https://sidof.segob.gob.mx/notas/5727977
- Incode Mexican PSC trust repository: https://psc.incode.com/repositorio-de-confianza/
- Incode public documents and effective policy OIDs: https://psc.incode.com/repositorio/
- Incode time-stamp practice statement: https://s3.eu-central-1.amazonaws.com/crt.tsp.incode.com/crts/psc/policies/DPS-SDT.pdf
