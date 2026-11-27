# External TSA and ledger provider candidates — 27-Nov-2026

## Purpose and decision boundary

This assessment identifies Mexican Prestadores de Servicios de Certificación (PSC) with publicly verifiable accreditation and relevant timestamp/ledger interfaces. Accreditation is evidence that a legal entity was authorized for the listed services; it is not, by itself, proof that a live token, certificate chain, nonce echo, independent custody or deployment CAS has been validated.

The ORIGEN challenge requires a one-use client challenge to be bound into the RFC 3161 request and echoed in the response. A provider is not compatible until it supplies a real TimeStampReq/TimeStampResp pair proving that behavior, together with the current TSA certificate chain, CRL/OCSP material, policy OID, accuracy/uncertainty and operational status.

## 1. Incode PSC — strongest public candidate, not provisioned

- Secretaría de Economía published its accreditation on 22-May-2024 for digital time stamps and NOM-151 conservation certificates. The DOF notice references oficio 192.2024.000219 dated 24-Jan-2024.
- Its public document repository identifies timestamp policy and practices version 1.1, effective 03-Jun-2024, with policy OID `2.16.484.101.10.316.100.12.1.3.1.1.1.0`; the repository says the listed documents are the latest revisions.
- Its public service page describes a request built from the data hash and OID, sent to the TSA, which signs and returns a time stamp. It does not document a caller-supplied RFC 3161 nonce or a nonce echo contract.
- Its Trusted Repository lists Root CA, Issuer CA, TSA and TSU certificate/CRL metadata for F25 and M25 hierarchies. For example, the F25 TSA entry lists serial `7a 27 29 de 3e 4d a6 33 36 8d 8d 8a 8b 6b cd e4 de 1c b9 f0` and validity 24-Apr-2025 through 23-Apr-2030.
- Important limitation: the Trusted Repository page identifies Incode Czech Republic s.r.o.; the legal/cryptographic linkage from those chains to the Mexican PSC Incode entity and its Mexican timestamp policy OID has not been verified. The web fetcher rejected DER/CRL content types and the container download did not retrieve the bytes. No certificate-chain validation or SHA-256 was performed.
- Disposition: `CANDIDATE_CURRENT_PUBLIC_POLICY_AND_CERT_METADATA / NONCE_UNDOCUMENTED / ENTITY_CHAIN_UNVERIFIED / NOT_PROVISIONED`.

## 2. Cincel Certificadora Digital — timestamp plus public-ledger candidate

- The DOF published accreditation on 24-Nov-2023 for digital time stamps and NOM-151 conservation certificates.
- Its public API v3 documents `GET /timestamps/{sha256_hash}.asn1`, returning a DER-encoded ASN.1 certificate from an accredited PSC. It lists `.asn1`, `.tsr` and `.xml` formats and a public audit endpoint for timestamp and blockchain verification.
- The API overview describes NOM-151, RFC 3161 and Bitcoin blockchain proof; evidence packages may include Bitcoin/Ethereum certification receipts.
- The documented request is hash-addressed; no client-supplied nonce field or echo requirement is documented. The Bitcoin proof would need independent transaction/merkle/inclusion verification; a vendor audit page alone is not an independent witness.
- Disposition: `CANDIDATE_TIMESTAMP_AND_PUBLIC_LEDGER / NONCE_UNDOCUMENTED / PROOF_NOT_INDEPENDENTLY_VERIFIED / NOT_PROVISIONED`.

## 3. ATEB — ASN.1 request candidate, public practices stale

- The DOF published accreditation on 23-Aug-2022 for digital time stamps and NOM-151 conservation certificates.
- Public technical material describes an ASN.1 request with a public key and signed request, and a returned `.tsr` time-stamp response. The policy describes UTC synchronization and an accuracy target of approximately 3 ms.
- The publicly available policy is version 1.3 (02-May-2022); the practice statement is version 1.4 (20-May-2022) and itself describes a six-month validity period that ended in 2022. No current replacement was verified in this search.
- The ASN.1 interface is the most promising public description for a client-supplied nonce, but no explicit nonce field or echo behavior was found. A current practice statement and a live request/response pair are required.
- Disposition: `CANDIDATE_ASN1_INTERFACE / PUBLIC_PRACTICES_STALE / NONCE_UNCONFIRMED / NOT_PROVISIONED`.

## 4. PSC Codex — accredited, documented hash-only integration

- The DOF published accreditation on 29-Apr-2024 for digital time stamps and NOM-151 conservation certificates.
- Its public timestamp policy is version 1.1 dated 11-Sep-2024. The public REST integration describes a single `tsa_hash` input and server-generated `.tsq`; no client-supplied nonce is documented.
- The public practice statement located is version 1.0 dated 03-Jan-2022. No live RFC 3161 token or certificate chain was retrieved.
- Disposition: `ACCREDITATION_VERIFIED / HASH_ONLY_API_NONCE_UNDOCUMENTED / NOT_PROVISIONED`.

## Required evidence before any provider is accepted

1. Current signed policy and practice statement, service scope and legal entity name.
2. A raw client-generated RFC 3161 TimeStampReq containing our one-use nonce, plus the unmodified TimeStampResp showing the same nonce.
3. TSA certificate DER, issuer/root chain, policy OID, current CRL and/or OCSP responses, key usage/EKU and revocation semantics.
4. Independent verification of message imprint, nonce, genTime, accuracy, ordering, policy and signature; retain the original request/response bytes.
5. A documented current time source, synchronization/holdover behavior, maximum uncertainty, outage behavior and audit evidence.
6. For ledger claims, raw transaction ID, inclusion proof, block header/height, confirmations and a verifier independent of the vendor's audit page.
7. For provider CAS, a separate durable monotonic-state service with authenticated read/compare-and-advance, linearizable transaction semantics, root provisioning and recovery/rollback controls. None of the public PSC timestamp APIs above demonstrates this CAS service.
8. No PSC timestamp service is a substitute for SEGOB/Lotería Nacional acta, signed draw records, independent physical custodian or authentic custody chain.

## Sources

- Secretaría de Economía PSC directory: https://psc.economia.gob.mx/directorio.html
- Incode DOF accreditation (22-May-2024): https://psc.economia.gob.mx/docs_l/DOF_INCODE_sdt_ccmd.pdf
- Incode current public policy/practices repository: https://psc.incode.com/repositorio/
- Incode Trusted Repository and certificate/CRL metadata: https://psc.incode.com/trusted-repository/
- Incode public timestamp service description: https://psc.incode.com/
- Cincel DOF accreditation (24-Nov-2023): https://psc.economia.gob.mx/docs_l/Acre_CINCEL_tsa_ccmd.pdf
- Cincel API timestamp and Bitcoin proof documentation: https://docs.cincel.digital/v3/digital-signature
- ATEB DOF accreditation (23-Aug-2022): https://psc.economia.gob.mx/docs_l/ATEB_Servicio_de_sellos_digitales_de_tiempo_DOF%2023-08-2022.pdf
- ATEB timestamp policy: https://ateb.mx/recursos/Pol%C3%ADticas_ESDT.pdf
- ATEB timestamp practices: https://ateb.mx/recursos/Declaraci%C3%B3nPr%C3%A1cticas_ESDT.pdf
- PSC Codex DOF accreditation (29-Apr-2024): https://psc.economia.gob.mx/docs_l/DOf_CODEX_sdt_ccmd.pdf
- PSC Codex public timestamp policy: https://www.psccodex.com/files/Anexo-97-Politica-SDT_VF.docx-1.pdf
- PSC Codex public timestamp practices: https://www.psccodex.com/files/Practicas-de-la-Autoridad-de-Sellado-Digital-de-Tiempo.pdf

## Final disposition

Incode is the first provider worth requesting a nonce-capable raw RFC 3161 interface from, with Cincel as a separate timestamp/ledger candidate. Neither is accepted or provisioned. No live credentials, service contract, token, certificate DER or CRL bytes were obtained. No hashes are asserted for source files or certificates.

V294 remains frozen. Canonical history remains untouched. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
