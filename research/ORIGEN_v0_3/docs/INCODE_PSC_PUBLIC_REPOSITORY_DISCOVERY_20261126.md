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

The repository page states that it publishes the latest revisions and that tokens issued from the listed effective date follow the corresponding revision, while earlier tokens must be checked against the version effective when issued.

### PDF text reviewed; binary capture still unavailable

The direct policy/practice PDF links returned **HTTP 403 Forbidden** when fetched as files. However, the web search index exposed parsed PDF text, which was opened and reviewed. This supports content-level discovery but not byte-level integrity: the original PDF bytes, SHA-256 digests, digital signatures and authoritative revision bytes were not captured.

The indexed text states:

- The policy identifies the same TSA policy OID above and describes precision of **one second or better**.
- The practice statement says the TSA uses the **Centro Nacional de Metrología (CENAM)** as its trusted time source and records synchronization, recalibration and loss-of-synchronization events.
- The practice statement describes an RFC 3161 flow. Its listed request fields include `messageImprint`, `reqPolicy` and `certReq=true`; the imprint is SHA-256. It says the response token is checked against the requested imprint and returned as Base64 `TimeStampResp`.
- The token contents are described as including the message hash and algorithm, serial number, policy OID, generation time, accuracy reference, TSA identifier, certificate chain, and OCSP/CRL references.
- The subscriber-facing service endpoint is delivered to the customer when the service is contracted; credentials and integration materials are also provided after contracting.
- The document describes certificate-based authentication between the exposed service API and the TSA, plus subscriber credentials.
- The practice statement describes two HSMs compatible with FIPS 140-2 Level 3 and RSA-4096/SHA-256 signing keys.
- It describes operational records containing the submitted hash, request/response time, subscriber identifier and timestamp token, with retention stated as at least three years after issuance.

**Important compatibility gap:** a text search of the indexed practice statement did not find a reference to an RFC 3161 `nonce` field or a provider-issued single-use nonce challenge. The document's listed request fields do not include nonce. This is not proof that the implementation rejects or omits nonce; the subscriber technical integration manual and a live conformance test are required. Until then, ORIGEN's provider-issued challenge contract is **not demonstrated compatible** with this TSA.

These are provider-declared policy/practice statements, not independently audited runtime facts. The text extraction does not prove the CENAM synchronization is currently healthy, the accuracy claim is met by a particular token, or a given token's chain/revocation status.

## Provider-published trust repository — certificate locator discovery

A second provider page, https://psc.incode.com/repositorio-de-confianza/, states that Incode publishes public keys/certificates for its service hierarchies and describes the chain as rooted in the Secretaría de Economía's **Autoridad Certificadora Raíz Segunda**. The page lists:

- `ACR2_SE.cer` — Autoridad Certificadora Raíz Segunda de la Secretaría de Economía.
- `SDT_Frankfurt.cer` and `SDT_Milan.cer` — Incode digital-time-seal authorities.
- `NOM151_Frankfurt.cer` and `NOM151_Milan.cer` — conservation-certificate authorities.

The three certificate links checked (ACR2_SE, SDT_Frankfurt, SDT_Milan) returned **HTTP 403 Forbidden** through the available retrieval path. Their filenames and provider-described roles are locators, not cryptographic evidence. No certificate bytes, DER fingerprints, issuer/subject linkage, key usage/EKU, validity check, signature verification, or revocation check was obtained. The provider page's description of its PKI root must not be substituted for independently validating the actual chain.

This is a concrete certificate-acquisition lead, but it does **not** close the trust-anchor or revocation blocker.

## ORIGEN treatment and next external requirements

- Keep the OID as **provider-published discovery metadata only**. Do not configure it as an authorized production policy OID or trust pin solely from the repository listing.
- Do not accept a token solely because its policy OID matches. Verify the exact TSA signer certificate, chain to the independently pinned Secretaría de Economía root, key usage/EKU, validity at `genTime`, and current OCSP/CRL status.
- Obtain the actual policy and practice PDF bytes through an independently verifiable channel and retain their hashes and versions.
- Obtain the subscriber technical integration manual and endpoint through a legitimate contracted or authorized channel; do not guess or probe private endpoints.
- Ask INCODE explicitly whether its TSA supports and echoes RFC 3161 request `nonce`, whether it rejects absent or mismatched nonces, and whether it can meet the ORIGEN one-use challenge requirement. Then test with real `TimeStampReq/TimeStampResp` pairs, exact request imprint, returned policy OID, serial, `genTime`, accuracy and included certificate chain.
- Obtain a provider-issued timestamp over a test artifact and verify the full response independently. Separately validate the claimed CENAM time-source controls and revocation evidence.
- Establish whether Lotería Nacional or its legally authorized draw operator recognizes this provider for the relevant draw evidence. PSC accreditation alone does not establish that relationship.

## Gate status

No certificate bytes, fingerprints, OCSP/CRL evidence, live timestamp token, authenticated provider endpoint, customer integration manual, nonce conformance result, or Lotería Nacional authorization was obtained. The provider, roots and state fixtures remain unauthenticated/synthetic for ORIGEN. Physical draw evidence and independent custody remain absent. ORIGEN remains `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
