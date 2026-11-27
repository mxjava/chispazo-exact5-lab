# Official Chispazo sequence-source discovery — 2026-11-23

**Status:** SOURCE LOCATED; ORIGINAL CSV NOT CAPTURED; CLASSIC SEQUENCE NOT AUTHENTICATED  
**Scope:** research-only provenance and sequence reconstruction  
**PR:** #13, draft; no merge or promotion

## Finding

The official Lotería Nacional "Números Ganadores" page exposes a dedicated link labelled "Histórico Chispazo" (link 60 in the page navigation). Its target is:

`https://loterianacional.gob.mx/Documentos/Historicos/Chispazo.csv`

The official product page states that Chispazo has two daily modalities: De las Tres at 15:00 and Clásico at 21:00. The official results page independently lists the two draws on 2026-11-22 as 12389 and 12390, respectively; the official results mask for that date identifies 12390 as Clásico. These sources establish that a global contest sequence interleaves modalities.

## Retrieval limitation

The official CSV endpoint was resolved from the official page, but the current research environment did not successfully retrieve its response body. The web reader rejected the CSV content type and the container download attempt failed. Therefore this repository does **not** claim to have captured the official CSV bytes, computed its SHA-256, inspected its schema, or verified its modality column.

A third-party mirror/search result describes a CSV schema with a `Sorteo` field, but that is not an authoritative substitute and must not be used to certify a sequence manifest.

## Required capture procedure

1. Retrieve the CSV directly from the official endpoint using a controlled acquisition host.
2. Preserve the exact response bytes, HTTP headers, retrieval timestamp, TLS/host details and acquisition operator record; do not normalize or reserialize the source.
3. Compute SHA-256 and byte length over the exact response body and store it in immutable, independently controlled custody.
4. Inspect the raw header and every row; establish whether modality is explicitly represented and how values map to "De las Tres" and "Clásico".
5. Reconcile every row against official result masks/official daily results over overlapping dates, recording exceptions and corrections.
6. Build a derived Classic-only ordinal table only from rows whose modality is explicitly supported by official source evidence. Preserve the original global contest ID and source row locator for every derived row.
7. Have an independent reviewer verify the derivation, completeness, duplicates, missing dates, modality assignments and digest before publishing a signed manifest.
8. Do not populate `declared_classic_sequence_refs` from an unauthenticated caller list and do not treat a locally generated ordinal as an official manifest.

## Acceptance rules

- A global contest ID is never assumed to be a Classic-only ordinal.
- A date/time schedule inference is not sufficient to classify an individual historical row when the official result record does not explicitly identify modality.
- Third-party mirrors are discovery/cross-check aids only, never authoritative evidence.
- Missing, ambiguous, duplicate or conflicting rows block manifest issuance; no silent interpolation.
- Until the official CSV bytes and independent row-level reconciliation are captured, `official_classic_sequence_manifest_ref` and digest remain unavailable and V317.1 remains blocked.

## Sources

- Official historical-results index: https://loterianacional.gob.mx/DatosAbiertos/NumerosGanadores
- Official CSV target resolved from its "Histórico Chispazo" link: https://loterianacional.gob.mx/Documentos/Historicos/Chispazo.csv
- Official Chispazo modality/time description: https://loterianacional.gob.mx/Chispazo/Chispazo
- Official results page: https://www.loterianacional.gob.mx/Chispazo/Resultados

## Current conclusion

A first-party historical data source has been located. It is **not yet an authenticated Classic-only sequence manifest**. No sequence manifest, physical continuity claim, predictor activation or production eligibility is created by this discovery.
