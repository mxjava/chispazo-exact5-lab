# PSC Codex TSA public-evidence addendum — 2026-11-27

## Classification

Public institutional accreditation and provider-document discovery only. PSC Codex is a real accredited-provider candidate for research; it is **not provisioned**, not an ORIGEN trust anchor, not a demonstrated nonce-compatible TSA, and not evidence that Lotería Nacional uses or authorizes the provider.

## Institutional accreditation

The current Secretaría de Economía PSC directory lists **PSC CODEX, S.A. DE C.V.** for:
- issuance of digital time seals (DOF notice dated 29-Apr-2024); and
- conservation of data messages (DOF notice dated 29-Apr-2024).

The official DOF notice states that the Secretaría de Economía issued the accreditation resolution under oficio **192.2023.004063**, dated **05-Dec-2023**, for digital time seals and conservation certificates under **NOM-151-SCFI-2016**.

Sources:
- https://psc.economia.gob.mx/directorio.html
- https://sidof.segob.gob.mx/notas/docFuente/5724957

This verifies accreditation/service metadata. It does not establish current operational status, a valid TSA certificate chain, current revocation status, live RFC 3161 behavior, or designation by Lotería Nacional.

## Provider-published policy and practices

The provider's public site exposes a current **Política de Sellos Digitales de Tiempo**, version **1.1**, dated **11-Sep-2024**. It assigns OID:

`2.16.484.101.10.316.100.10.1.3.1.1.1.0`

The policy states that PSC Codex received Secretaría de Economía accreditation on 15-Dec-2023 and began operating the time-seal service on 27-May-2024.

Source:
- https://psccodex.com/files/Anexo-97-Politica-SDT_VF.docx-1.pdf

The publicly linked **Declaración de Prácticas de la Autoridad de Sellado Digital de Tiempo** is version **1.0**, dated **03-Jan-2022**. It predates both the accreditation and the service start; its own review calendar says reviews are annual, but the publicly linked document remains version 1.0. Treat it as stale provider-declared material until Codex supplies a current signed practice statement.

Source:
- https://psccodex.com/files/Practicas-de-la-Autoridad-de-Sellado-Digital-de-Tiempo.pdf

The provider practice statement declares:
- CENAM as the source of UTC time, transferred over a VPN to the service data centers;
- accuracy of one second or better and no issuance when synchronization is lost;
- two FIPS 140-2 Level 3 HSMs and 4096-bit TSA signing keys;
- an RFC 3161 token containing the TSA identifier, generation time, policy OID, digest algorithm, serial, accuracy and certificate chain;
- public distribution of the TSA public certificate.

These are provider-declared controls, not independent measurements, an audit report, a live token validation, or proof that the controls remain in effect today.

## Nonce compatibility — not demonstrated

The published practice statement describes the client-facing request as a REST POST with Bearer-token authentication and a single request parameter named `tsa_hash`, containing the SHA-256 digest. It says the service internally builds a `TimeStampReq` and sends it to the TSA.

The published request schema does not expose a caller-supplied RFC 3161 nonce, and a search of the practice statement found no nonce description. Therefore the public documentation does **not** demonstrate that ORIGEN can bind its provider-issued, single-use, state-generation-bound challenge to the RFC 3161 request and require the same nonce in `TSTInfo`.

This is not proof that the private subscriber API cannot support nonce. The technical integration manual is delivered to subscribers after contracting. Require Codex to provide:
1. a current API specification showing a caller-supplied nonce field or a documented mechanism that preserves the exact ORIGEN challenge;
2. a real `TimeStampReq/TimeStampResp` pair with the requested nonce echoed in `TSTInfo`;
3. proof that absent, mismatched and replayed nonce requests are rejected;
4. exact response policy OID, message imprint, serial, `genTime`, accuracy and certificate chain.

Do not adapt ORIGEN to a hash-only API by silently dropping the nonce requirement.

## Certificate and revocation retrieval

The practice statement says the TSA certificate is published at a URL containing the apparent typo `www.psccodex.con` and references the legacy `firmadigital.gob.mx` directory. The current provider site is `psccodex.com`, but the corrected path `https://www.psccodex.com/certificado/sellosdetiempo/` could not be retrieved through the available web reader.

No DER certificate bytes, SHA-256 fingerprint, issuer/subject linkage, Basic Constraints, Key Usage, timestamping EKU, validity, current CRL, OCSP response, or chain to the independently obtained Secretaría de Economía ACR2 root was captured or verified.

Certificate locator from the provider document (not a verified certificate object):
- https://www.psccodex.com/certificado/sellosdetiempo/

The provider's published practice statement discusses checking the certificate chain and revocation for each token, but that does not substitute for obtaining and verifying the actual certificates and fresh revocation evidence.

## Comparison with INCODE PSC

INCODE remains the more current public-document candidate in the existing provider screen: its Mexican PSC directory entry and DOF accreditation are verified, and its repository lists TSA policy/practice version 1.1 effective 03-Jun-2024. Its policy/practice PDF and certificate objects were not retrievable in the prior capture, and its public indexed request fields did not demonstrate nonce support.

Codex adds an accessible 2024 policy PDF and an explicit provider practice description, but the practice statement is dated 2022 and its published API request is hash-only. Neither provider is currently suitable for ORIGEN provisioning without the missing nonce conformance, exact certificate chain, current revocation, live token, and independent authorization checks.

## ORIGEN disposition

- Keep Codex OID as provider-published discovery metadata only; do not add it to an authorized production policy.
- Do not pin the TSA certificate based on a URL or provider assertion.
- Do not mark nonce compatibility as supported.
- Do not infer Lotería Nacional designation from PSC accreditation.
- Keep all provider fixtures synthetic and segregated from real draw evidence.

**Disposition:** `CANDIDATE_PUBLIC_METADATA_ONLY / NONCE_UNPROVEN / NOT_PROVISIONED`.

ORIGEN remains `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
