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
