# Physical-bias research lead — Chispazo Clásico (2026-11-19)

Status: DOCUMENTED DATA-ACQUISITION LEAD; NO PREDICTIVE EDGE ESTABLISHED.

## Why this lead is materially different

The public Lotería Nacional procedure `SGVO-PRO-05 — Procedimiento Sorteos Electrónicos` is marked public, revision 39, publication date 20 March 2026. Its policy 6 says sphere weighing is performed for every draw and defines two allowed sphere types:

- Smartballs: 4.25–5.25 g; maximum difference between lightest and heaviest sphere 0.30 g.
- Ping-pong: 2.30–3.00 g; maximum difference 0.15 g.

The procedure states that if the limits are not met, another sphere case is selected and weighed again. The activities section says the signed weighing strip (`tira de pesaje`) is reviewed/rubricated by the Operations representative, SEGOB inspector and General Directorate representative, then attached to the corresponding draw record/act. It also says spheres are placed progressively in machine feeders.

Official source:
https://loterianacional.gob.mx/Documentos/NormatecaInterna/2014/SUSTANTIVAS/VIGENTES/sgvo_pro_05.pdf

Relevant source locations in the PDF:
- Policy 6 and weight limits: printed pages 5–6 (PDF text lines 204–209).
- Weighing strip signatures and attachment to the act: printed page 14 (PDF text lines 603–619).

The current official Chispazo page says Clásico is held at 21:00 and uses a machine to select five numbers from 1–28:
https://loterianacional.gob.mx/Chispazo/Chispazo

## What this does and does not imply

A tolerance envelope is not a measured bias. The allowed maximum spread does not tell us the actual mass of each numbered sphere, which sphere set was used for a given draw, whether number-to-sphere assignments changed, or whether any measurable mass difference affects extraction probability in this specific machine. Do not infer a hot/cold number from historical frequencies or from the tolerance limits.

This lead becomes testable only with contemporaneous records and a documented number-to-sphere mapping. Any weight effect must be estimated without looking at the corresponding winning draw, then validated prospectively.

## Required primary records to request

For each Chispazo Clásico contest in a defined date range (preferably all contests for which records are retained):

1. The signed `tira de pesaje` for each draw, including the individual mass of all 28 spheres, units, precision, scale identifier, calibration status and timestamp.
2. The draw act to which that strip was attached, with contest number/date and confirmation that the strip corresponds to that Clásico draw (not De las Tres).
3. Sphere-case/set ID, sphere type (Smartballs or ping-pong), machine ID/model, feeder position and the mapping from physical sphere ID to printed number 1–28.
4. Any sphere/case replacement, re-weighing, rejected measurement, maintenance, incident, or number-to-sphere remapping.
5. The applicable weighing form/specification and scale calibration records for the requested period.
6. Where available, video or official record that establishes the physical mapping and loading order, with timestamps.

Request machine-readable copies where available (CSV/XLSX); otherwise legible PDF scans. Ask the agency to identify records not held, retention periods and any legal basis for withholding/redaction. Do not ask for or publish personal data of staff; signatures may be redacted while retaining role, timestamp and verification evidence.

## Analysis plan once records arrive

1. Verify chain of custody, timestamps, contest/modality labels, scale calibration and sphere-number mapping.
2. Reject or quarantine incomplete, post-draw, ambiguous, or remapped records.
3. Freeze all features before each draw close. Candidate feature: measured sphere mass and validated machine/set covariates only; no winner-derived features.
4. Test whether mass predicts extraction after controlling for set, machine, date/regime and selection process. Respect the without-replacement nature of five extracted spheres.
5. Compare against uniform 5-of-28 and predeclared baselines using chronological prequential log scores, multiplicity correction, calibration and a separate anytime-valid Exact5 e-process.
6. Require at least 100 untouched prospective Classic draws, two sealed pre-close outputs and independent custody before any edge claim.

## Current repo/data state

- `data/physical-metadata/V265_PHYSICAL_METADATA_TEMPLATE_FULL.csv` currently contains headers only; no measurements.
- `data/prospective-ledger/README.md` defines the required sealed-output fields; there are no populated prospective entries in the current branch tree.
- Canonical history remains byte-for-byte unchanged; no writes to `main`; V294 remains frozen.
- Classification: `BLOCKED_PROVENANCE` for physical-bias testing; `NO_EDGE_EVIDENCE` overall.

## Decision

This is the strongest currently documented non-historical lead because the public procedure confirms that individual weighing records exist operationally and are attached to draw acts. It is not yet a signal and produces no defensible preferred numbers. The next scientific bottleneck is obtaining the signed per-draw weighing strips and the physical-number mapping.
