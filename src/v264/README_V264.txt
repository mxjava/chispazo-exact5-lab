CHISPAZO V264 — EVIDENCE FIREWALL + CPU EXACT5 REPAIR
=====================================================

WHY THIS VERSION EXISTS
-----------------------
Target 12250 exposed two separate issues that earlier versions mixed together:
1) The V249 Exact5 XGBRanker trainers returned None whenever CUDA was unavailable,
   even though XGBoost supports CPU ranking. That silently produced five zero Exact5
   specialist columns in CPU/degraded runs.
2) Structural portfolio optimization cannot create predictive Exact5 mass when the
   underlying ranking has no validated out-of-sample edge.

V264 fixes both.

CPU EXACT5 REPAIR
-----------------
The NDCG, pairwise and adversarial XGBRankers now train whenever XGBoost is present.
Device selection is:
    CUDA available -> requested CUDA device
    CUDA unavailable -> CPU
GPU absence no longer means "ranker disabled".

On the causal 12250 reconstruction (history only through 12249), all five Exact5
specialists became live. The realized 12250 winner 02-07-08-10-18, inspected only
AFTER the frozen reconstruction, moved from parent heuristic rank 51,474 to:
    NDCG Exact5       6,096
    Balanced Exact5   5,984
    ADV Exact5       25,990
    Hard Exact5      21,355
    Ultra Exact5     38,640
This is diagnostic, not proof of a gambling edge.

EXACT-SET ANYTIME TEST
----------------------
V264 also adds an exact normalized 5-of-28 probability test. A fixed pool of causal
number experts (frequency windows, EWMA, gaps and transition) is converted into
valid PMFs over all 98,280 exact sets. A Bayesian mixture is scored prequentially
against the exact uniform null 1/98,280.

Historical result through target 12249:
    evaluated targets:      10,087
    posterior uniform:      1.0
    mean log-lift:          negative
    production edge:        NOT PROVEN
No historical result is used before its own prediction.

EVIDENCE FIREWALL
-----------------
Predictive concentration is permitted only if ALL are true:
  * >=2 live Exact5 specialists;
  * >=100 causal OOS targets for the tested ranker/depth;
  * one-sided capture test survives Holm correction at alpha 0.05;
  * exact-set anytime e-value >= 20.
Otherwise the state is RESEARCH_ONLY_NO_EDGE. Structural null hedges may still be
used for coverage, but must not be called predictive lift.

IMPORTANT
---------
This version deliberately refuses to manufacture a claimed 5/5 edge from
post-hoc tuning. A fair 5-of-28 draw gives each exact line probability 1/98,280.
The goal is to detect a reproducible departure from that null, not to rename
coverage as prediction.
