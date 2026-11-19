# Run119 — PMF custody and complete-target ledger

**Engineering reference validated locally; not integrated into the ORIGEN execution or production path.**

- Base: `b780e75b81e8a50b222b512e2d76b6d7b3b52579`
- Isolated branch: `research/run119-pmf-custody-20261119`
- Local package SHA-256: `fd524cee3d4ef0f088e05d4012fa986f5157b2e83c949cde4b305d8979bf2aa1`
- Local validation: 41/41 synthetic tests passed; compileall passed.
- No historical replay, no candidate retuning, no prediction, no official result scoring, no main write, no merge, no promotion.

## PMF contract

The package defines a canonical full PMF over all 98,280 five-of-28 outcomes, in fixed 1-based lexicographic order. Non-negative integer weights are encoded as canonical decimal strings; the exact integer sum is the normalizer. Canonical JSON bytes are hashed and bound to a manifest containing candidate/specification, target, local date/timezone, history cutoff/hash, source commit, dependency/environment hashes, official schedule source, generator/custodian identities and asserted pre-close timestamps.

Scoring uses the exact ratio (q_t(S_t)/(1/98280)). The running log likelihood-ratio process is calculated with threshold \`log(20)\`. A mathematical threshold crossing never changes the returned state from \`BLOCKED_PROVENANCE\`.

## Target completeness

The separate target ledger requires an explicitly official \`CLASSIC\` target manifest and exactly one terminal state per target: \`SEALED\`, \`FAILED\`, \`LATE\` or \`QUARANTINED\`. IDs must increase but need not be consecutive; modality is never inferred from parity. The hash chain detects missing/reordered entries relative to the supplied manifest and detects tail truncation when an external head anchor is supplied.

## Security boundary

Local hash/format validation does not authenticate the official schedule, external signatures, trusted timestamps, custodian identities, model execution or previsibility. A complete ledger is complete only relative to its supplied target manifest. External attestation, independently anchored manifest/head, reproducible model execution and separate integration review remain mandatory.

## Protected state

- V294: frozen.
- Canonical history blob: `2f5ff5bfbd779fe505736398e417b7211955958e`.
- Canonical history SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- No change to the canonical CSV, V294, prior closed runs, `main` or the existing draft PR.

**Disposition:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`. No new prospective target counted.
