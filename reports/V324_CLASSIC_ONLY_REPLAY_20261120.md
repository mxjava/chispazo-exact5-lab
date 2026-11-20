# V324 — Clásico-only retrospective replay (inferred modality)

Date: 2026-11-20  
Branch: `research/v249-snapshot-integrity-20261119`  
Workflow run: [44757412786](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44757412786) — **success**  
Workflow head: `67f60623d4dd91318f35c762d917b0f49efc1e4f`  
Artifact: `14637882334` — SHA-256 `35ca40d517ffed8e574184488ed4a80ca10d699ac162e3366107ce992201e4e0`

## Why this replay was necessary

The canonical history `data/history/Chispazo_through_12249.csv` contains no product/modality field. Earlier V264/V323 results therefore mixed an unresolved sequence. V324 adds a conservative filter: it excludes the single-draw historical era and selects only even contest IDs from the first complete two-draw-per-date sequence.

## Modality evidence and limits

The canonical file contains 10,887 rows (contests 1363–12249). Structural audit found:
- 4,560 single-draw rows from contests 1363–5922; these are left **unclassified and excluded**.
- The paired sequence begins on 2017-09-25 with contests 5923 and 5924.
- From 5923 through 12248, the file contains 3,163 complete same-date consecutive pairs, always odd/even.
- Contest 12249 is the final unpaired odd row in this frozen file and is excluded.
- The selected even-ID history contains 3,163 inferred Clásico contests (5924–12248). The next inferred Clásico contest after this frozen history is 12250; contest 12249 is the excluded odd-ID draw. The workflow corrects V264's mechanical sequential-next-ID field to this Clásico-specific target. This is target indexing only, not a prediction.

Official Lotería Nacional material supports the parity direction at multiple independent 2026 anchors:
- Official product page states Chispazo de las Tres at 15:00 and Chispazo Clásico at 21:00: https://www.loterianacional.gob.mx/Chispazo/Chispazo
- 2026-10-25: 12333 De las Tres / 12334 Clásico: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-10-25.pdf
- 2026-11-03: 12351 De las Tres / 12352 Clásico: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-03.pdf
- 2026-11-08: 12361 De las Tres / 12362 Clásico: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-08.pdf
- 2026-11-10: 12365 De las Tres / 12366 Clásico: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-10.pdf
- 2026-11-15: 12375 De las Tres / 12376 Clásico: https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-15.pdf

**Classification is inferred, not row-level officially certified.** The canonical CSV has no official modality tag. The parity rule is supported by the uninterrupted paired sequence and official schedule/result anchors, but no source label was available for every historical contest. V324 therefore remains a sensitivity analysis, not certified Clásico-only evidence. The pre-pair era is not assigned a modality.

## Replay design

- Filtered history: 3,163 contests, 5924–12248, even IDs only.
- V264 prequential replay, warmup 800 Clásico draws.
- Evaluated targets: 2,363, contests 7524–12248.
- Experts: 28.
- V323 candidate family: static full Bayes plus nine rolling mixtures (windows 100/250/500 × eta .25/.5/1).
- Multiplicity: joint circular moving-block bootstrap, block length 30, 5,000 resamples, seed 20261120; single-step maxT one-sided FWER adjustment and simultaneous two-sided 95% max-absolute-t intervals.
- Max-absolute-t 95% critical value: 2.5096479068.

## Results

| Candidate | Mean log-lift | maxT adjusted p | Simultaneous 95% CI |
|---|---:|---:|---:|
| Static full Bayes | -0.001410158 | 0.99660 | [-0.004040375, +0.001220058] |
| Rolling W100, eta .25 | -0.016011799 | 1.00000 | [-0.024503127, -0.007520472] |
| Rolling W100, eta .5 | -0.012242660 | 1.00000 | [-0.019840907, -0.004644412] |
| Rolling W100, eta 1 | -0.009208676 | 1.00000 | [-0.016414736, -0.002002617] |
| Rolling W250, eta .25 | -0.007675690 | 1.00000 | [-0.013309431, -0.002041949] |
| Rolling W250, eta .5 | -0.004686675 | 1.00000 | [-0.008869631, -0.000503720] |
| Rolling W250, eta 1 | -0.003539890 | 1.00000 | [-0.007201153, +0.000121373] |
| Rolling W500, eta .25 | -0.003021233 | 1.00000 | [-0.005979248, -0.000063217] |
| Rolling W500, eta .5 | -0.001866140 | 0.99960 | [-0.004372604, +0.000640325] |
| Rolling W500, eta 1 | -0.001410504 | 0.99960 | [-0.004040721, +0.001219712] |

V264 summary on the same filtered replay:
- Mean log-lift: -0.0014101585.
- Cumulative log-e: -3.3322045102.
- E-value: 0.0357142857 (1/28), far below the existing promotion threshold of 20.
- Posterior mass on uniform expert: 1.0.
- Top-30 mass lift: 1.0 (effectively uniform).

## Decision

`V324 = RESEARCH_ONLY_NO_EDGE`.

1. No candidate has positive mean log-lift.
2. No candidate has favorable multiplicity-adjusted evidence; adjusted p-values are approximately 1.
3. W100 and W250 eta=.25/.5/1 and W500 eta=.25 have simultaneous intervals entirely below zero: adaptive forgetting harms performance.
4. Static full Bayes and the least-bad W500 settings are indistinguishable from zero, not an edge.
5. The V264 mixture collapses to uniform and its e-value does not pass the promotion gate.
6. No 5/5 capability or prospective betting advantage is demonstrated.

This is a useful negative result: separating the inferred Clásico sequence does not recover the signal that was absent in the mixed-sequence replay. Do not alter frozen V294 from this result; do not promote or merge.

## Integrity hashes

- Filtered Clásico history CSV: `0b801bf1ea7692d6e684bed72024fad1e2777cee064adb85dce4d90122f25436`
- Expert score CSV: `8742e4d792047f4d343ea4a3e83c3d4ffbdf76a776ead43a8c363a73fa223d5d`
- maxT JSON: `2757da3f8cafe36bffb1e362a23c402f1d70a4ddc5f69d3dbaf3372f2b311cc6`

The canonical history file and V294 were not modified. The replay ran on the research branch only.
