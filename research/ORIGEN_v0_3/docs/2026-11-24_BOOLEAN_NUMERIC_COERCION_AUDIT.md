# Boolean-to-number coercion at the Exact5 evaluation boundary

**Date:** 2026-11-24  
**Scope:** ORIGEN v0.3 statistical evaluation input validation. This is a research-only software-integrity correction, not a change to a model or a statistical result.

## Reproducible defect

Python's bool is a subclass of int. The prior evaluate_log_scores converted observation fields with float(...), so p_alt=True became 1.0. The prior Holm validator used isinstance(p, (int, float)), so family_p_values={"primary": False} was accepted as a raw p-value of 0.0.

With 120 paired rows, a caller-declared PREREGISTERED status, all caller-supplied gates set to true, and an e-value at the threshold, that Boolean p-value could force a Holm rejection and produce the state STATISTICAL_SIGNAL_REQUIRES_EXTERNAL_AUDIT. The evaluator still hard-coded edge_certified=False and promotion_authorized=False, but the statistical-candidate label itself could be manufactured by a type-confused input.

## Minimal correction

- Holm input now requires an exact built-in dict, non-empty exact-string hypothesis IDs, exact built-in int/float p-values, and an exact built-in numeric alpha. Booleans and numeric subclasses are rejected.
- The score evaluator requires exact built-in dictionaries for observations and gates, exact text keys, exact built-in numeric probability values, an exact dictionary for the complete p-value family, and exact text for protocol status and primary test ID.
- Probability range checks occur before float conversion, so arbitrarily large integers are rejected without an overflowing conversion.
- No caller-supplied gate is upgraded to an authenticated receipt. The evaluator still cannot return EDGE_SUPPORTED or authorize promotion.

## Adversarial regression coverage

Six new tests cover Boolean p-values (both False and True), non-string hypothesis identifiers, Boolean alternative/null probabilities, the candidate-manufacture path, observation dictionary subclasses, and gate dictionary subclasses.

## Scope and safety

No model weights, selection rules, thresholds, preregistration, V294, canonical history, physical evidence, or production state were changed. This correction prevents type coercion at a statistical-input boundary; it does not establish prospective evidence, provenance, custody, or edge. Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
