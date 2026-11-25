# Exact5 validation closeout — 2026-11-21

## Scope and safeguards

- Repository: `mxjava/chispazo-exact5-lab`
- PR: #10, branch `fix/origen-v03-integrity-guards-20261120`
- Tested head: `6f87b92a65c453db5e03800e604f34d1af06d859`
- This is a retrospective/prequential diagnostic over the frozen canonical history ending at contest 12249.
- Canonical history SHA-256 supplied to all replay jobs: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- 10,887 source rows; 7,723 structurally assigned Classic draws; 800 warmup; 6,923 scored targets.
- Structural modality assignment is not independent official row-level verification.
- V294 remains frozen; canonical history was not modified; no writes to `main`; no challenger promotion.

## CI and isolated validation

All listed runs completed successfully on the tested head:

| Workflow | Run | Result |
|---|---:|---|
| General CI | [44849808563](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849808563) | 482 passed, 2 skipped, 28 subtests passed |
| ORIGEN v0.3 isolated | [44849808473](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849808473) | 271 tests passed |
| V322 | [44849808478](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849808478) | success |
| V323 | [44849808471](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849808471) | success |
| V324 | [44849802918](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849802918) | success |
| V325 | [44849802884](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849802884) | success |
| V326 | [44849802882](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44849802882) | success |

## Prequential model diagnostics

V322 and V323 each scored the same 6,923 targets chronologically, before incorporating each target into model state.

| Model | Mean log-lift | Median log-lift | Cumulative log-lift | Positive fraction | Classification |
|---|---:|---:|---:|---:|---|
| V322 hierarchical partition | -0.00542775 | -0.00478811 | -37.57633 | 47.52% | NO_EDGE |
| V323 context partition | -0.00533134 | -0.00437849 | -36.90890 | 47.93% | NO_EDGE |

V323 is marginally less negative than V322, but both have negative mean and cumulative log-lift. This is not evidence of predictive advantage.

## Rolling-memory ablation (V324)

All variants scored the same 6,923 targets. Mean log-lift remained negative:

| Classic-memory window | Mean log-lift | Cumulative log-lift |
|---:|---:|---:|
| 400 | -0.00632972 | -43.82066 |
| 800 | -0.00700442 | -48.49159 |
| 1,600 | -0.00706516 | -48.91211 |

No rolling-memory setting demonstrates an edge. These exploratory horizons are not a basis for promoting a winner.

## Portfolio audit (V325)

The expanding-history portfolio recorded 3 exact 5/5 hit lines across 6,923 targets, versus a uniform expectation of approximately 2.113. Its 4/5 count was 242 versus an expectation of approximately 243.024. Rolling windows of 400, 800 and 1,600 recorded 0, 1 and 3 exact 5/5 hit lines respectively. These are retrospective portfolio reconstructions, not pre-close forecasts. The observed 3/5 and 4/5 counts are not evidence of a statistically established advantage.

## Diversified portfolio audit (V326)

The expanding-history portfolio recorded 4 exact 5/5 hit lines across 6,923 targets versus a uniform expectation of approximately 2.113; the null probability of at least four under the stated uniform reference is approximately 0.164. Its 4/5 count was 235 versus an expectation of approximately 243.024. Rolling windows of 400, 800 and 1,600 recorded 1, 1 and 3 exact 5/5 hit lines respectively. The expanding 4/5 count was 235 versus 243.024 expected. The 4/5 and 3/5 aggregate counts did not exceed their corresponding uniform reference expectations in a way that establishes an edge.

V326 remains exploratory. Do not select its seed, objective, candidate pool size or horizon on this same historical sample. It is not confirmatory evidence.

## Custody verifier hardening

Subsequent to the tested head above, the branch received further changes:
- Recompute SHA-256 and byte length from the exact payload file.
- Bind receipt to manifest contest, modality, candidate, source commit and digest.
- Require separately configured custodian identity, distinct from originator.
- Require receipt time not before manifest generation and before scheduled close.
- Require Cosign verification and exactly one Rekor integrated timestamp from the verified bundle; the timestamp must be before close and not materially predate the signed receipt claim.
- Corrected the originator workflow so it signs, verifies and archives the same file name, `originator-attestation.bundle.json`.
- Added adversarial tests for tampering, duplicate JSON keys, identity collision, pre-close ordering and missing Rekor timestamp.

The verifier hardening and adversarial tests were subsequently included in a fresh successful CI run at commit `8e7581083e7e0651e2492bbf2a08ec553b61abfd`: [CI run 44850774102](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44850774102), **485 passed, 2 skipped, 28 subtests passed**. ORIGEN isolated validation also passed at that commit: [run 44850774097](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44850774097), **271 tests passed**. The later commits `35ab84b` and `0ad5df0` only update documentation/reporting; no verifier code changed after the tested commit.

## Certification decision

**NOT CERTIFIED — EXTERNAL CUSTODIAN AND PHYSICAL EVIDENCE REQUIRED.**

The repository cannot certify itself as an independent custodian. A real external custodian must receive the exact payload before official close, recompute its digest, sign a receipt using a separately trusted identity, place the receipt in a verified transparency log before close, retain the payload in separately controlled immutable storage, and complete independent retrieval. Two witnessed dry-runs and negative tests remain mandatory.

Physical evidence certification separately requires original official draw records and chain of custody. Predictive-edge certification separately requires preregistered untouched prospective targets and the stated statistical gates. No external receipt, witnessed dry-run, original physical evidence package or prospective edge evidence was present in this audit.

**Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.** No `CUSTODY_ACCEPTED`, `SEALED`, `PHYSICAL_EVIDENCE_VERIFIED` or `EDGE_SUPPORTED` claim is made.
