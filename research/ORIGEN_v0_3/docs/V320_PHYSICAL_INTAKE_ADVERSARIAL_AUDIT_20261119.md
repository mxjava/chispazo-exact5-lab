# V320 — Physical intake validator adversarial hardening

Status: ENGINEERING VALIDATION ONLY; NO PRIMARY PHYSICAL DATA; NO PREDICTIVE RESULT.

## Scope and protected boundary

This change audits and hardens only the physical-record intake validator. It does not change V294, any candidate/challenger, historical result data, V312–V319 statistical specifications, or the canonical history. It is confined to the research branch.

Base research commit: `905add070fc5dd3c04f2d37385513a79ab7cfd30`.
Canonical history SHA-256 remains `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.

## Reverse-engineering findings

The prior validator checked that mass values were finite and positive, but did not enforce the official operating envelopes described in SGVO-PRO-05. Consequently, a structurally complete set with impossible/out-of-envelope values could be labelled usable. It also accepted arbitrary sphere-type labels, allowed a mapping-validity timestamp later than set assignment, and did not require contest-level consistency for scale identity, resolution, calibration interval, set-assignment time, or mapping activation time. Draw dates were only checked for non-emptiness.

These are intake-quality defects, not evidence of biased extraction.

## Implemented hardening

- Smartballs: each mass must be in [4.25, 5.25] g and the within-set max-minus-min spread must be <= 0.30 g.
- Ping-pong spheres: each mass must be in [2.30, 3.00] g and the within-set spread must be <= 0.15 g.
- Unknown sphere types are quarantined.
- Mapping validity must begin no later than set assignment; both remain pre-close.
- Draw date must use strict YYYY-MM-DD format.
- Per-contest set assignment, scale ID, measurement resolution, calibration interval, mapping-valid-from, source-document reference/hash and other draw identity fields must be consistent across all 28 rows.
- Added adversarial tests for boundary violations, excessive spread, unknown sphere type, mixed scale/calibration identity, late mapping activation, and malformed dates.

All violations fail closed into existing quarantine labels; no source data is repaired or rewritten.

## Explicit limitations retained

The validator still cannot authenticate a source document from a hash string, prove that the timestamp was independently observed, verify a signature, establish the physical sphere-ID-to-number mapping from primary bytes, or detect an unreported remapping. Those require an original-document manifest, independently witnessed mapping evidence, trusted timestamp/custody, and complete remap/incident records. No physical measurements have been received; no mass-effect model is evaluated.

The official tolerance envelope is a data-quality gate only. It does not imply unequal extraction probabilities.

## Validation

- Isolated ORIGEN workflow [44469124625](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44469124625) on implementation commit `3a291538007c34821ce63c17f1b3f84ef7de5b17`: **success**. All 152 isolated tests passed in 16.886 seconds; all six new physical-intake adversarial tests are present in the log and passed.
- Root CI [44469124280](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44469124280): **success**. `compileall` passed; root suite reported 351 passed, 2 skipped and 16 subtests passed in 33.48 seconds.
- Two existing canonical replays, [44469124306](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44469124306) and [44469441240](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44469441240), completed successfully after being redundantly triggered by the PR-wide path filter on successive PR updates. Both reran the frozen V312 historical integrity computation (6,923 scored historical targets). Neither output was used for the 12382 overlay, candidate selection, or any edge claim. Neither replay was needed for this intake/overlay work.
- To prevent recurrence, `.github/workflows/origen-v03-replay.yml` now retains its narrow `push.paths` and manual `workflow_dispatch` triggers but no longer runs on every PR synchronization. It will run automatically only when the changed push touches the frozen modality/V312 implementation or canonical history.

No statistical edge claim is possible from this engineering patch.
