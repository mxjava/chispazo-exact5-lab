# Mexican PSC timestamp-provider screen — 2026-11-26

## Purpose

Screen publicly documented candidates for a future ORIGEN RFC 3161 adapter. This is a discovery comparison only. PSC accreditation is not a statement that Lotería Nacional uses or authorizes any candidate, and public policy text is not proof of live service behavior.

## Official accreditation directory

The Secretaría de Economía's PSC directory lists these entities with an accredited digital-time-seal service (among others):
- Advantage Security
- ATEB Servicios
- CECOBAN
- Cincel Certificadora Digital
- EDICOMUNICACIONES México
- INCODE PSC
- Interfactura
- Legalex GS
- Notaría 230 CDMX
- PSC Codex
- PSC World
- Seguridata Privada

Directory: https://psc.economia.gob.mx/directorio.html

The directory states that the Secretaría de Economía accredits PSCs and supervises their functions. It also clarifies that PSC services do not, by themselves, carry public faith (fe pública). The directory's accreditation status does not demonstrate current endpoint availability, current certificate validity/revocation, RFC 3161 nonce behavior, or a relationship with Lotería Nacional.

## Candidate review

| Candidate | Public evidence found | RFC 3161 / time source evidence | Nonce status | Disposition |
|---|---|---|---|---|
| INCODE PSC | Secretaría de Economía directory and DOF accreditation 22-May-2024; policy/practice version 1.1 effective 03-Jun-2024; public trust-repository page lists ACR2_SE and SDT_Frankfurt/Milan cert locators | Indexed policy/practice text says RFC 3161, SHA-256 imprint, CENAM time source, claimed precision <=1 second, and certificate/OCSP/CRL references in token. Endpoint/manual delivered after contracting. | No nonce mention in indexed practice statement; request field list shows messageImprint, reqPolicy, certReq. Not demonstrated compatible. | Best-documented current candidate found; request integration manual and explicit nonce conformance before adapter work. Certificate/PDF binary bytes and live token not obtained. |
| CECOBAN | Official PSC directory lists SDT accreditation (DOF 07-Oct-2010); public practice manual version 1.1, updated 04-Jan-2022 | Manual says RFC 3161 interoperability, UTC synchronization with CENAM, claimed ±1 second, and client certificate authentication; service requires contract and compatible client software. | No nonce mention in searchable manual. | Possible alternate candidate, but published practice document is old and marked internal-use; require current signed policy/manual and live nonce test. |
| ATEB Servicios | Official PSC directory lists SDT accreditation (DOF 23-Aug-2022); public policy manual version 1.3 updated 02-May-2022 | Manual describes RFC 3161 TSR output, CENAM Cronos sync, claimed ±3 ms, and client-signed requests. | No nonce mention in searchable manual. | Do not rely on this manual as current: it explicitly says its validity ends 01-Nov-2022. Request current policy/practice documents and test. |
| Cincel Certificadora Digital | Official PSC directory lists SDT accreditation (DOF 24-Nov-2023); Cincel PSC page links public practice, policy and usage guide and publishes OID 2.16.484.101.10.316.100.11.1.3.1.1.1.1. | Site/blog states RFC 3161; linked policy/practice files lead to Google Drive pages that only show “Loading…”/sign-in in the available retrieval path. | Not established; technical text could not be inspected. | Candidate worth requesting current policy and API guide from; do not infer nonce support. |

### Sources

- Secretaría de Economía PSC directory: https://psc.economia.gob.mx/directorio.html
- INCODE practice/policy repository: https://psc.incode.com/repositorio/
- INCODE trust repository: https://psc.incode.com/repositorio-de-confianza/
- CECOBAN practice manual: https://www.cecoban.com/wp-content/uploads/2022/01/7.-Manual-de-Declaracion-de-Practicas-de-la-ASDT-Cecoban.pdf
- ATEB policy manual: https://ateb.mx/recursos/Pol%C3%ADticas_ESDT.pdf
- Cincel PSC page: https://www.cincel.digital/psc
- RFC 3161: https://www.rfc-editor.org/rfc/rfc3161

## RFC 3161 nonce compatibility requirement

RFC 3161 defines nonce as an OPTIONAL field in TimeStampReq; when present, the returned TSTInfo nonce MUST be present and have the same value. The RFC's relying-party guidance uses the nonce to detect replay when a local trusted time reference is not used. ORIGEN intentionally strengthens this by requiring a provider-issued, state-bound, single-use challenge and atomic consumption in its independent deployment provider.

Therefore, generic claims of “RFC 3161 compliant” are insufficient. Before selecting a provider, obtain a real TimeStampReq/TimeStampResp pair showing:
1. the exact request nonce is transmitted;
2. the response TSTInfo echoes the same nonce;
3. a missing or mismatched nonce is rejected by ORIGEN;
4. the returned policy OID, imprint, genTime, accuracy, serial and TSA certificate chain validate;
5. revocation status is checked at the required validation time;
6. provider-side request audit and evidence-retention records can be independently obtained.

RFC 3161 source: https://www.rfc-editor.org/rfc/rfc3161

## Selection gate

No provider is currently selected or configured. INCODE is the best-documented current candidate in this public-source screen, not an authenticated ORIGEN provider. The next external step is to request current signed policy/practice bytes, certificate-chain bytes, API/manual, endpoint, subscriber terms and a nonce-conformance sample from INCODE; request equivalent current material from CECOBAN or Cincel only if INCODE cannot satisfy the nonce contract.

Do not configure a provider OID as authorized from discovery metadata alone. Do not create synthetic trust evidence and call it institutional. No provider adapter should be enabled until the root chain, revocation, nonce behavior, exact-byte timestamp verification, independent state backend and Lotería Nacional relevance are established.

ORIGEN remains BLOCKED_PROVENANCE; production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
