# Physical sphere intake validator — v1

Status: IMPLEMENTED; NO PRIMARY MEASUREMENTS RECEIVED; NO BIAS RESULT.

## Purpose

`origen.physical_intake` provides a fail-closed structural/provenance gate for incoming weighing records. It does not estimate extraction probabilities, rank printed numbers, or certify source authenticity.

## Canonical intake format

Use one row per physical sphere per contest in:

`data/physical-metadata/PHYSICAL_EVIDENCE_LONG_FORM_TEMPLATE_V1.csv`

A complete contest must have exactly 28 rows, one unique physical sphere ID per row, and a one-to-one mapping onto printed numbers 1–28. Rows carry contest/modality, set and machine identity, physical sphere identity, mass and units, measurement resolution/time, scale calibration interval and certificate hash, mapping-valid-from time, and source document hash/reference.

The legacy wide template `V265_PHYSICAL_METADATA_TEMPLATE_FULL.csv` stores only weights by printed number. It cannot, by itself, establish physical-sphere identity or prove that the mapping was known before sales close. It remains unchanged for compatibility; do not treat it as sufficient for number-level physical inference.

## Validation

```python
from origen.physical_intake import validate_physical_csv

report = validate_physical_csv("data/physical-metadata/received_records.csv")
print(report)
```

The validator:
- requires timezone-aware ISO-8601 timestamps;
- requires assignment, measurement and number-mapping availability strictly before sales close;
- checks that the calibration interval covers the measurement time;
- checks positive finite masses and resolution in grams;
- checks valid SHA-256-shaped document/certificate identifiers;
- checks 28 rows, unique sphere IDs and exact printed-number coverage;
- checks within-contest consistency for modality, date, set, sphere type, machine and source/certificate references;
- emits quarantine labels rather than guessing or silently repairing records.

Quarantine labels follow `PHYSICAL_EVIDENCE_INTAKE_PROTOCOL_V1.md`. A structurally usable contest is not proof that the source, timestamps, signature, scale or calibration certificate is authentic. Independent documentary verification is still mandatory.

## Statistical firewall

Do not use any measurements to rank numbers at this stage. In particular:
- no tolerance envelope is a measured effect;
- no missing mapping may be inferred from printed-number order;
- no post-close record may be treated as pre-close;
- no historical association is prospective evidence;
- no result may alter V294 or the canonical history.

After authentic records arrive, publish a hashed source manifest and quarantine report first. Only then preregister the physical-covariate model, without-replacement likelihood, chronological holdout, multiplicity family and prospective stopping/evidence rules.

## Tests

`tests/test_physical_intake.py` covers complete 28-sphere intake, incomplete sets, post-close measurements, duplicate/missing mappings, duplicate physical IDs, calibration validity, timezone enforcement, conflicting machine identity, invalid mass/unit, source hashes, missing schema and read-only CSV hashing.