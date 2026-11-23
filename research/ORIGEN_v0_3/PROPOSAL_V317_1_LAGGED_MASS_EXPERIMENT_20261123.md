# V317.1 — proposed lagged physical-mass experiment (DRAFT; NOT PREREGISTERED)

Date: 2026-11-23  
Status: **DESIGN PROPOSAL ONLY — BLOCKED PENDING INDEPENDENT REVIEW, PHYSICAL CONTINUITY EVIDENCE AND INDEPENDENT BETA CALIBRATION.**

This document does not amend, replace, or silently reinterpret the frozen V317 preregistration. It proposes a separately versioned experiment because the official procedure audit established that weighing for a Classic draw occurs after that draw's 21:00 sales close.

## 1. Why a new estimand is required

For source contest s, the official weighing strip is produced after source sales close and before source extraction. Its 28 masses therefore cannot predict source contest s. The only potentially defensible predictive use is for a later target contest t, where s < t, if the same physical spheres, number mapping, sphere set and relevant draw mechanism are proven to persist and the source measurements are already independently available before target t closes.

The initial proposal is a **one-contest lag** (t = s + 1 in the official Classic contest sequence). No skipping ahead to a more favorable target is permitted. If any source/target sequence gap, replacement, remapping, machine/feeder change, or custody gap occurs, the target is not eligible under the primary protocol.

## 2. Frozen feature and timing contract

For each target t:
- Source s is the immediately preceding official Classic contest, not De las Tres and not a retrospectively selected contest.
- The source feature is the 28 individual masses measured on the official source-draw weighing strip after source close and before source extraction.
- Sphere IDs are mapped to printed numbers using the source mapping register.
- The full source evidence bundle, original-byte hashes, source signatures, custody receipts and trusted-time proofs must be independently verified and received before target t's 21:00 Mexico City sales close.
- Before target close, there must already be independently verifiable evidence that the exact 28 sphere IDs, their printed-number mapping, the sphere set, machine and feeder geometry assigned for target t are unchanged and scheduled for target use. A caller-supplied declaration or membership in V2's declared-reference sets is not authentication.
- The target's own post-close weighing strip, inspection, draw acta and outcome are never features for predicting target t.

If target assignment/continuity is only documented after target close, that target is **not eligible**. No post-close evidence may retroactively turn a failed pre-close gate into an eligible prediction.

## 3. Handling the target's mandatory post-close weighing

The official procedure requires weighing for every draw. Target t's own post-close weighing is therefore recorded as a **post-prediction process observation**, never as a pre-close predictor.

The primary evaluation must be intention-to-predict over every target that passed the pre-close eligibility gate. A later target weighing, recheck, or discrepancy cannot be used to selectively remove an unfavorable prediction after the result is known. Any post-close discrepancy is reported as a protocol deviation and triggers a predeclared sensitivity analysis; it does not rewrite the primary eligibility decision. If independent reviewers conclude that such post-close events make the target mechanism non-comparable or invalidate the physical continuity assumption, the entire affected regime must be stopped prospectively under a predeclared rule, not selectively filtered by outcome.

## 4. Model and calibration

The model family remains sequential Plackett–Luce sampling without replacement, with exact unordered five-set probability (sum over all 5! orders), and uniform 5-of-28 null. The existing kernel may be reused only after independent numerical review.

Beta must be estimated in an independent physical calibration experiment, not from Chispazo outcomes, on the same sphere material/type and materially equivalent machine/feeder geometry. Freeze signed beta, exact calibration report digest, calibration protocol, uncertainty statement and timestamp before any Chispazo target outcomes are examined. No beta grid, sign search, post-hoc scaling, or target-outcome fitting is allowed. If this calibration cannot be produced, the experiment remains blocked.

The calibration must also justify whether mass alone is an adequate persistent physical covariate across the source-to-target interval. If not, the proposed one-step-lag estimand is not identified and must not be run as written.

## 5. Primary evaluation

- Consecutive eligible target Classic contests under the one-step-lag rule; all quarantines and gaps are logged.
- At least 100 consecutive eligible targets after protocol, beta, code and eligibility policy are independently frozen.
- Two independent pre-close output seals for each target, including source feature vector digest, exact 98,280-set probability vector digest, target ID, code digest, beta/calibration digest and trusted timestamp.
- Primary score: per-target log(q_beta,t(S_t) / q_uniform(S_t)).
- Report every target's eligibility decision, log-lift, cumulative log-likelihood ratio, maximum e-value, anytime-valid p-value, protocol deviations and quarantines.
- No outcome-dependent exclusion, beta refit, stopping, model search, alternate lag, or feature change.
- EDGE_SUPPORTED only if all authentication, calibration, continuity and sealing gates pass, at least 100 consecutive eligible prospective targets are scored, mean log-lift is positive, and max e-value is at least 20 (anytime p <= 0.05).

The e-process claim additionally depends on the conditional uniform-null assumptions and valid pre-close predictability. Independent reviewers must approve those assumptions before scoring.

## 6. Mandatory blockers before implementation or scoring

1. Independent review and signed approval of this temporal estimand before inspecting target outcomes.
2. Authoritative primary source records for actual source-draw sphere weighing, mapping, set assignment and equipment.
3. Trust-rooted signature verification, authorized institutional identities/roles, revocation checks, trusted timestamp verification and independent custody. The current manifest parser is structural only.
4. A pre-close target assignment/continuity record for the exact source sphere IDs, mapping, set, machine and feeder.
5. Independent beta calibration and metrology uncertainty budget.
6. Two independent pre-close sealing services and a tamper-evident audit trail.
7. Adversarial tests and independent security/statistical review of the final evaluator.

V2 currently checks structural temporal ordering and caller-declared reference membership; it explicitly does not authenticate those declarations or prove physical continuity. It is not a substitute for items 2–6.

## 7. Explicit non-claims

- This is not an approved preregistration or a production-ready predictor.
- It does not establish that a sphere-mass effect exists.
- It does not provide a Chispazo number ranking or combination.
- No historical or prospective outcome has been scored under this proposed lagged estimand.
- V294, the canonical historical data, main branch and existing frozen preregistrations remain unchanged.

## References

- Frozen V317: `PREREGISTRATION_V317_PHYSICAL_MASS_PLACKETT_LUCE.md`
- Official timing audit: `docs/V317_OFFICIAL_TIMING_COMPATIBILITY_AUDIT_20261123.md`
- V2 temporal intake: `src/origen/physical_intake_v2.py`
- Official SGVO-PRO-05 Rev. 39: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
