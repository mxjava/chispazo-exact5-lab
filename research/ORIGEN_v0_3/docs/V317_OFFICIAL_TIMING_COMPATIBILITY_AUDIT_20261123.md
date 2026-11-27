# V317 official timing compatibility audit — 23-Nov-2026

Status: **BLOCKED_SPECIFICATION_TIMING_CONFLICT**. No outcome analysis, beta search, model retuning, or production use is authorized by this audit.

## Finding

V317 preregistration currently describes the candidate as using authenticated “pre-close masses ... for contest t” and requires measurement/mapping/set-assignment times strictly before sales close. The official electronic-draw procedure does not place the weighing for a draw before that draw's sales close.

SGVO-PRO-05 revision 39 establishes:
- Policy 9: automatic sales close at 21:00 for nocturnal draws; the official Chispazo product page maps the 21:00 slot to Clásico.
- In the activity flow, activity 4.1 verifies the SICAL sales state as “Cerrado” and prints the Sumario de Sorteo. The next section is explicitly “Pesaje y Colocación de las Esferas”; activity 5.1 starts weighing in the presence of the SEGOB inspector and Lotería representatives; 5.2 checks the individual sphere weights; 5.4 signs the weighing strip; 5.5 delivers it for attachment to the Acta; 5.6 loads the spheres into the machine feeders.
- Policy 6 requires weighing for every electronic draw.

This establishes a direct timing conflict for a same-draw predictor: the mass vector measured for Classic contest t is obtained after sales close for t, so it cannot be an input sealed before that same close. The official process does not support treating the target contest's own post-close weighing as pre-close data.

## What V2 already gets right

The V2 temporal contract separates source contest from target contest. It allows source-draw weighing after the source close and before source extraction, then requires the evidence bytes/custody to be available before the later target close and requires continuity of sphere set, machine and sphere-to-number mapping through the target draw.

That temporal design is consistent with the official activity sequence. It is a possible route to a later-target experiment only if the exact physical set and mapping are proven to persist into the target draw. SGVO-PRO-05 also requires weighing each draw, so a prior draw's mass vector cannot simply be carried forward on assumption; any subsequent reweigh, case change, sphere replacement, remapping or equipment change must be captured and resolved before the target feature is eligible.

## Consequence for V317 as currently written

The current V317 text says (m_{it}) is the mass mapped to number i “in contest t” and calls (q_{\beta,t}) a distribution computed from authenticated pre-close masses and mappings for contest t. Those statements are not operationally satisfied by the official same-draw weighing sequence.

Do not silently reinterpret (m_{it}), relabel a post-close strip as pre-close, or use a prior contest's mass as if it were measured for the target. That would change the feature timestamp and source-target relationship of the preregistered experiment.

## Required safe resolution before any V317 outcome scoring

A separately versioned, pre-outcome preregistration addendum and independent review must choose and freeze one explicit estimand:

1. **Same-draw mass description only:** use each draw's official strip for descriptive/forensic analysis, but do not claim it was available for predicting that draw. It cannot enter that draw's pre-close e-process.
2. **Lagged source-to-target experiment:** define the source contest and target contest explicitly; use only the source draw's post-close/pre-extraction measured masses; prove exact sphere IDs, sphere-to-number mapping, sphere set and machine continuity through target close and target draw; incorporate any new target-draw weigh/inspection/replacement record; require all source bytes, signatures, custody and trusted-time proofs to be independently available before target sales close; and freeze the exact rule for what happens on any reweigh or change. This is a temporal redesign of the registered feature, not a harmless implementation detail, so it must be approved and preregistered before outcomes are inspected.
3. **Independent pre-close measurement:** only if Lotería Nacional supplies a documented authorized process that genuinely makes the target sphere measurements and mapping available before target sales close, with original records and trusted timestamps. Do not assume such a process exists; the reviewed procedure's standard activity flow currently says otherwise.

In every case beta must still come from an independent physical calibration on materially equivalent equipment, frozen before Chispazo outcomes are examined. The required prospective sample, multiplicity controls, anytime e-value, independent seals, clean hashes and authentic custody remain unchanged.

## Current decision

- V317 empirical status: **BLOCKED**; no beta supplied; no physical primary records supplied; no outcome scoring performed.
- ORIGEN V2: structural temporal gate only; not an authenticated trust verifier.
- Production: **BLOCKED / RESEARCH_ONLY_NO_EDGE**.
- V294 and canonical history: unchanged.
- No main write, merge, promotion, canonical append, or model parameter change.

## Official references

- SGVO-PRO-05 Rev. 39, especially policy 6 and 9 and activity flow pages 11–13: https://www.loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf
- Official Chispazo schedule (De las Tres 15:00; Clásico 21:00): https://www.loterianacional.gob.mx/Chispazo/Chispazo
- ORIGEN temporal contract V2: `docs/PHYSICAL_EVIDENCE_TEMPORAL_CONTRACT_V2_20261119.md`
- V317 preregistration as currently frozen: `PREREGISTRATION_V317_PHYSICAL_MASS_PLACKETT_LUCE.md`
