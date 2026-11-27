# V317.1 audit finding — sphere-to-number mapping is not bound to a primary artifact

**Date:** 2026-11-27  
**Classification:** BLOCKER — structural provenance gap  
**Scope:** research-only audit of ORIGEN V2 temporal intake at PR #13 HEAD `6d4d57d5083384f30a8487ba48d8f9f6dde88b5a`  
**Disposition:** no predictor activation, no canonical-history change, no V294 change.

## Finding

The V2 intake schema requires `mapping_valid_from` and `mapping_valid_to`, and the evaluator checks that the declared interval covers the assignment and target draw. It also checks that the 28 rows contain 28 distinct sphere IDs and the printed numbers 1 through 28.

However, the V2 row contract has no dedicated mapping-register artifact reference or digest. The required provenance fields `source_document_ref` and `source_document_sha256` are grouped as one source document across the 28 sphere rows; the code does not establish that this document is the authoritative sphere-to-number mapping register, nor does it bind the per-sphere pairs to a separately identified mapping artifact.

Consequently, a structurally valid 28-row mapping can pass the mapping-window and bijection checks without V2 proving which primary mapping record supplied the pairs. The caller-supplied `declared_source_refs` membership check only establishes membership of the generic source reference; it does not add a mapping-specific binding.

## Why this blocks V317.1

V317.1 uses the mass vector indexed by printed number. If sphere identity-to-number assignment is missing, substituted, or changed between source weighing and target assignment, the model can associate a measured mass with the wrong number. A valid 28-element vector and valid mass range/spread do not repair that identity failure.

This is not evidence that a mapping was actually altered. It is a gap in what the current intake contract proves.

## Required remediation before eligibility

1. Add explicit mapping-register artifact identity to the V2 contract: immutable source-object reference and original-byte SHA-256, separate from the weighing-strip artifact.
2. Bind every `sphere_id -> printed_number` pair to that mapping artifact and require exactly 28 unique sphere IDs and exactly the number set 1..28.
3. Require the mapping artifact to be covered by the physical-evidence manifest, original-byte hashing, authorized signature/role verification where applicable, trusted time and independent custody.
4. Require mapping validity and assignment evidence to establish that the same mapping was effective for the target before its 21:00 sales close.
5. Add adversarial tests: mapping artifact missing; digest malformed; mapping reference changed across rows; one sphere remapped; two spheres assigned the same number; mapping artifact not in independently verified references; post-close mapping evidence.
6. Keep the evaluator fail-closed. Do not infer mapping provenance from row consistency, a URL, a caller-provided set, or a digest string.

## Acceptance boundary

A structural parser may validate field shape and row-to-artifact references. It must continue to report that it does not authenticate bytes, signatures, issuer identity, revocation, trusted timestamps, custody or institutional authority. Those checks belong to the independently provisioned verifier. No parser result alone may become `AUTHENTICATED`, `EDGE_SUPPORTED`, or production-eligible.

## Evidence inspected

- `research/ORIGEN_v0_3/src/origen/physical_intake_v2.py`: V2 required columns, mapping-window checks, 28-sphere bijection checks, and caller-declared reference membership.
- `research/ORIGEN_v0_3/docs/PHYSICAL_ARTIFACT_MANIFEST_V1_CONTRACT_20261123.md`: separately identifies `SPHERE-NUMBER-MAPPING-REGISTER` as a required artifact and explicitly limits the parser to structural validation.
- `research/ORIGEN_v0_3/PROPOSAL_V317_1_LAGGED_MASS_EXPERIMENT_20261123.md`: requires source sphere IDs and printed-number mapping to remain unchanged through the target assignment.

This audit note records a contract gap only. No official draw-specific mapping register was obtained in this review.
