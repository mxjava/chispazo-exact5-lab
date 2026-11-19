# V317 — preregistration: physical-mass Plackett–Luce test

Status: MODEL KERNEL IMPLEMENTED; EMPIRICAL TEST BLOCKED PENDING AUTHENTIC PHYSICAL RECORDS AND INDEPENDENT BETA CALIBRATION.

## 1. Question and scope

Does the measured mass of each physical sphere, linked to its printed number before sales close, improve the probability assigned to the unordered five-number Classic outcome under a specified sequential weighted-without-replacement mechanism?

This tests one mechanistic hypothesis only. A negative result does not exclude other physical effects; a positive historical association is not prospective evidence.

## 2. Fixed model

For contest t, let m_it be the verified mass in grams of the sphere mapped to printed number i, and let z_it be its z-score across the 28 spheres in that contest using population standard deviation. Set log weight a_it = beta * z_it and weight w_it = exp(a_it).

beta is a signed slope per one within-set standard deviation. It MUST be obtained from an independent, documented physical calibration experiment using the relevant sphere type and materially equivalent machine/feeder geometry. The calibration experiment must not use Chispazo winning outcomes. Freeze beta as an exact numeric value, calibration report hash, protocol, and timestamp before any Chispazo outcome labels are inspected. If a defensible external beta is unavailable, V317 remains BLOCKED and no beta grid/search is permitted.

The draw mechanism is sequential Plackett–Luce without replacement: at each extraction, a remaining sphere i is selected with probability proportional to w_it among remaining spheres. Because the published result is an unordered set S of five printed numbers, the model probability is the sum of the sequential probabilities over all 5! possible extraction orders.

The exact unordered-set log probability is computed by the recurrence P(empty)=1 and P(S)=sum over i in S of P(S without i) * w_i / (sum of w_j over j not in S without i). The implementation evaluates this recurrence in log space. It is not permissible to replace the unordered set probability with the probability of one arbitrary order.

## 3. Primary score and null

Uniform null: q0(S)=1/C(28,5) for every five-number set.

Candidate: q_beta,t(S), the normalized unordered Plackett–Luce probability computed solely from authenticated pre-close masses and mappings for contest t.

Per-contest log-lift: ell_t=log(q_beta,t(S_t)/q0(S_t)).

Prequential likelihood-ratio process: E_0=1 and E_t=E_(t-1)*exp(ell_t). Since beta and all features are frozen/known before close, and q_beta,t is a normalized conditional distribution over all 98,280 five-number sets, E_t is a nonnegative likelihood-ratio martingale under the conditional uniform null, subject to the stated draw-independence/null assumptions.

Anytime-valid p-value: p_anytime=min(1, 1/max_{s<=t} E_s), by Ville's inequality. There is one primary model and one primary hypothesis; multiplicity family size is one. No additional beta signs, magnitudes, feature families, draw windows, or alternate mechanisms may be searched against the same evaluation stream.

## 4. Data eligibility and provenance gates

Each contest must pass `PHYSICAL_EVIDENCE_INTAKE_PROTOCOL_V1.md` and `origen.physical_intake` with no quarantine labels. Required evidence includes all 28 individual masses; stable physical sphere IDs; exact sphere-ID ↔ printed-number mapping; set and machine identity; scale and in-date calibration certificate; source act/tira linkage; and authenticated measurement, mapping and set-assignment times strictly before sales close.

Original source files are immutable and hashed. An independent custodian verifies document linkage and timestamps. A structural validator PASS does not authenticate the records. Any remapping, set/machine change, reweigh, rejection, calibration gap, missing sphere or ambiguous time causes the affected contest to be excluded before outcome analysis and reported in the quarantine ledger.

No winning number, post-close field, later correction, or future contest may enter the feature construction for contest t. The mass vector is ordered by printed number only after the physical-ID mapping is independently verified.

## 5. Evaluation design

- Prospective primary evaluation: at least 100 consecutive eligible untouched Classic contests after beta and the analysis code are frozen.
- Two independent pre-close portfolio/model-output seals are required before the first scored prospective contest; the physical mass vector and resulting q_beta distribution must also be hashed and timestamped before close.
- No outcome-dependent tuning, stopping, exclusion, beta refit, mapping repair, or feature engineering.
- Report every eligible and quarantined contest, every per-draw ell_t, E_t, max E_t, p_anytime, cumulative log-lift, mean log-lift, and calibration diagnostics.
- Keep a chronological untouched holdout; any exploratory historical period is reported separately and cannot count toward the 100 prospective contests.

## 6. Decision rule

V317 may be classified EDGE_SUPPORTED only if all provenance/custody gates pass, at least 100 prospective eligible Classic contests are scored, mean log-lift is positive, max E_t is at least 20 (equivalently p_anytime at most 0.05), and no integrity or calibration failure is found. Otherwise classify NO_EDGE_EVIDENCE or BLOCKED_PROVENANCE as appropriate.

Even a successful result supports only the frozen mass-weighted mechanism in the validated equipment/regime. It does not prove universal bias or justify extrapolation across sphere types, sets, machines, or mapping regimes without separate validation.

## 7. Implementation verification

`origen.plackett_luce` provides:
- standardized mass-to-log-weight conversion with signed externally frozen beta;
- exact unordered-set Plackett–Luce log probability via a subset recurrence;
- per-contest log-likelihood ratio against uniform 5-of-28;
- enumeration of all 98,280 sets for normalization audits.

Tests compare the recurrence against explicit enumeration of all 120 orders for a selected set, check that all 98,280 set probabilities sum to one, verify beta=0 recovers exact uniform 5-of-28, and reject malformed inputs.

## 8. Explicit non-claims

No primary physical measurements have been received. No independent beta calibration has been supplied. V317 has not evaluated Chispazo outcomes and produces no number ranking or recommendation. The kernel's correctness is an implementation property, not evidence that the physical mechanism exists.