CHISPAZO V263 — INTEGRITY + ISLAND RESCUE + NULL-HEDGE

WHY V263 EXISTS
---------------
Target 12250 exposed a production-contract failure: all five Exact5 LTR columns
were constant zero, yet the pipeline continued and produced a portfolio. V263
makes that impossible.

MODES
-----
PASS / HEALTHY_PARENT_ISLAND_RESCUE_READY
  At least 2 Exact5 specialists are live. V263 creates an expanded eligibility
  pool from parent head, each live Exact5 head, support heads, and specialist
  disagreement frontier. The probability objective remains V262/DRO; the island
  pool only prevents head truncation.

HARD_FAIL_EXACT5
  Fewer than 2 Exact5 specialists are live. Normal production must stop.

DEGRADED_NULL_HEDGE (explicit opt-in only)
  Emits 30 structurally balanced lines with 5-6 exposures per number and pair
  repetition minimized. This is NOT a prediction. Under the uniform lottery null
  its Exact5 probability is exactly 30/98,280, same as any 30 distinct lines.

USAGE
-----
Health gate only (recommended production behavior):
  python CHISPAZO_V263_INTEGRITY_ISLAND_DRO.py --ranking FULL_RANKING.csv --target 12251 --out-dir resultados_v263_12251

Explicit degraded hedge for research/coverage only:
  python CHISPAZO_V263_INTEGRITY_ISLAND_DRO.py --ranking FULL_RANKING.csv --target 12251 --out-dir resultados_v263_12251 --allow-degraded-hedge

The engine never reads the current/future result.

PRODUCTION WRAPPER
------------------
CHISPAZO_V263_PRODUCTION_GATE.py runs the integrity gate before V262. When the
parent passes, it monkey-patches V262 candidate eligibility with the V263 island
pool while leaving V262's calibrated probability/DRO objective unchanged.

Example:
  python CHISPAZO_V263_PRODUCTION_GATE.py --ranking FULL_RANKING.csv --target 12251 --history Chispazo.csv --expected-last 12250 --v262-config chispazo_v262.toml --audit-out-dir resultados_v263_12251

A dead Exact5 parent exits with code 4 and produces no normal prediction.
