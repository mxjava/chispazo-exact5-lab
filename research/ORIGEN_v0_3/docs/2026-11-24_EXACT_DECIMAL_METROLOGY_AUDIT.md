# Exact-decimal physical metrology boundary audit — 2026-11-24

## Defect

The ORIGEN physical sphere intake accepted decimal measurements as strings but converted them to binary IEEE-754 `float` before checking the SGVO-PRO-05 mass envelope and maximum spread. This can round an over-limit decimal onto the permitted boundary.

Concrete Python binary-float behavior:

- `float("5.2500000000000001") == 5.25`
- `float("4.5500000000000001") - float("4.25") == 0.2999999999999998`

The first value is strictly above the 5.25 g upper bound; the second pair has an exact decimal spread strictly greater than 0.30 g. Both can be misclassified by binary-float comparisons.

## Regression coverage

`test_decimal_mass_boundaries_do_not_round_over_limit_values_into_compliance` isolates each boundary from unrelated spread failures by setting the remaining 28-sphere values to a compliant common baseline.

The initial regression fixture was too broad: unrelated baseline values independently triggered the spread quarantine, so the first CI run passed without proving the intended bypass. The fixture was corrected in commit `79fdfad0837bf7b35960568db1cb69c1a783aa2e`; no red CI result is claimed for the inadequate fixture.

## Correction

Commit `13f97f73d469a324f985dd2525a0f1e8729c1ecb` replaces binary-float parsing with bounded `Decimal` parsing for mass and measurement resolution, expresses regulatory limits as exact decimals, and uses a local precision of 40 for spread arithmetic. It rejects values with more than 18 coefficient digits or an exponent magnitude above 9 to keep arithmetic bounded and deterministic.

This corrects numerical classification only. It does not authenticate the source measurements, weighing strip, calibration certificate, instrument identity, signatures, timestamp, or custody chain.

## Disposition

- Research only; PR #30 remains draft and unmerged.
- No changes to `main`, V294, model parameters, thresholds, or canonical history.
- No production eligibility change. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
