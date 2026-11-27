# ORIGEN V1 — Signed evidence completeness requirements

## Defect addressed

A validly signed receipt could previously declare only one artifact and still pass the receipt-signature plus exact-byte-binding composition. Exact byte matching proves that supplied bytes match the receipt's claims; it does not prove that the receipt contains every evidence class required by the deployment.

## V1 contract change

The signed trust-policy envelope now contains a non-empty, unique `required_artifact_types` array. Because this field is part of the canonical policy payload covered by the Ed25519 root signature, callers cannot silently weaken the required evidence set without invalidating that signature.

The composed verifier checks that every required type appears in the signed receipt before returning its byte-match result. Extra receipt artifact types remain allowed; all declared receipt bytes must still be supplied exactly and match their signed SHA-256 and byte-length claims. A missing required type fails closed.

## Example for a Classic physical-evidence deployment

The following names are illustrative policy identifiers, not a statement that the corresponding records have been acquired or authenticated:

- `draw-acta`
- `sphere-measurement-register`
- `sphere-number-mapping-register`
- `machine-and-ball-set-identification`
- `scale-calibration-certificate`

The institution/deployment owner must approve the actual mandatory list and publish it in a root-signed policy envelope. Do not copy this example as an authoritative Lotería Nacional schema.

## Security boundary

This change establishes policy-bound evidence completeness only. It does not verify nested participant signatures, institutional roles, the contents or authenticity of the evidence documents, RFC 3161 tokens, trusted time, ledger inclusion, source acquisition, machine/sphere continuity, or independent custody. The adapter continues to return `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

All tests use synthetic keys and synthetic receipt bytes. No real institutional trust anchor or physical evidence is claimed.
