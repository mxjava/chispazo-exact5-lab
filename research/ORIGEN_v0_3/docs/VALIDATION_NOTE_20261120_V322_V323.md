# V322/V323 validation hardening — 2026-11-20

This note records source and test corrections on the isolated ORIGEN research branch.

## V322
- Reject Python booleans in alpha and five-number draw inputs. Python treats bool as a subclass of int, so True could otherwise pass integer and 1..28 checks.
- Regression coverage includes alpha, candidate feature extraction, training update, and target scoring.

## V323
- Use the conventional statistical median for even-sized score samples.
- Validate all 20 prior context draws as five distinct integer values in [1, 28], rejecting booleans, duplicates, out-of-range values, malformed rows, and non-sequences.
- Context remains strictly prior-only; no target values enter regime assignment.

## Integrity and interpretation
- No changes to V294, main, or the canonical historical CSV.
- No predictive claim is made. These are code-integrity fixes only.
- CI for this exact head must pass before these changes are treated as validated.
- Retrospective prequential scores remain research diagnostics, not authenticated pre-close evidence.
