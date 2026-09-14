# Prospective Exact5 protocol

For each target `T`:

1. Verify the official target contest and sales cutoff.
2. Verify the most recent completed result from an external source.
3. Append it to history only if its contest is exactly the current max + 1.
4. Run the parent model using history ending at `T-1`.
5. Run V266 preflight. Any critical FAIL blocks predictive production.
6. Run V264 evidence firewall. Predictive concentration is forbidden unless OOS tests and exact-set evidence pass.
7. If production is allowed, freeze exactly 30 distinct lines with `freeze_prediction.py` before sales cutoff.
8. Do not modify a frozen registration.
9. After the draw, evaluate the frozen registration. Never use the realized result to alter the original record.

## Current scientific state

The engineering pipeline is operational, but the historical signal family tested so far has not demonstrated a reproducible Exact5 predictive edge over the uniform null. Coverage/null-hedge outputs must be labelled as such.
