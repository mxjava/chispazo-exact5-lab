# Changelog

## 0.3.0
- Added chronological and expanding-window evaluation splits.
- Added paired prequential log-score summaries and exact sign testing.
- Applied Holm-Bonferroni to the complete declared family, including ORIGEN's internal sign test.
- Added adversarial-null empirical benchmarking.
- Added frame diversity diagnostics.
- Added SHA-256 manifests and tamper verification.
- Added MetaObserver search-path audit for preregistration ordering and post-outcome adaptation.
- Added CLI interfaces, examples, and 28 unit tests.
- Kept research-only classification; no automatic prediction, promotion, or repository mutation.

## 0.3.1 research hardening (2026-11-19)
- Added pre-close custody record verification with exact schema, candidate-specification hash binding, independent generator/custodian identities, strict UTC ordering, and hash-linked ledger verification.
- Added adversarial tests for altered bytes, record mutation, duplicate targets, deleted/reordered ledger entries, invalid timestamps, and exclusive file creation.
- Implemented the preregistered V316 identity-resolved temporal persistence omnibus: 8,140 statistics across 20 lags, all 28 number identities, all 378 pair identities, and aggregate overlap.
- V316 uses packed-bit pair counts with an independent nested-loop reference oracle; frozen source digest, Classic sample count/boundaries, PCG64 seed 3162026, and 1,999 null simulations are enforced.
- Added an isolated GitHub Actions workflow for the V316 confirmatory historical falsification run. Its output remains research-only and cannot establish prospective predictive edge.
- No change to V294, canonical history, or main; PR remains draft and unmerged.

- Completed frozen V316: 7,723 Classic draws, 8,140-cell maximum family, 1,999 simulations, seed 3162026; observed max |z|=3.70796 vs null 95th percentile 5.85308, Monte Carlo p=0.9995. No rejection and no predictive edge. Report: docs/V316_IDENTITY_PERSISTENCE_RESULT_20261119.md.

## Physical intake validator v1 (2026-11-19)
- Added a long-form physical evidence template with one row per physical sphere and contest; header-only, no fabricated data.
- Added strict validator for 28-sphere completeness, unique physical IDs, exact 1–28 mapping, pre-close timestamps, calibration coverage, units, positive finite mass/resolution, SHA-256-shaped provenance identifiers and within-contest consistency.
- Quarantine labels are explicit; validator does not repair data or estimate bias.
- Added CLI: `origen validate-physical --file <csv>`.
- Added 13 adversarial intake tests. Awaiting final GitHub Actions result on the latest branch head.

## V317 physical-mass Plackett–Luce preregistration (2026-11-19)
- Added exact unordered five-set likelihood for sequential weighted sampling without replacement; no arbitrary draw order is assumed.
- Added log-likelihood ratio against exact uniform 5-of-28 and the corresponding prequential e-process design.
- Added tests against all 120 permutations for a chosen set, normalization over all 98,280 possible sets, uniform beta=0 recovery, and invalid input rejection.
- Preregistered the physical mass test; beta must be independently calibrated on equivalent equipment and frozen before Chispazo outcome labels are inspected. No primary measurements/beta calibration exist; V317 remains blocked, no predictions.

## V318 combinatorial-shape omnibus (2026-11-19)
- Preregistered seven fixed result-only shape families before replay.
- Added exact 98,280-set category probability enumeration and one global Monte Carlo max-statistic test over all categories/families.
- Added adversarial tests for set encoding, feature contracts, exact probability normalization, frozen simulation/source guards and sample-size guards.
- Added isolated GitHub Actions workflow to run unit tests and the 1,999-replicate canonical Classic replay.
- No physical sphere masses or mapping are inferred from the historical winning-number file; no predictive or causal claim is permitted.

### V318 result (2026-11-19)
- Full suite: 140 tests passed; frozen canonical replay and artifact upload succeeded (run 44446819621).
- Global maximum z=2.7721; null q95=4.4837; Monte Carlo p=0.7855 (1,570/1,999 exceedances). `NO_REJECTION`.
- No shape family or category is promoted; no prediction or physical-bias claim.

## V319 fixed-era contrast (2026-11-19)
- Preregistered one fixed era split at 2022-03-10, inherited from V265 rather than selected by this replay.
- Implemented a single max-statistic over 28 number identities, 378 pair identities and 184 V318 shape categories, calibrated using 1,999 pairs of independent uniform era sequences.
- Added numerical, shape, frozen-seed, source-hash and minimum-sample tests plus an isolated workflow.
- A result can indicate only a historical era difference, not a causal machine effect or predictive edge.

### V312 full static mixture result (2026-11-19)
- Canonical Classic-only replay completed successfully (run 44446737614): 7,723 draws, 800 warm-up, 6,923 scored targets.
- Mean log-lift -0.0262296890 nats; cumulative -181.5881; positive fraction 36.07%. Candidate underperformed uniform; no edge.

### V319 result (2026-11-19)
- 146 tests passed; full fixed-era replay and artifact upload succeeded (run 44447156133).
- Era A n=6,075; era B n=1,648; global max z=4.3320; null q95=6.8491; Monte Carlo p=0.1820. `NO_ERA_DIFFERENCE_DETECTED`.
- No causal equipment attribution or predictive signal.


## Trust-receipt timestamp binding and official 22-Nov refresh (2026-11-22)
- The unverified receipt parser now requires the trusted-time proof selected by `receipt_attestation.timestamp_proof_sha256` to carry the same `event_at_utc` as `receipt_attestation.signed_at_utc`. This is an internal consistency check only; it does not verify an RFC 3161 token or authenticate the clock/authority.
- Corrected the synthetic valid fixture and added an adversarial regression test for a one-second mismatch.
- Added status-only overlay `data/official-overlays/2026-11-22_2158_official_status_only.json`. Official Home index places contest 12389 at 15:00 and contest 12390 at 21:00; the official product page maps those slots to De las Tres and Clásico respectively.
- At the 21:58 local observation, official results endpoints still showed 12389 (01 15 17 22 25) and no 12390 combination; the mask index still listed 21-Nov as newest. Contest 12389 is schedule-slot matched to De las Tres, not same-day-mask confirmed.
- No 22-Nov original mask bytes, signed draw act, signed participation file, CS-11, weighing strip, measurements, calibration certificate, trusted timestamp, independent custody receipt, or pre-close seal were obtained. No canonical append, V294 change, main write, merge, or promotion.
- Validation of the parser/test change on commit `7e710244c0975a552aac4399f8a371d1f4287f81`: isolated ORIGEN run `45109181485` passed **323 tests**; root CI run `45109181527` passed `compileall` and `pytest -q` (**525 passed, 2 skipped, 92 subtests passed**). The subsequent overlay/changelog commits are data/documentation only and do not alter executable code; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
