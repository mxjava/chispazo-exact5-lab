# V321 inference audit — serial dependence limitation

Date: 2026-11-20

## Finding
V321 uses unrestricted permutation of individual weekday labels. This preserves marginal weekday counts but assumes exchangeability. Consecutive lottery outcomes form a time series; serial dependence, slow drift, regime changes, and missing contests can invalidate that reference distribution. The resulting p-values are exploratory and must not be treated as confirmatory weekday evidence.

## Required handling
- Preserve the original V321 preregistration and output unchanged.
- Do not replace the null after seeing the result and call it preregistered.
- A follow-on weekday test must be separately preregistered, use a dependence-aware null, test calibration on synthetic null series with matched serial structure, and predeclare drift, autocorrelation, and missing-contest diagnostics.
- Historical association still requires chronological prospective log-score evaluation and authenticated PRE-CLOSE predictions before any edge claim.

## Decision
V321 is insufficient to establish a weekday signal. This is an inference limitation, not evidence that a weekday effect exists or does not exist. V294, main, and canonical history remain untouched.
