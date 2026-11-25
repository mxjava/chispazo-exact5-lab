# Institutional signature and trust-anchor audit — 2026-11-25

## Scope and conclusion

A fresh review of Lotería Nacional's public material found an official, current procedure for electronic draws and a current Chispazo product page. They describe a meaningful operational evidence chain, including pre-draw electronic signatures, SEGOB inspection, a security box, OIC custody, draw acts and Chispazo-specific result files.

They do **not** publish enough cryptographic material to provision an independently verifiable institutional trust anchor. No public key, certificate chain, key identifier, signature algorithm, canonical signed-byte format, revocation data, or public verification test vector was found in the reviewed material. This is a bounded finding about public sources, not a claim that Lotería Nacional lacks such material internally.

## Primary official sources

1. Lotería Nacional, SGVO-PRO-05, Procedimiento Sorteos Electrónicos, revision 39, published 20 March 2026:
   https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
2. Lotería Nacional, Chispazo product page, checked 25 November 2026:
   https://www.loterianacional.gob.mx/Chispazo/Chispazo

The SGVO-PRO-05 PDF identifies itself as a public VIGENTES procedure, revision 39, and names its approving and authorizing officials. It is not the separate SVO-PRO-05 “Sorteos” procedure (revision 38) and should not be conflated with that document.

## Chispazo modality mapping

The current Chispazo page states two daily draws:

- Chispazo de las Tres — 15:00.
- Chispazo Clásico — 21:00.

The procedure separately describes the electronic-draw operational slots and sales closures. For ORIGEN evidence intake, the product page is the direct source for mapping the two Chispazo modalities; the procedure supplies the operational controls. Do not assign an unrelated 21:00 contest identifier to Chispazo.

## Officially documented evidence chain

The revision-39 procedure states, among other controls:

- Policy 8: the electronic signature for the participation file is recorded on a storage device before the draw; the DTIT representative gives it to the SEGOB inspector, who deposits it in a security box to which the OIC has access.
- Policy 9: electronic-draw sales close at the scheduled 13:00, 15:00, 17:00, 19:00 and 21:00 slots, subject to the procedure's authorization process for changes.
- Policy 11 and its report matrix: the draw act includes the winner report and supporting records. For Chispazo, the matrix names CLSBR140 (Relación de Ganadores and its electronic signature), CLIER195 (Información Básica), CLSKR170 (Resultados Obtenidos) and CLSAR110 (Máscara Ganadora); the procedure also lists CS-11, Sumario de Sorteo and Tira de Pesaje.
- Policy 12: reports and the electronic signature of the winner report are collected on weekly storage media and attached to the acts for custody.
- The process describes inspection of the electronic signature and comparison of the first and last four digits on the stored and printed forms.
- The glossary defines “Firma Electrónica” generically as an algorithm intended to ensure a document or file's veracity and unaltered state.

These statements support an evidence-request plan. They do not disclose the actual cryptographic verification inputs or establish that a publicly downloadable signature can be verified independently.

## Trust-anchor gap

The reviewed PDF does not specify:

- whether the “algorithm” is a cryptographic hash, MAC, digital signature, or another construction;
- the algorithm and parameters, signature container, or exact byte canonicalization;
- a public key, X.509 certificate, certificate chain, fingerprint, or institutional key ID;
- key validity, rotation, revocation, compromise handling, or a signed trust-policy sequence;
- RFC 3161 TSA identity, TSA certificate chain, timestamp token format, nonce policy, or revocation checks;
- a public verification tool or signed known-answer test vector.

The first/last-four-character comparison is an operational consistency control, not an independent cryptographic verification method.

No trust anchor is therefore provisioned from this public procedure. The caller-supplied V3 root remains explicitly unauthenticated.

## Required external evidence request (not yet obtained)

To replace the synthetic fixtures with authentic institutional evidence, obtain through an authenticated institutional channel:

1. Original participation/cancellation files and their exact electronic-signature sidecars for a specified Chispazo contest, preserving original bytes.
2. Signature algorithm, parameters, signed-byte format, and a vendor/institution verification utility or signed known-answer test vectors.
3. Institutional public key or certificate chain, fingerprints, key IDs, validity and revocation/rotation history, plus the authority and process that approve key changes.
4. The relevant CS-11, Sumario, Tira de Pesaje, Acta, Relación de Ganadores and their signatures, each with exact-byte hashes and documented custody.
5. Any TSA tokens and the TSA trust material, if timestamps are used.
6. The OIC/SEGOB custody receipt and a separately verifiable receipt for the transfer, including the custodian identity/role and an independently anchored timestamp.

Until those items are supplied and verified, keep the external provenance adapter and production eligibility blocked.

## Provenance metadata

- Reviewed: 2026-11-25.
- Official procedure publication date shown in the PDF: 2026-03-20.
- Procedure: SGVO-PRO-05, revision 39, public VIGENTES copy.
- Raw PDF bytes downloaded and hashed in this run: no.
- PDF SHA-256: NOT_CAPTURED.
- Original institutional signature artifacts received: none.
- Institutional public trust anchor verified: no.
- All code fixtures in the companion V3 custody verifier remain synthetic.

## Normateca identity and revision reconciliation — verified 2026-11-25 14:55 America/Mexico_City

The official **Normas Sustantivas Vigentes** index has a row for **PROCEDIMIENTO SORTEOS ELECTRÓNICOS**, emitted 01/10/2003, last updated 20/03/2026, linking to `sgvo_pro_05.pdf`:

- https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- Direct linked PDF: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

The linked PDF itself identifies **SGVO-PRO-05, revision 39**, states **FECHA DE PUBLICACIÓN: 20 MAR 2026**, and contains six approval/authorization name blocks with handwritten signature images. This is the current official Normateca entry and the version to use for this audit. The prior claim that revision 39 was only a project and that revision 38 was the current SGVO-PRO-05 version was incorrect.

Two similarly named files in the separate historical **Proyectos Normativos** index must not be conflated with that current file:

- `sgvo_pro_05p.pdf`: PROCEDIMIENTO SORTEOS ELECTRÓNICOS, consultation 23/02/2026–04/03/2026.
- `svo_p_05.pdf`: SORTEOS, consultation 19/09/2025–25/09/2025.

Project index: https://www.loterianacional.gob.mx/Normateca/Proyectos?id=0 . The distinct filename, prefix and consultation dates matter; neither project listing displaces the current `sgvo_pro_05.pdf` row in Normas Sustantivas Vigentes.

Revision 39's operational facts relevant to Chispazo include:

- Policy 6: Smartballs 4.25–5.25 g, maximum mass spread 0.30 g; Ping Pong 2.30–3.00 g, maximum spread 0.15 g; weighing is performed for each draw.
- Policy 8: the participation-file electronic signature is written to storage before the draw; the DTIT representative hands the device to the SEGOB inspector, who deposits it in the security box assigned for OIC access.
- Policy 9: the stated electronic sales-close slots include 15:00 for De las Tres and 21:00 for nocturnal draws. Chispazo's own product page maps its Clásico to 21:00.
- Policy 11 and its annex matrix: the Acta must identify place, date, time, assigned officials and SEGOB inspector; Chispazo attachments include the winner report CLSBR140, sales-close Sumario, CS-11, Sumario and Tira de Pesaje. The weekly media matrix lists CLSBR140, CLIER195, CLSKR170 and CLSAR110.

This confirms the current procedural revision and the evidence-request targets. It does **not** supply a public cryptographic algorithm, public key/certificate chain, signature-byte canonicalization, revocation data or independently verifiable known-answer vector. The procedure's first/last-four-character comparison is an operational control, not a substitute for independent signature verification.

The official web PDF was inspected through the published URL and parsed text in this run; the original PDF bytes were not successfully captured in the working container. Its SHA-256 remains **NOT_CAPTURED**. No draw-specific physical record was obtained.
