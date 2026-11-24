# ORIGEN prospective evaluation threshold subclass audit — 2026-11-24

## Finding

The prior evaluator rejected booleans for the observation minimum and anytime e-value, but used isinstance for both. Python permits subclasses of int and float to override comparison operators. A caller-controlled subclass could therefore make an invalid threshold pass the gate.

Two concrete reproductions were confirmed against the previous implementation:

1. SpoofedMinimum(0), an int subclass whose __lt__ always returns false, bypassed the min_observations < 1 guard. With one positive-lift row, all caller-declared gates true, a rejecting Holm result, and a valid e-value, the evaluator could label a one-observation sample STATISTICAL_SIGNAL_REQUIRES_EXTERNAL_AUDIT.
2. SpoofedEValue(0.0), a float subclass whose __ge__ always returns true, passed the e-value threshold comparison despite its underlying value being zero. math.isfinite accepted the underlying finite float value.

These are Python type-boundary defects, not statistical evidence. The evaluator still never returns EDGE_SUPPORTED.

## Correction

Commit cc50f4b7f56ea1b4777028663f98949a412913c1 changes the minimum-observation guard to require type(value) is int. The e-value threshold now accepts only exact built-in int or float values before finiteness and threshold checks.

Commit 605bfaa04e419e0974754d2073770efb39d86d6d adds two adversarial regressions:
- comparison-overriding integer subclass cannot lower the minimum observation count;
- comparison-overriding float subclass cannot manufacture an anytime e-value threshold crossing.

The tests assert the first input raises a validation error and the second remains NO_EDGE_EVIDENCE with the e-value gate failed.

## Scope and limitations

This hardening does not authenticate caller-declared protocol status, gates, preregistration, e-values, PMFs, or custody. It prevents subclass operator dispatch from bypassing local type/range gates only. The independent provenance adapter remains fail-closed. No model parameters, V294, historical data, or production eligibility were changed.

## Required verification

Exact-head CI must pass on the resulting PR #26 head. A successful test suite establishes software behavior only; it does not establish a prospective edge or physical evidence provenance.
