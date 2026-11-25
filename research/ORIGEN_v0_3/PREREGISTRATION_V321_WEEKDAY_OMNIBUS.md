# V321 — Weekday omnibus preregistration

**Status:** preregistered before execution  
**Input:** V320 Classic atlas only; no new feature selection after inspecting test output.  
**Scope:** historical association, not prediction and not evidence of a physical mechanism.

## Fixed hypothesis and family
Test whether the distribution of any of the ten V320 scalar features differs across the seven ISO weekdays. The fixed family is exactly: `sum`, `range`, `odd_count`, `prime_count`, `consecutive_pairs`, `low_1_9`, `mid_10_18`, `high_19_28`, `low_1_14`, `max_gap`.

## Statistic and null
For each feature calculate one-way between-weekday eta-squared (between-group sum of squares / total sum of squares). The global statistic is the maximum eta-squared across the ten fixed features. Under the null, randomly permute weekday labels while preserving the observed weekday counts. Use PCG64, seed `3212026`, and 1,999 permutations. Use the plus-one Monte Carlo p-value. Feature-wise familywise adjusted p-values compare each observed eta-squared against the permutation distribution of the maximum across all ten features.

## Integrity and interpretation
Sort records by numeric contest before analysis; reject duplicate contests, missing weekdays, non-finite feature values, and any weekday outside ISO 1–7. The input is the V320 Classic atlas, not a reclassified or retuned dataset. A rejection is only historical association and requires a separately preregistered expanding-window prospective log-score test before any predictive claim. A non-rejection closes this weekday hypothesis for this feature family. No changes to V294, main, or canonical history are permitted.
