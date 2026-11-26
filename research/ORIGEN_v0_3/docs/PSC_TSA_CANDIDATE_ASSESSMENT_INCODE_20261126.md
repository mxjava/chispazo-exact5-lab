# Institutional TSA candidate assessment — Incode PSC (2026-11-26)

**Classification:** verified accredited-provider candidate; NOT provisioned; NOT an accepted deployment trust anchor.

## What is independently supported by public institutional records

The current Secretaría de Economía PSC directory lists **INCODE PSC, S. de R.L. de C.V.** as accredited for:
- issuance of Digital Time Seals; and
- Conservation Certificates for Data Messages.

The directory links the time-seal accreditation to the DOF notice dated **22-May-2024**. The DOF notice states that the Secretaría de Economía issued the accreditation resolution under oficio 192.2024.000219 dated 24-Jan-2024, for RFC/NOM-151 digital time seals and conservation certificates.

Official sources:
- Secretaría de Economía PSC directory: https://psc.economia.gob.mx/Directorio
- DOF accreditation notice: https://psc.economia.gob.mx/docs_l/DOF_INCODE_sdt_ccmd.pdf
- DOF notice publication date: 22-May-2024; resolution date: 24-Jan-2024.

## Provider-published service material

Incode's public document repository states that the listed documents are its latest/current revisions for each service. For its Digital Time-Stamping Authority it lists:
- Policy of Digital Time Seals, version 1.1, effective 03-Jun-2024, OID `2.16.484.101.10.316.100.12.1.3.1.1.1.0`;
- Declaration of Practices for Digital Time Seals, version 1.1, effective 03-Jun-2024, OID `2.16.484.101.10.316.100.12.1.3.2.1.1.0`.

The provider's service page says its time-stamp service conforms to RFC 3161 and NOM-151-SCFI-2016 and states synchronization with CENAM. These are provider-published service assertions, not independent clock measurements or a deployment authorization.

Provider sources:
- Current public document repository: https://psc.incode.com/repositorio/
- Time-seal service description: https://psc.incode.com/
- Public trust repository: https://psc.incode.com/repositorio-de-confianza/

## Published certificate inventory

The provider trust repository lists:
- Secretaría de Economía root: `ACR2_SE.cer`;
- Incode TSA certificates: `SDT_Frankfurt.cer` and `SDT_Milan.cer`;
- separate NOM-151 service certificates for Frankfurt and Milan.

The repository states that the Incode PSC hierarchy chains to the Secretaría de Economía's ACR2-SE root. The Secretaría de Economía directory itself links the ACR2-SE certificate at:

https://psc.economia.gob.mx/certificados/ACR2_SE.cer

## Retrieval and verification result in this run

The public directory and DOF notice were readable and verified. The provider repository pages were readable and exposed the policy versions, effective dates, OIDs and certificate filenames.

The actual policy PDFs and DER certificate objects could not be retrieved into the research environment in this run: the provider's S3 object links returned HTTP 403 to the web reader and the working-container download attempt failed; the official ACR2-SE certificate endpoint returned an unsupported certificate content type to the web reader and the container download attempt also failed.

Consequently, no certificate bytes were captured and no local SHA-256 fingerprints are claimed:
- `ACR2_SE.cer`: `NOT_CAPTURED`;
- `SDT_Frankfurt.cer`: `NOT_CAPTURED`;
- `SDT_Milan.cer`: `NOT_CAPTURED`;
- current TSA policy PDF: `NOT_CAPTURED`;
- current TSA practices declaration PDF: `NOT_CAPTURED`.

No certificate path, Basic Constraints, Key Usage, timestamping EKU, subject/SAN, serial, validity, CRL, OCSP, revocation freshness, endpoint behavior, nonce handling, accuracy semantics or actual RFC 3161 token was verified. The OID and effective date are transcribed from the provider's public repository; they are not yet pinned as trusted configuration.

## Assessment and next verification gate

Incode is a stronger **research candidate** than the previously examined ATEB material because:
- its time-seal accreditation is present in the current Secretaría de Economía directory and the DOF notice is from 2024;
- its public repository identifies TSA policy and practice revisions effective in 2024 and explicitly presents them as current;
- it publishes named TSA certificate objects and a trust-repository description of the ACR2-SE hierarchy.

This does **not** authorize the repository to trust Incode yet. Before provisioning:
1. obtain the exact policy and practices PDFs and certificate DER bytes through a retrievable, independently authenticated channel;
2. compute and preserve SHA-256 for every original object;
3. verify the ACR2-SE certificate against the official Secretaría de Economía publication and current certificate policy;
4. validate the complete TSA path, EKU, Key Usage, constraints, certificate validity and current revocation evidence;
5. obtain the actual service endpoint, supported policy OID, nonce and accuracy profile, and test a live RFC 3161 response against the exact original request imprint;
6. obtain current accreditation/status confirmation and a signed deployment authorization that fixes the root fingerprint, TSA certificate identity, endpoint and OID;
7. persist the accepted trust anchor and anti-rollback floor in a separately administered, rollback-resistant store.

The accreditation is for certification services generally; it does not establish that Incode is designated by Lotería Nacional to certify Chispazo draw events, nor does a timestamp authenticate the truth of a physical weighing strip or custody assertion.

**Disposition:** `CANDIDATE_VERIFIED_PUBLIC_METADATA_ONLY / NOT_PROVISIONED`.

All ORIGEN results remain `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
