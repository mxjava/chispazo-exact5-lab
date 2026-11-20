# ORIGEN v0.3 — Physical evidence acquisition protocol

Status: RESEARCH_ONLY / BLOCKED_PROVENANCE  
Scope: Chispazo electronic draws (including Clásico). This defines an evidence request and intake contract; it does not claim Lotería Nacional has supplied primary records.

## 1. Official procedural basis

Public Lotería Nacional documents checked on 2026-11-20:
- SGVO-PRO-05, Procedimiento Sorteos Electrónicos, revision 39, listed as current substantive procedure (PDF publication 20 Mar 2026): https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Normateca Sustantivas Vigentes index: https://www.loterianacional.gob.mx/Normateca/Sustantivas?id=2
- Chispazo official game page (universe 1–28 and daily draw schedule): https://comercializadores.loterianacional.gob.mx/Chispazo/Chispazo

Relevant requirements transcribed from SGVO-PRO-05 rev. 39:
- Policy 6: each draw's spheres are weighed; Ping Pong spheres must be 2.30–3.00 g each with max-min spread <=0.15 g; Smartballs must be 4.25–5.25 g each with max-min spread <=0.30 g.
- Policy 25: scales used to weigh electronic-draw spheres must be calibrated at least annually under the operating unit's calendar.
- The weigh-in is performed one sphere at a time and in numeric order in the presence of the SEGOB inspector and Lotería Nacional representatives.
- The weighing strip is checked against the policy limits, signed by the operator, reviewed/rubricated by the operating representative, SEGOB inspector and General Directorate representative, then attached to the draw record.
- The winning-number CS-11 form is read aloud, checked against sphere numbers, signed by Lotería Nacional representatives and the SEGOB inspector, and distributed with the original attached to the draw record.
- The draw act records place, date/time, names/roles/signatures of Lotería Nacional representatives, and the SEGOB inspector's name, signature and commission-office number; incidents are recorded.

The 2026 official procedure, not older draft/project documents, is the controlling reference for this intake contract.

## 2. Per-draw primary evidence package

Request and preserve the following original records for each target draw, keyed by official draw ID and modality:
1. Original weighing strip: all individual sphere weights, set/case identifier, date/time, instrument identity, printed statistics, signatures/rubrics.
2. Original CS-11 winning-numbers form: draw ID, date, modality, sphere-to-number correspondence, names and signatures of responsible Lotería Nacional representatives and SEGOB inspector.
3. Signed draw act: participants, roles, inspector commission-office number, start/end times, and incident entries or explicit no-incident notation if available.
4. Scale calibration certificate valid at measurement time, plus instrument make/model/serial number and traceability details.
5. Sphere set inventory: set/case ID, physical sphere identifiers, mapping to printed numbers, sphere type, and assignment/validity intervals.
6. Unedited original audiovisual recording from weigh-in through sphere loading and draw completion, with official custodian, creation metadata, and verifiable hash of acquired original bytes.
7. Custody and verification attestations: who produced, transmitted, received, hashed, and independently verified each item; timezone-aware timestamps and trusted time source; signature validation evidence and signer identity/authority.

The official procedure confirms the weigh strip, CS-11, and act records. Additional identity, calibration, audiovisual, hashing, and custody fields are ORIGEN evidence-quality requirements, not represented as verbatim statutory requirements.

## 3. Independent verification contract

A reference string in JSON is not proof of authenticity. A record is independently verified only when ORIGEN receives separately verifiable evidence for source bytes and SHA-256; source signature bytes and cryptographic validation; signer identity and authority; timestamp source; calibration certificate and traceability; physical sphere identity and mapping continuity.

The source signer, evidence preparer, and custodian must not collapse into one person. The verifier must be independent of source signer and custodian. Preserve original bytes read-only; OCR, transcriptions, normalized CSVs and screenshots are derivatives and must never replace originals.

## 4. Intake and quarantine rules

- One record set per draw; never combine Clásico and De las Tres.
- Require exactly 28 distinct sphere identities mapped bijectively to numbers 1–28 for a complete Chispazo set.
- Validate draw ID, modality, local draw date, weigh-in/assignment/measurement/draw chronology, mapping validity interval, mass range and set spread.
- Reject naive timestamps, duplicate identities, invalid hashes, missing signature attestations, signer/custodian identity collisions, incomplete sets, and mapping overlaps.
- Keep invalid rows and source files in quarantine; do not silently repair or overwrite.
- Hash originals before parsing; retain source bytes, acquisition metadata, and every transformation's input/output hashes.
- Same-draw post-close weighing strip or recording is post-close evidence. It may audit the physical process but cannot become a pre-close predictor for that draw.
- No model fitting, ranking, feature selection, or candidate generation may use evidence acquired after target draw close as a predictor for that draw.

## 5. Acceptance gates

A draw may be labelled PHYSICAL_EVIDENCE_VERIFIED only when all required primary artifacts are present and independent verification passes. Otherwise label BLOCKED_PROVENANCE and list exact missing items.

Physical evidence verification does not establish predictive edge. EDGE_SUPPORTED remains subject to separate prospective gates: at least 100 intact chronological out-of-sample Classic draws, predeclared positive lift, Holm-adjusted p < 0.05, Exact5 anytime e-value >=20, two live pre-close Exact5 score outputs, clean hashes, and independently custodied pre-close snapshots.

## 6. Current repository status

As of this protocol's creation, no original signed weighing strips, CS-11 forms, signed draw acts, calibration certificates, raw recordings, or independent verification attestations for target historical draws have been deposited in the ORIGEN evidence store. Therefore no historical draw is promoted to PHYSICAL_EVIDENCE_VERIFIED; the correct state remains BLOCKED_PROVENANCE.

## 7. Official source navigation

The Normateca page lists current substantive documents and provides SGVO-PRO-05. Relevant PDF locations: Policy 6 (sphere weights and spread limits); Policy 25 (annual scale calibration); Activities 5.1–5.6 (weigh-in, checking, signatures, attachment to act, loading); Activities 13.1–13.6 (CS-11 creation, cross-check, signatures and distribution); Policy 11 (draw-act information and SEGOB inspector commission-office number).
