# V266 validation — causal reconstruction target 12250

This validation uses only history through contest 12249 and the causal V264 parent ranking reconstructed before inspecting the target result.

## Integrity / model health

- History rows: 10,887.
- Contest range: 1363..12249, contiguous.
- Rows with contest >= 12250: 0.
- Invalid/out-of-range draw values: 0.
- Full ranking rows: 98,280.
- Unique valid exact combinations: 98,280.
- Live Exact5 specialists: 5/5.
- V263 parent state: `HEALTHY_PARENT_ISLAND_RESCUE_READY`.

## Evidence gate

Despite the engineering health checks passing, production remains blocked:

- V264 state: `RESEARCH_ONLY_NO_EDGE`.
- Holm-approved OOS tests: 0.
- Exact-set anytime e-value: ~0.035714, below the production threshold 20.
- Posterior mass on uniform expert: 1.0 in the historical exact-set test.

Therefore `V266_PREFLIGHT_12250.json` correctly reports `BLOCKED`. This is an evidence failure, not a pipeline-health failure.
