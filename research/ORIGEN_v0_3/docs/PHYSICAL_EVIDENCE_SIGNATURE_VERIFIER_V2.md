# ORIGEN physical-evidence signatures with V2 CLASSIC policy-domain binding

Status: RESEARCH ONLY / SYNTHETIC FIXTURES / NOT AUTHENTICATED

## Scope

This increment reuses the strict physical-manifest parser and nested Ed25519
signature verifier in the V2 policy line. The verifier accepts only a canonical
V2 signed policy envelope and binds it to
`origen.chispazo.classic.provenance`. The manifest parser independently
requires modality `CLASSIC` and the official 21:00 America/Mexico_City close.

## Change

- Original artifact bytes are re-hashed and length-checked.
- Detached signature bytes are re-hashed and verified against the exact
  canonical manifest claim payload.
- The signed policy is verified using the V2 envelope parser, caller-supplied
  root pin, key ID, sequence floor, expected domain and clock.
- Even if a caller supplies a valid signed De las Tres domain and matching
  expected-domain argument, the CLASSIC manifest boundary rejects it.
- The result exposes the verified policy domain.
- Role claims remain unverified; the V2 policy still does not authorize roles.
- RFC 3161, ledger inclusion, custody receipt signatures, external identity,
  root provisioning and anti-rollback persistence remain unverified.
- The result remains `BLOCKED_PROVENANCE`.

## Synthetic test boundary

All signing keys and evidence bytes in tests are generated in-process. They
are not institutional keys, official source records, or proof of a real draw.
The fixtures must never be installed as trust roots.

## Validation contract

This PR is expected to run the isolated ORIGEN suite and repository CI on its
exact head. No production promotion or provenance status change is permitted.
