# INCODE PSC public-repository discovery — 2026-11-26

## Scope and classification

This is a public-source discovery note for the ORIGEN research trust-boundary. It is not trust-anchor provisioning, a TSA integration, a certificate validation, or evidence that Lotería Nacional uses or authorizes this provider.

## Primary institutional accreditation evidence

The Secretaría de Economía's official Prestadores de Servicios de Certificación directory lists **INCODE PSC, S. de R.L. de C.V.** with:
- Servicio de sellos digitales de tiempo.
- Servicio de conservación de mensajes de datos.
- DOF notice dated **22-May-2024**.

The linked official DOF notice states that, by resolution issued under oficio **192.2024.000219** dated **24-Jan-2024**, the company was accredited for issuance of digital time seals and conservation certificates under **NOM-151-SCFI-2016**.

Sources:
- https://psc.economia.gob.mx/directorio.html
- https://psc.economia.gob.mx/docs_l/DOF_INCODE_sdt_ccmd.pdf

This verifies public accreditation/service metadata only. It does not establish current operational status, a valid certificate chain, current revocation status, actual RFC 3161 response behavior, or any contractual/institutional relationship with Lotería Nacional.

## Provider-published TSA repository metadata

The official DOF notice points to the provider's public repository:
https://psc.incode.com/repositorio/

At capture, the repository page stated that it publishes the latest revisions of public documents for its accredited certification services. Under **Autoridad de Sellado Digital de Tiempo**, it listed:

| Document | Version | Effective date | OID |
|---|---:|---|---|
| Política de Sellos Digitales de Tiempo | 1.1 | 03-Jun-2024 | `2.16.484.101.10.316.100.12.1.3.1.1.1.0` |
| Declaración de Prácticas de Sellos Digitales de Tiempo | 1.1 | 03-Jun-2024 | `2.16.484.101.10.316.100.12.1.3.2.1.1.0` |

The repository page also states that tokens issued from the listed effective date follow the corresponding published revision, while earlier tokens must be checked against the version effective when they were issued.

The linked policy and practice-statement PDFs were not retrievable during this capture: the document links returned **HTTP 403 Forbidden** from the linked S3 host. Therefore the policy text, certificate profile, TSA certificate chain, signer identity, revocation endpoints, algorithm constraints, timestamp accuracy/ordering terms, and operational audit requirements have **not** been independently inspected.

## ORIGEN treatment

- Keep the OID above as **provider-published discovery metadata only**.
- Do not configure it as an authorized production policy OID or as a trust pin.
- Do not accept a timestamp token solely because its policy OID matches this public listing.
- Before any integration, retrieve the policy/practice PDFs through an independently verified channel; obtain the TSA certificate(s) and chain as bytes; validate fingerprints, validity, key usage, EKU, policy OID, and current revocation; test RFC 3161 responses and nonce handling; and establish independent operational/contractual authorization.
- Separately establish whether Lotería Nacional or its legally authorized draw operator recognizes this provider for the relevant draw evidence. The PSC accreditation itself does not establish that relationship.

No certificate bytes, fingerprints, OCSP/CRL evidence, live timestamp token, authenticated provider endpoint, or Lotería Nacional authorization was obtained in this research step.

## Gate status

This note does not remove any blocker. All trust fixtures remain synthetic; the provider is not deployed or independently authenticated; physical draw evidence and custody remain absent. ORIGEN remains `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.


## Provider-published trust repository — certificate locator discovery

A second provider page, https://psc.incode.com/repositorio-de-confianza/, states that Incode publishes public keys/certificates for its service hierarchies and describes the chain as rooted in the Secretaría de Economía's **Autoridad Certificadora Raíz Segunda**. The page lists these certificate files:

- `ACR2_SE.cer` — Autoridad Certificadora Raíz Segunda de la Secretaría de Economía.
- `SDT_Frankfurt.cer` and `SDT_Milan.cer` — Incode digital-time-seal authorities.
- `NOM151_Frankfurt.cer` and `NOM151_Milan.cer` — conservation-certificate authorities.

The three certificate links checked for this note (ACR2_SE, SDT_Frankfurt, SDT_Milan) returned **HTTP 403 Forbidden** through the available retrieval path. Their filenames and provider-described roles are locators, not cryptographic evidence. No certificate bytes, DER fingerprints, issuer/subject linkage, key usage/EKU, validity check, signature verification, or revocation check was obtained. The provider page's description of its PKI root must not be substituted for independently validating the actual chain.

This improves discovery: there is a documented certificate repository and named TSA certificate candidates to request or retrieve through another independently verifiable channel. It does **not** close the trust-anchor or revocation blocker.
