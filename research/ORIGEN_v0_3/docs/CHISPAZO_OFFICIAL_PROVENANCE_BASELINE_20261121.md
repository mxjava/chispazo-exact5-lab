# Chispazo — Official procedure and provenance baseline

**Observation:** 2026-11-21 19:57:54 America/Mexico_City  
**Classification:** RESEARCH / PUBLIC-RESULT STATUS ONLY / NOT PHYSICAL EVIDENCE  
**Scope:** Chispazo Clásico (21:00) versus Chispazo de las Tres (15:00)

## 1. Primary official references

1. Lotería Nacional, *Reglamento del Concurso Chispazo de Pronósticos para la Asistencia Pública*, official compiled PDF. Its cover states that the last reform was published in the Diario Oficial de la Federación on 7 March 2012:
   https://www.loterianacional.gob.mx/documentos/legal/reglamentojuegos/Reforma-Reg-Chispazo-marzo-2012.pdf
2. Lotería Nacional, current Chispazo product page and published schedule:
   https://www.loterianacional.gob.mx/Chispazo/Chispazo
3. Lotería Nacional, dedicated Chispazo results page:
   https://www.loterianacional.gob.mx/Chispazo/Resultados
4. Lotería Nacional, daily result masks index:
   https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
5. Lotería Nacional, home index:
   https://www.loterianacional.gob.mx/home/index

The regulation copy is an official Lotería Nacional publication, but its stated last reform is 2012. This note does not independently establish whether later administrative instruments modify any operational detail; legal applicability must be confirmed with Lotería Nacional / SEGOB before relying on it as current legal advice.

## 2. Regulatory facts relevant to provenance

The compiled regulation makes several distinctions that ORIGEN must preserve:

- **Article 8:** the official winning results are those recorded in the act referenced in Article 15. Website and result-mask publications are expressly informational; if they differ from the official result, the act prevails.
- **Article 9(I):** the Chispazo ceremony uses one urn containing 28 spheres described as similar in all their characteristics, numbered 1 through 28.
- **Article 9(II)-(III):** the sales close and creation of the participation file occur in the presence of the specified institutional representatives; the file receives an electronic signature for integrity, is delivered to the SEGOB inspector, and is deposited in a safe accessible only to the Internal Control Body.
- **Article 9(IV):** five spheres are drawn one by one and at random in the presence of the named officials.
- **Article 15:** after the ceremony and identification of winning combinations, an act records the background, results and any incident; the SEGOB inspector and the named officials participate and sign it.
- **Article 15 bis:** a narrow force-majeure exception exists for inspector absence where a notary cannot be engaged; the designated institutional representative then performs the inspector's functions and delivers the act to the authority within three business days.

The text says the 28 spheres must be similar in their characteristics. It does **not** provide a quantitative Chispazo sphere-mass tolerance or a full calibration/measurement protocol in the cited provisions. Do not import tolerances from another lottery or another draw's regulation.

## 3. Official schedule and 21-Nov-2026 observation

The current product page states:
- Chispazo de las Tres: **15:00** local time.
- Chispazo Clásico: **21:00** local time.

At the observation time:

| Contest | Date / scheduled time | Modality basis | Public result status |
|---|---|---|---|
| 12387 | 21-Nov-2026 / 15:00 | De las Tres by matching the official 15:00 product schedule | Dedicated results page published **01 05 11 18 19** |
| 12388 | 21-Nov-2026 / 21:00 | Clásico by matching the official 21:00 product schedule | Home index advertised the contest; no winning numbers were visible in the inspected result sources at 19:57:54 |

The 21-Nov result-mask index still listed 20-Nov as its latest available daily mask at observation. Therefore:
- 12387 is a public result classified by schedule, not by 21-Nov mask inspection.
- 12388 is a scheduled Classic contest, not a result.
- Do not treat 12387 as the 21:00 Classic draw.
- Do not infer or fabricate any 12388 winning numbers.

## 4. Evidence classification

The public results page, home index and mask index are discovery/publication sources. Under Article 8, they are not substitutes for the official act.

No 21-Nov official act, inspector-signed act, signed participation-file copy, safe-access record, original sphere-weight log, calibration certificate, sphere-set identity, equipment identity, maintenance log, or independently timestamped custody receipt was obtained in this observation.

No original 21-Nov daily-mask PDF bytes were captured in this run. No SHA-256 is asserted for that PDF or for the live pages. The source URLs above are locators, not immutable evidence objects.

Consequently, this observation supplies **no authenticated physical evidence** and no prospective evidence eligible for scoring. Do not append either contest to canonical history through this note; do not set pre-close, OOS, custody, score, or eligibility flags to true.

## 5. Minimum evidence request for a defensible physical audit

For each separately identified draw (12387 De las Tres and 12388 Clásico), request and preserve, as distinct immutable objects:

1. The complete Article 15 act, including all pages, signatures, inspector identity/authority and incident annexes.
2. The Article 9 signed participation-file manifest and cryptographic digest, the inspector's receipt, and the documented safe deposit/access chain.
3. The equipment and urn identifiers used for that draw, with setup, inspection, maintenance and changeover records.
4. The 28-sphere inventory and individual identifiers; pre-draw and post-draw measurements, instrument identity, calibration certificate, resolution, operator, witnesses and measurement timestamps.
5. The applicable approved technical procedure defining what “similar characteristics” means operationally, including any approved mass/diameter/surface tolerances. Do not substitute a procedure from another lottery.
6. Original audiovisual recording and official event log, where retained, with acquisition metadata and independent custody.
7. Original source bytes, byte lengths and SHA-256 digests computed at intake, plus independent timestamp and receipt evidence.

Keep result outcome records separate from physical-measurement records. A published combination cannot prove the physical state, identity, weight or calibration of the spheres that produced it.

## 6. ORIGEN handling

- Keep all public result observations in a status-only overlay until the official act and provenance package are obtained and independently verified.
- Do not classify website or mask content as an official act.
- Keep De las Tres and Clásico in separate contest rows, source windows and modality labels.
- Do not change the frozen V294 model, canonical historical CSV, scoring, or production state.
- Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
