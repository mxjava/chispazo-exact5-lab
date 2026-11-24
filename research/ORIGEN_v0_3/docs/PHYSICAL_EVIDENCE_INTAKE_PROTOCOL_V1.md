# Physical evidence intake and quarantine protocol

Status: PRE-REGISTERED INTAKE RULES; no physical observations have been received.

## 1. Immutable intake

For every delivery:
1. Preserve the received bytes as a read-only original; never normalize or overwrite the source.
2. Record filename, source/agency, receipt timestamp (America/Mexico_City), delivery channel, byte size and SHA-256.
3. Keep a separate working copy. Any conversion from PDF/image to CSV must retain page references and a human-verification record.
4. Store the request/response folio and any redaction notice beside the source manifest.
5. Never merge a row into the analysis table until its source document and contest linkage have been checked.

## 2. Required row-level identity

A usable observation must identify:
- contest number, date/time and modality (Clásico or De las Tres);
- source document/act and the matching weighing strip;
- sphere-set/case ID and machine ID;
- sphere type;
- stable physical sphere ID and its mapping to printed number 1–28;
- all 28 individual masses, units, measurement precision and measurement timestamp;
- scale ID and calibration evidence;
- any re-weigh, rejection, replacement, remapping or incident.

A row missing the physical-ID-to-number mapping is not usable for a number-level predictive feature. A row missing modality or act linkage is quarantined, not guessed from an odd/even contest pattern alone.

## 3. Source-event chronology vs. target availability

SGVO-PRO-05 Rev. 39 closes sales before the weighing activity for that source draw. Therefore, for a source contest, the physical event sequence is assignment/mapping before close, then sales close, then weighing, strip signature/delivery, and extraction. A source measurement at or after its own close is expected; it is not a pre-close feature for that same contest.

V1 validates only the source contest's structural/event chronology. Its `usable_contests` output must never be interpreted as predictive eligibility. It has no target-contest, evidence-availability, custody-receipt or continuity fields.

For a later target contest, the evidence bytes and independent custody must be verified as available before the target's sales close, and the same sphere set, machine and sphere-to-number mapping must be proven continuous through that target draw. Those checks belong to the V2 source-to-target intake. A timestamp written on a later report is not proof of pre-close availability. If target availability or continuity is unknown, block the target.

Post-draw measurements, winning-number-derived fields and records whose target availability cannot be established are prohibited as pre-draw predictors.

## 4. Measurement and identity checks

- Preserve original units and precision; convert to grams only in a derived field with the conversion recorded.
- Check that each set has exactly 28 distinct physical sphere IDs and exactly one valid mapping to each printed number 1–28 for the relevant draw.
- Check duplicate IDs, missing IDs, duplicate printed numbers, impossible/non-numeric masses, inconsistent units and values outside the procedure's applicable operating envelope.
- Recompute min, max and range from the 28 raw measurements; compare with the signed strip. Do not silently replace the source's reported values.
- Verify calibration validity on measurement date. If unavailable, retain the source but mark metrology status unresolved.
- Treat set changes, remapping, re-weighs and machine maintenance as explicit events with timestamps, not as free-text notes only.

Operating-envelope checks are data-quality checks, not evidence that one sphere is more likely to be drawn.

## 5. Quarantine labels

Use one or more:
- Q_SOURCE_UNVERIFIED: no authenticated source/folio or incomplete document.
- Q_CONTEST_LINK: cannot link strip to exact contest and modality.
- Q_MAPPING: physical sphere to printed number mapping missing/ambiguous.
- Q_TIME: source-event chronology or the official modality-specific sales-close slot is invalid; V2 separately blocks evidence not available before the target close.
- Q_METROLOGY: calibration, units or precision unresolved.
- Q_INCOMPLETE_SET: fewer/more than 28 valid sphere measurements.
- Q_REMAP: mapping changed without complete event chain.
- Q_CONFLICT: source documents disagree.

Quarantined rows remain preserved but do not enter feature construction or scoring.

## 6. Analysis firewall

Before examining any association with winning numbers:
1. Publish a source manifest with hashes and quarantine counts.
2. Freeze the mapping and time-availability decisions.
3. Freeze candidate feature definitions, model, comparison baseline, chronological split, multiplicity family and stopping rule.
4. Separate exploratory historical analysis from untouched prospective evaluation.
5. Use a without-replacement model for five extracted spheres; do not treat the five outcomes as independent Bernoulli draws.
6. Compare prequential log score to the exact uniform 5-of-28 baseline and report calibration, uncertainty and all attempted variants.
7. Keep a separate anytime-valid evidence process; retrospective p-values do not satisfy the prospective evidence gate.

## 7. Decision rule

No number ranking or actionable recommendation may be generated from physical data unless:
- source-event chronology and row-level mapping pass; and V2 independently proves target pre-close availability, custody and physical continuity;
- metrology and chain of custody pass;
- the candidate is frozen before evaluation;
- at least 100 untouched prospective Classic draws are evaluated;
- the preregistered lift is positive, Holm-adjusted p < 0.05, and the Exact5 anytime e-value is at least 20;
- two sealed pre-close outputs and independent custody are documented.

Until then classification is BLOCKED_PROVENANCE or NO_EDGE_EVIDENCE, never EDGE_SUPPORTED.

## 8. Current state

The repository currently contains a header-only physical metadata template and no received primary weighing records. This protocol is therefore prospective intake governance, not a claim that measurements have been obtained or analyzed.
