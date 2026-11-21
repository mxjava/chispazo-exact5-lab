# Changelog

## 0.3.2 custody receipt binding (2026-11-20)
- Found a provenance gap: the external receipt signed selected manifest fields but did not commit to the complete manifest bytes, leaving history cutoff/hash, environment metadata and other manifest fields mutable without invalidating the receipt.
- Bumped the independent receipt schema to 1.1 and require `manifest_sha256`, computed over the exact raw manifest bytes received by the custodian.
- The verifier now rejects a manifest object that differs from its captured bytes and rejects any receipt whose signed manifest digest does not match those exact bytes.
- Added regression tests for post-receipt mutation of `input_history_sha256` and for a parsed manifest object that does not match its captured bytes.
- A second TOCTOU review found that the CLI re-opened private temporary snapshots between structural validation and Cosign. It now captures all four inputs once in memory and passes the same receipt bytes to structural validation/Cosign and the same bundle bytes to Cosign/Rekor parsing; regression coverage mutates the original source paths during the Cosign call.
- No real receipt or custody event was created; this is a verifier-contract change only. External custodian, signature, trusted timestamp, independent retention, two witnessed dry-runs and physical evidence remain outstanding.
- V294, challenger, canonical history and `main` remain untouched.


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

## 2026-11-20 — Custody verifier contract and source refresh

- The independent receipt verifier now validates the complete manifest v1.0 key set and semantic constraints: positive Classic contest ID, prior history cutoff, 40/64-character source and history digests, valid IANA timezone, HTTPS gob.mx schedule source, safe data/schedule-evidence/ archive path, and generation strictly before close.
- The verifier now requires the exact archived schedule-evidence bytes (--schedule-evidence) and checks their SHA-256 against the manifest. It validates the candidate payload as exactly 30 unique canonical LF lines, each containing five distinct ascending values from 01 through 28.
- Receipt chronology is strict: generation < independent receipt < official close. Structural validation remains separate from Cosign/Rekor signature verification and does not establish legal custodian independence or source authenticity by itself.
- V324/V325/V326 historical audits are now workflow_dispatch only. Unrelated research-branch pushes no longer replay these closed retrospective analyses.
- Added status-only official-source overlay 2026-11-20_225251_source_refresh_status_only.json: 12385 = 03 13 20 22 23 (De las Tres); 12386 is scheduled Classic at 21:00 but remains blank in official Home/Resultados at the observation; the official mask index remains at 19-Nov. The commercializer dedicated extract remains stale at 12384.
- No canonical append, no use of append_verified_result.py, no V294/challenger change, no main write, and no promotion. Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.

- Physical-evidence request expanded from the current Normateca listing for SGVO-PRO-05 rev.39 (published 20-Mar-2026): adds the Chispazo-specific CLSBR140/CLIER195/CLSKR170/CLSAR110 reports, both draw summaries, weekly signed-record media and delivery trail, CS-12 access logs, CS-18 risk reports, SEGOB commission/attendance, OIC act transmittal, and the signed participation-file custody chain. The documented Smartballs/Ping Pong weight limits are treated as procedure criteria only, not observed measurements.
