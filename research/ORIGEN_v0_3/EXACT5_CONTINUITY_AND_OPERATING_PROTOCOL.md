# Exact5 — Operating protocol and continuity contract

Status: active working contract
Scope: Exact5 Algorithm Lab / Chispazo Clásico
Research branch: `research/origen-v0.3-engine-20261118`

This file preserves the user's standing instruction: continue the research proactively without waiting for a separate confirmation after every completed step. Short directives such as “adelante”, “continúa”, “dalo todo” and “avanza” authorize the next complete research cycle.

## Execution loop

1. Recover current repository state, open experiments, artifacts, logs, and prior decisions before starting new work.
2. Select the next experiment or correction based on expected information value; do not repeat closed work without a documented reason.
3. Preregister hypotheses, test families, null models, seeds, sample rules, and stopping/decision rules before computation.
4. Implement in isolated research scope; add regression tests for every discovered defect.
5. Run focused tests, full isolated ORIGEN tests, canonical replay, and relevant CI.
6. Independently inspect logs, artifact contents, hashes, sample boundaries, and numerical results. A green workflow alone is not sufficient if the analysis has not been reviewed.
7. Record result, limitations, classification, artifact identifiers, hashes, and next decision in the repository.
8. Continue to the next useful cycle without asking the user to re-authorize routine research steps.
9. Report substantive outcomes, including negative results and blockers. Never represent activity as predictive progress.

## Non-negotiable invariants

- Keep V294 frozen: weekday × (múltiplos de 4, pares consecutivos), alpha=200, selection 1-SE.
- Keep canonical history `data/history/Chispazo_through_12249.csv` byte-for-byte unchanged. Baseline SHA256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Do not write to or merge into `main`.
- Research only on `research/origen-v0.3-engine-20261118` unless the user explicitly changes scope.
- No invented results, no post-hoc claims of advantage, and no use of retrospective patterns as betting predictions.
- Do not merge PR #8 until required CI is green and independent review is complete.
- Preserve modality separation: Classic only for Classic tests; exclude De las Tres from features, warm-up, and scoring unless a preregistered experiment explicitly studies it.
- Treat physical-mechanism evidence as blocked until primary records with pre-close availability, sphere-to-number mapping, actual individual masses, machine/set, calibration, timestamps, and chain of custody are obtained.

## Evidence gates for any edge claim

A candidate is not an established edge. The required prospective evidence includes at least 100 chronological untouched Classic OOS draws, positive preregistered prequential lift, Holm-adjusted p < 0.05, Exact5 anytime e-value >= 20, two sealed prospective outputs, independent custody, and clean integrity hashes. All gates must be independently verified. Otherwise retain a non-edge or blocked classification.

## Current experiment ledger pointer

- V313 global null: no family rejects after max-stat Monte Carlo calibration; research-only historical falsification.
- V314 triple motif: max-stat Monte Carlo p=0.9825; no supported motif; research-only.
- V315 pair-conditioned transition: corrected run passed; max-stat p=0.591; no rejection; research-only, not predictive.
- V315 corrected implementation commit: `b17b3747282d36c4dd001ebde32fbf5c2e98e914`.
- V315 workflow: [44438922372](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44438922372).
- The first V315 run on the preceding implementation failed tests and produced no accepted artifact; the defect was fixed before accepting the result above.

## Next-work selection

Prioritize primary physical traceability records and robust prospective custody design over unconstrained retrospective motif mining. Any further retrospective search must preregister the complete search family and calibrate the maximum statistic for all searched cells. If a candidate emerges, test it only in untouched prospective data; never retrofit V294.


## Operational update — 2026-11-19

- Corrected malformed YAML in `.github/workflows/origen-v03.yml`: the two `with` mapping keys for artifact uploads now include their required colon.
- Fix commit: `46d211d062808a5424773349d6f7654eb68010e0`.
- Root CI for that commit completed successfully: run `44440351832`; dependency install, compileall and full `pytest -q` all succeeded.
- The isolated ORIGEN workflow definition was re-read after the fix and its artifact upload steps now have valid `with:` mappings. A successful isolated workflow run on this exact commit is still required; root CI success does not substitute for it.
- PR #8 remains open, draft and unmerged. No changes to `main`, V294, or the canonical history are authorized.
- Physical-bias request V2 remains a draft and has not been submitted. No primary weighing strips or sphere-to-number mapping have been received; status remains `BLOCKED_PROVENANCE`.
- Next action: verify the isolated workflow on the corrected branch head, then continue physical-evidence acquisition preparation and prospective custody design. Do not mine additional retrospective motifs absent a materially new hypothesis.


## Operational update — integrated ORIGEN validation confirmed (2026-11-19)

- Verified branch head: `148b4ae10b1df0624fa9b7574a08ec9855b881bc` on `research/origen-v0.3-engine-20261118`.
- The corrected integrated ORIGEN workflow was triggered by PR #8 and completed successfully: run [44441010244](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44441010244), conclusion `success`.
- Job `unit-tests` succeeded. Independently inspected step summaries: isolated ORIGEN tests, Classic-only modality audit, frozen V312 retrospective replay, preregistered V313 global-null replay, and all three artifact uploads completed successfully.
- Artifacts produced on this run:
  - modality audit: ID `14490918644`, SHA-256 digest `f0a754a0d3460caa668bf9d0a000b475c33c582f30f3cdde2a9dd3d9bf2ec71a`;
  - V313 global-null: ID `14490898632`, digest `9e69b58697f28ea9a45905cf8ed033dbc9c6890c81616422efaf7134c6bfcb7e`;
  - V312 retrospective integrity: ID `14490404318`, digest `3ab31395eda64cf986e9f8ec6fbfa59b99cd913bdc7f88d7f66c77787d2d3cf8`.
- PR #8 remains open and draft. Its base is `main` at `58ff8e609fc62e540ab9226ebdb01782b3301fdc`; no merge was performed.
- Main remains at the protected baseline SHA above. The canonical history remains governed by the established SHA-256 baseline; this workflow used it read-only. V294 remains frozen.
- This closes the prior isolated-workflow validation blocker. It does not establish predictive edge: V312 remains retrospective and negative; V313 rejects none of its global-null families; physical primary records and independent prospective custody are still absent.
- Next high-value work: build a concrete sealed prospective-custody specification and operator checklist (two pre-close outputs, immutable timestamped hashes, independent witness/custodian, draw-close boundary, append-only score ledger, failure/recovery rules), then separately pursue primary weighing strips and sphere-number mapping. No government request is submitted without the user's explicit instruction.


## Operational update — custody hardening and V316 (2026-11-19)

- Implemented src/origen/custody.py with exact-schema validation, candidate specification hash binding, distinct generator/custodian identifiers, strict pre-close timestamp ordering, exact portfolio byte binding, exclusive create-only file writes, ordered ledger-chain verification, and optional externally anchored ledger-head verification.
- Custody tests cover byte tampering, record mutation, role collision, equal/late timestamps, wrong modality, malformed numeric IDs, duplicate portfolio lines, invalid hashes, record overwrite, chain deletion/reordering, and external head-anchor detection. A first CI pass exposed two test expectation mismatches; the assertions were corrected rather than suppressing the failures. The latest complete run is pending.
- Implemented V316 from the already frozen preregistration: one max-statistic family of 8,140 cells (20 lags; aggregate overlap; 28 number identities; 378 pair identities), Classic-only, exact 5-of-28 null, fixed canonical source digest/count/boundaries, PCG64 seed 3162026 and exactly 1,999 simulations.
- V316 pair counts use packed-bit intersections with a direct nested-loop reference oracle. Its dedicated workflow is .github/workflows/v316-identity-persistence.yml; latest execution is pending. No V316 result or signal is claimed.
- V313/V314/V315 remain unchanged and their accepted historical conclusions remain no rejection/no edge. V316 is a new frozen confirmatory retrospective falsification, not a predictor.
- The custody implementation does not authenticate identity or time and does not create immutable storage. An independent custodian, trusted timestamp evidence, and an externally retained ledger-head anchor remain operational prerequisites.
- Current branch remains research-only; PR #8 remains draft/unmerged. V294 and the canonical history remain protected; no writes to main.

- V316 completed successfully on final dedicated workflow [44444654369](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44444654369), commit 6479a6c5aebac4a603c3e883f2c15aff4a145080; artifact ID 14491733775, ZIP SHA-256 f4d293fd765bffe6a218cc1edc6acde8d4063ea79c236b354a2458735338f554. N=7,723 Classic; family=8,140; simulations=1,999; seed=3162026; observed max |z|=3.70796; null 95th percentile=5.85308; Monte Carlo p=0.9995. No rejection, no predictive edge. Full report: docs/V316_IDENTITY_PERSISTENCE_RESULT_20261119.md.


## Repository boundary incident — 2026-11-19

- During V316 result publication, one create-file operation omitted the explicit research-branch argument and therefore wrote the result report to the default branch main. This was an operator error.
- The exact accidental commit `8e0e6ec4aa9811590333510024e7e39e72c1407c` changed only `research/ORIGEN_v0_3/docs/V316_IDENTITY_PERSISTENCE_RESULT_20261119.md`; it did not touch the canonical history, V294, or any other path.
- The report was immediately deleted from main in remediation commit `424eee9dd906f8235541e97ae61026441083bbfe`; a read of the default-branch path returned NOT_FOUND afterward. The correct report was then created on the research branch at `986429c1f03fd3182a0289a025245592697e005f` and subsequently updated there only.
- Current tree comparison confirms the canonical history and V294 paths were not touched. Main's tree no longer contains the report. Main history retains the add/delete pair; the research branch is two commits behind main because it does not include those main commits. Do not merge PR #8 until the branch/base relationship is deliberately reconciled and reviewed.
- This incident is recorded rather than concealed. Continue to pass `branch: research/origen-v0.3-engine-20261118` explicitly on every GitHub create/update operation; verify target branch and compare protected paths after writes.

## Physical evidence intake and V317 (2026-11-19)

- Added long-form header-only template `data/physical-metadata/PHYSICAL_EVIDENCE_LONG_FORM_TEMPLATE_V1.csv`, one row per physical sphere per contest. No measurements have been inserted.
- Added `src/origen/physical_intake.py`, `tests/test_physical_intake.py`, and CLI command `origen validate-physical --file <csv>`. The validator enforces 28 rows per contest, unique physical sphere IDs, exact printed-number coverage 1–28, pre-close set/measurement/mapping timestamps, timezone offsets, calibration interval coverage, finite positive gram values/resolution, source hashes and within-contest consistency. It quarantines; it does not repair or score.
- Legacy wide template `V265_PHYSICAL_METADATA_TEMPLATE_FULL.csv` remains unchanged and is not sufficient to establish sphere-ID ↔ printed-number mapping.
- Added `src/origen/plackett_luce.py` and tests for an exact unordered-set likelihood under sequential weighted sampling without replacement. It sums all 120 extraction orders rather than assigning an arbitrary order; it can audit normalization across all 98,280 possible 5-of-28 sets.
- Added preregistration `PREREGISTRATION_V317_PHYSICAL_MASS_PLACKETT_LUCE.md`. A signed beta must come from independent calibration on materially equivalent equipment and be frozen before Chispazo outcome labels are inspected. Without that external calibration and authenticated pre-close sphere records, V317 remains BLOCKED_PROVENANCE; no number ranking is produced.
- Latest code/test workflow [652f3bf](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44445677893): isolated ORIGEN unit-test step passed; the subsequent canonical modality audit and frozen replay steps were still running at last inspection. Do not call the whole workflow green until it completes.
- The ORIGEN workflow path filter now excludes documentation-only changes and runs only for source, tests, package metadata, canonical history, or workflow changes, avoiding expensive replay for report edits.
- Repository comparison at head ade660bc: research branch 160 commits ahead and 2 behind main; no diff touches canonical history or V294. PR #8 remains draft/unmerged. Do not merge while the branch is diverged; reconcile deliberately after reviewing the two base commits.
## V317 numerical regression correction

- First full ORIGEN test run after adding the exact Plackett–Luce kernel executed 129 tests and found one overly strict floating-point assertion: the centered log-weight sum differed from zero by 1.40e-12. The likelihood kernel, explicit 120-order oracle and 98,280-set normalization test passed.
- Corrected only the test tolerance from 13 to 11 decimal places; no model equation, beta definition, likelihood or data gate was changed. Fix commit: `74bc8551be36c2dbcf09839f42ef241bad00f56a`.
- A new isolated test workflow was queued for that fix at last inspection. Until it completes, V317 code validation is not declared green.
## V317 implementation validation — corrected and green

- Corrected test run [44446185498](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446185498), commit `8e017e84f64451bb2ea9765574dfae82ca9bf2b3`, completed successfully: 132 tests passed in 12.744 seconds.
- This includes all 13 physical-intake tests, exact enumeration/normalization of all 98,280 unordered five-number sets, the 120-order Plackett–Luce reference check, and three prequential e-process tests.
- The prior one-test failure was only the overly strict floating-point assertion documented above; the corrected run is green. No statistical model equation or preregistered decision gate was relaxed.
- Separate canonical replay integrity workflow [44446179906](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446179906) and root CI were still running at last inspection; do not conflate the green isolated test suite with those pending workflows.

## V318 historical shape omnibus — completed negative (2026-11-19)

- Preregistered seven fixed result-only shape families before execution: sum, range, odd count, prime count, consecutive adjacent-pair count, low/high split, and three-band occupancy.
- Used exact category probabilities from all 98,280 possible 5-of-28 sets and a single global max-statistic calibrated on 1,999 complete uniform Classic sequences (PCG64 seed 3182026).
- Canonical Classic sample: 7,723 draws, contests 1363–12248, source SHA-256 `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- CI/replay: [run 44446819621](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446819621), success; 140 tests passed; artifact ID 14493333027, ZIP SHA-256 `8f624f6c32769fe022262049a9e7afb7688d29d588630a5dfde2548651e22445`.
- Global max z=2.7721136; null 95th percentile=4.4836559; 1,570/1,999 null replicates at least as extreme; global add-one p=0.7855. Decision `NO_REJECTION`.
- Result document: `docs/V318_COMBINATORIAL_SHAPE_RESULT_20261119.md`. This closes only these seven descriptive shape families; it does not establish perfect randomness or a predictive edge.
- V318 does not recover physical mass or sphere identity from winning-number history. The physical-covariate hypothesis remains blocked until authentic primary records and mapping arrive.


## V312, V318 and V319 historical replays — 2026-11-19

- V312 fixed 27-expert static mixture: run [44446737614](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446737614) completed successfully. 7,723 Classic draws, 800 warm-up, 6,923 scored; mean log-lift -0.0262296890 nats, cumulative -181.5881, positive fraction 36.07%. The static mixture underperformed uniform. Result: `docs/V312_STATIC_MIXTURE_RESULT_20261119.md`.
- V318 fixed seven-family result-shape omnibus: run [44446819621](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44446819621) completed successfully; 140 tests passed. Global max z=2.7721; null q95=4.4837; p=0.7855. No shape departure detected. Result: `docs/V318_COMBINATORIAL_SHAPE_RESULT_20261119.md`.
- V319 fixed-era contrast at 2022-03-10: run [44447156133](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44447156133) completed successfully; 146 tests passed in 17.027s. Era A n=6,075, Era B n=1,648; 590-category global max z=4.3320; null q95=6.8491; 363/1,999 null replicates >= observed; p=0.1820. No era difference detected. Result: `docs/V319_FIXED_ERA_CONTRAST_RESULT_20261119.md`.
- V318 and V319 both use exact 98,280-set shape-category probabilities and full-sequence Monte Carlo. They are retrospective falsification only; neither establishes a forecast edge or a machine/physical cause.


## Operational update — V320 physical-intake hardening and official contest 12382 overlay (2026-11-19)

- Reverse-engineered `src/origen/physical_intake.py` against the official SGVO-PRO-05 operating envelope and the repository's intake protocol. The old validator accepted any finite positive mass and arbitrary sphere-type text, did not enforce max within-set spread, and did not enforce consistent scale/calibration/mapping/assignment identity across the 28 rows.
- Research-only fix commit: `3a291538007c34821ce63c17f1b3f84ef7de5b17`. It enforces Smartballs 4.25–5.25 g / max spread 0.30 g; ping-pong 2.30–3.00 g / max spread 0.15 g; known sphere types; mapping validity no later than set assignment; strict YYYY-MM-DD draw dates; and consistent per-contest set, scale, resolution, calibration, mapping activation and source identity fields.
- Six adversarial tests were added for range/spread, unknown sphere type, inconsistent scale/calibration identity, late mapping activation and malformed date. Isolated run `44469124625`: success, 152 tests passed. Root CI `44469124280`: success, 351 passed, 2 skipped, 16 subtests passed.
- Explicit limit: this validator still cannot authenticate source bytes, signatures, independent clock, mapping source, or remap/incident history. It validates structure and operating envelope only. No physical observations have arrived; no mass-effect model was fitted.
- Added status-only official overlay `data/official-overlays/contest_12382_status_only.json` and report `docs/CONTEST_12382_OFFICIAL_STATUS_ONLY_20261119.md` on the research branch. Official dedicated result page and daily mask PDF agree: contest 12382, 18/11/2026, **05-09-11-23-25**. The PDF explicitly labels 12381 De las Tres and 12382 Clásico. Mask index lists 2026-11-18.
- Raw PDF bytes could not be captured; source SHA-256 remains NOT_CAPTURED. The overlay has `snapshot_preclose=false`, `oos_eligible=false`, `score_computed=false`, `canonical_history_appended=false`; classification `BLOCKED_PROVENANCE`. It is not a prospective observation and must not be scored.
- The canonical replay workflow ran twice redundantly on successive PR events because its pull-request path filter evaluated the PR's full historical diff. Runs `44469124306` and `44469441240` repeated frozen V312 historical integrity work; neither output was used as new evidence. Its `pull_request` trigger has now been removed; narrow push-path and manual-dispatch triggers remain to avoid repeating closed retrospective work on unrelated PR updates.
- The 12382 overlay records the exact observation-window start separately from source retrieval time; the exact retrieval timestamp and raw PDF SHA-256 were not captured.
- Current protected canonical blob remains `2f5ff5bfbd779fe505736398e417b7211955958e` in both `main` and the research branch. V294 remains frozen. No writes to `main`, no merge, no promotion, no candidate/challenger change.

Classification remains `BLOCKED_PROVENANCE / RESEARCH_ONLY_NO_EDGE`.


## Operational update — V320 second-pass adversarial correction (2026-11-19)

- A second reverse-engineering pass found a strict-format gap: Python `datetime.strptime("%Y-%m-%d")` accepts non-zero-padded dates (for example `2026-1-2`). The intake validator now requires an exact four-two-two digit date with a regex before calendar validation. Added the adversarial regression test.
- Fix commit: `73e6bf44ece2971bedceb58c110a742e0febee16`.
- Final isolated ORIGEN: runs `44470243887` (push) and `44470250160` (PR), both success, 153 tests passed.
- Final root CI: run `44470243842` success, 352 passed, 2 skipped, 16 subtests passed; PR run `44470250079` also success.
- The earlier 152-test run remains recorded as the first pass; the 153-test result supersedes it for current validation. No physical records or predictive edge were produced.


## Operational update — 2026-11-21 11:53 America/Mexico_City

### Official result/mask overlay
- Status-only overlay: `research/ORIGEN_v0_3/data/official-overlays/2026-11-21_official_result_refresh_status_only.json`.
- Latest schema-v3 correction commit: `eb08acdb6a50ab3b5159348864f52bba075b480b`.
- The dedicated Chispazo results page and the official 20-Nov mask agree on:
  - 12385 — **De las Tres** — 03 13 20 22 23.
  - 12386 — **Clásico** — 02 04 09 18 24.
- The modality labels are explicit on a visual inspection of page 1 of the official mask; the PDF text extraction omits the logo labels. Do not downgrade these two rows to inferred modality.
- Home/Resultados still shows 12386 blank while the dedicated Chispazo page and 20-Nov mask publish it; retain this as a stale endpoint discrepancy.
- The home index advertises 12387 for 21-Nov at 15:00. At the 11:53 observation time no result was published; do not infer a later Clásico ID.
- Original PDF bytes/SHA-256 were not captured. No independent custody or signed pre-close snapshot exists. All overlay rows remain `snapshot_preclose=false`, `oos_eligible=false`, `score_computed=false`.
- No canonical append, no `append_verified_result.py`, no main write, no V294/challenger change, no promotion. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

### V265.1 parallel hardening
- PR #12 remains draft/unmerged: https://github.com/mxjava/chispazo-exact5-lab/pull/12
- Added a fail-closed Classic modality guard requiring explicit `SLOT=21:00` in every physical metadata row; missing/unknown/De las Tres values fail closed.
- Corrected two CLI test fixture builders and an extra-row fixture that initially omitted SLOT. The first post-guard CI failure was a fixture/schema mismatch, not a model result; subsequent latest PR CI run `44932932622` passed `compileall` and **278 tests passed, 2 skipped**.
- Public procedure/audit docs now reference the current evaluator blob `0010b5f07c6cbfcb78201180fbe758d68e61b031`, distinguish pre-close planned set from post-weigh final set, and state that `actionable_for_betting` is hardcoded false.
- Generic timestamp checks and syntactic source hashes are not independent provenance. Physical records, independent custody, untouched OOS and Exact5 promotion gates remain outstanding.

All closed historical runs remain closed. Do not repeat Run53–56 or Run96–106, rebuild retrospective PMFs/ranks/scores, or use `append_verified_result.py` to classify or mutate canonical history without verified modality and provenance.
