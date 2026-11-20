# V315 — Pair-conditioned next-Classic-draw overlap result

Date: 2026-11-19 (UTC)
Branch: `research/origen-v0.3-engine-20261118`
Implementation commit: `b17b3747282d36c4dd001ebde32fbf5c2e98e914`
Workflow run: [44438922372](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/44438922372)
Artifact: `exact5-v315-pair-transition`, ID `14490830238`
Artifact ZIP SHA256: `f6e040ce8b5bf17e9a64f3ab18eb6ed338042f34aae6b41cf14fb8b76cc0f33f`

## Frozen question and test

For each adjacent pair of Classic draws, enumerate the 10 unordered pairs in the previous draw and classify the next draw's overlap with each pair as 0, 1, or 2. The family contains 378 pairs × 3 overlap categories = 1,134 cells.

The test statistic is the maximum absolute standardized deviation over all 1,134 cells. The Monte Carlo null uses 1,999 complete independent uniform 5-of-28 sequences, NumPy PCG64 seed 3152026, and add-one p-values. Classic only; De las Tres is excluded.

For a fixed prior pair:
- P(next overlap 0) = 0.6693121693121693
- P(next overlap 1) = 0.30423280423280424
- P(next overlap 2) = 0.026455026455026454
- P(a specific pair appears in the previous draw) = 0.026455026455026454

## Reproducible result

- Classic draws: 7,723 (contests 1363–12248)
- Source SHA256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a` — matches the canonical history baseline.
- Simulations: 1,999; seed: 3152026; family size: 1,134.
- Observed maximum |z|: 3.698758155237095
- Null 95th percentile: 4.559373181508406
- Monte Carlo p-value: 0.591

Largest historical cell: previous pair (17, 27), next-draw overlap 2; observed 14, expected 5.4043839758125465, z=3.698758155237095. Chronological block counts were 4, 3, 2, and 5 across four blocks (1,931, 1,931, 1,930, 1,930 transitions).

## Interpretation and disposition

The observed maximum is below the simulated 95th percentile and the family-wise Monte Carlo p-value is 0.591. This experiment does **not** reject the independent-uniform null. The largest cell is a descriptive maximum selected from 1,134 cells, not a validated motif and not a prediction.

Classification: `RESEARCH_ONLY_HISTORICAL_TRANSITION_TEST_NOT_PREDICTIVE_EDGE`.

No predictive advantage is established. No prospective custody, prequential lift, Holm-qualified prospective evidence, or Exact5 anytime e-value is supplied by this experiment. Do not use pair (17, 27), or any cell from this scan, as a betting signal.

## Defect caught before this result

The first V315 CI run failed two tests because expected/variance arrays had length 3 while observed counts had length 1,134. No result was accepted from that run. The implementation was corrected to tile the three category probabilities across all 378 pairs. The corrected isolated V315 workflow and root CI both passed on commit `b17b374...`.

## Integrity

- V294 incumbent remains frozen.
- Canonical history was read-only; its SHA256 matches the established baseline.
- No writes to `main`; work remains on the research branch.
- No promotion or edge claim is authorized.
