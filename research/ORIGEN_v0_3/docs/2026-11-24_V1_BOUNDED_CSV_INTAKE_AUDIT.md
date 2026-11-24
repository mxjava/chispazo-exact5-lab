# V1 bounded physical CSV intake audit — 2026-11-24

## Reproducible defect

The V1 `validate-physical` path had a row-count ceiling, but its `csv.DictReader` boundary did not bound the header, individual physical records, or aggregate input bytes before constructing field strings and row mappings. It also inherited general CSV multiline-field behavior although every V1 field is a scalar. An input could therefore consume disproportionate memory within the nominal 28,000-row limit, and a quoted multiline value could cross physical-record boundaries before structural validation.

This was a parser resource/record-boundary defect, not evidence of a provenance-authentication bypass or a predictive-model defect.

## Minimal hardening

`validate_physical_csv` now reads the original file as bounded binary physical lines and validates the CSV envelope before passing rows to the existing structural validator:

- header: at most 4,096 bytes;
- encoded physical record: at most 65,636 bytes (derived from the 32,768-byte decoded row-payload limit and the fixed V1 column count);
- decoded UTF-8 field payload per row: at most 32,768 bytes;
- aggregate input: at most 64,000,000 bytes;
- row count: existing maximum of 28,000 rows.

The parser rejects invalid UTF-8, unsupported embedded carriage returns, malformed or multiline records, duplicate/noncanonical/missing/unexpected headers, and records with more fields than the header. Short rows remain represented with missing cells and are quarantined by the existing structural validator. The input file is opened read-only; no source normalization or rewriting occurs.

## Adversarial regression coverage

Six tests were added for oversized headers, oversized physical records, multiline scalar fields, decoded row payloads above the limit, aggregate byte limits, and records with excess fields. The existing V1 modality/chronology, 28-sphere completeness, mapping-history, and source immutability tests remain in the suite.

Implementation and tests are on the isolated PR #26 research branch only. The independent trust adapter remains fail-closed. V1 `usable_contests` remains source-structure output only; it is not target pre-close eligibility or authenticated evidence.

## Official source status observed at 01:55:45, 24-Nov-2026 (America/Mexico_City)

- The dedicated Lotería Nacional Chispazo results page still showed 12392 dated 23-Nov-2026, combination 06 11 16 23 28, with 24-Nov as the next draw date. Its recent-results table also showed 12391 = 03 07 19 20 24.
- The official Mascarillas index listed RESULTADOS 2026-11-23 as its newest Chispazo-linked result package. The one-page PDF text includes contests 12391 and 12392 and their combinations, but does not explicitly label the two Chispazo modalities.
- The official Chispazo product page states De las Tres at 15:00 and Clásico at 21:00. The 23-Nov contest-to-slot assignment is carried forward from the separately recorded official home-index observation; it is not inferred from the mask PDF text.
- SGVO-PRO-05 revision 39, published 20-Mar-2026, remains the public electronic-draw procedure. It specifies per-draw weighing and the automatic close slots. It is procedural context, not proof of any specific draw's compliance.

Sources:
- https://www.loterianacional.gob.mx/Chispazo/Resultados
- https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-23.pdf?v=23112026215757
- https://www.loterianacional.gob.mx/Chispazo/Chispazo
- https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

The rendered official PDF page was visually inspected, but the original PDF byte stream could not be downloaded into the working artifact store during this cycle; no source-byte SHA-256 is claimed. Original HTML bytes were also not captured. No 24-Nov draw result, signed Acta, signed participation file, CS-11 original, 28-measurement strip, calibration record, machine/contest linkage, sphere mapping, RFID trace, independent custody receipt, trusted timestamp, or two independent pre-close output seals were obtained. Public results and procedure must not be upgraded to physical provenance.

## Safety state

No V294 or canonical-history changes; no write to `main`; no merge or promotion. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`. This audit does not establish any 4/5 or 5/5 predictive edge.
