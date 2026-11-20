# V323 — Context-conditioned hierarchical partition-and-divide

Status: preregistered fixed diagnostic; no result until CI artifact is produced.

## Hypothesis

A static combinatorial partition may behave differently under distinct recent-draw regimes. V323 conditions the fixed V322 model on a coarse regime derived exclusively from the preceding 20 Classic draws. The test asks whether conditioning improves chronological predictive log score versus the exact uniform 5-of-28 baseline.

## Fixed context definition

For a target draw, use only the immediately preceding 20 structurally assigned Classic draws. Compute the mean number of shared values between each adjacent pair among those 20 draws (19 overlaps).

- LOW_REPEAT: mean overlap < 0.75.
- TYPICAL_REPEAT: 0.75 <= mean overlap <= 1.05.
- HIGH_REPEAT: mean overlap > 1.05.

Thresholds are fixed before execution and are not estimated or tuned on the target outcomes.

## Model

- Three independent copies of the frozen V322 hierarchical partition model.
- Same fixed three partition trees, alpha=200, uniform base measure, and 98,280 outcome universe.
- Each historical Classic target is assigned to exactly one regime using its own preceding-20 context, then updates only that regime's model.
- For every scored target, compute regime from preceding-20 draws, score the target with that regime model, and only then update it.
- The first 800 Classic draws are warmup. During warmup, regime-specific models are primed from targets whose complete preceding-20 context exists.
- If a regime has no prior observations, use exact uniform PMF for that target.

## Evaluation and reporting

Report overall and per-regime mean/cumulative log-lift, positive fraction, exact rank-1 count, tie-aware expected top 1/5/10/30/100 inclusions, source hash, per-target score file hash, and regime sample sizes. Compare overall top-K inclusions with n*K/98,280. The primary criterion is overall mean prequential log-lift; per-regime results are exploratory and require multiplicity correction.

## Stop and interpretation rules

- No threshold search, model weight search, feature changes, or regime redefinition after seeing results.
- A positive subgroup alone is not evidence of a repeatable edge.
- A retrospective prequential replay is not an authenticated pre-close prediction.
- Any positive result must be frozen and tested on at least 100 untouched consecutive Classic draws with two independently sealed pre-close outputs before any EDGE_SUPPORTED classification.
- A non-positive overall mean log-lift closes V323 as NO_EDGE_EVIDENCE; do not retune against the same history.

## Non-interference

V294 remains frozen. Canonical history is read-only. No writes to main, no merge, no promotion. V323 is isolated research only.
