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
