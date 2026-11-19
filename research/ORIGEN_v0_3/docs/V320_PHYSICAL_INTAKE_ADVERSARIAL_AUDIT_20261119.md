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

## Validation status

The isolated ORIGEN workflow must execute the new adversarial tests before this change is considered green. No statistical edge claim is possible from this engineering patch.
