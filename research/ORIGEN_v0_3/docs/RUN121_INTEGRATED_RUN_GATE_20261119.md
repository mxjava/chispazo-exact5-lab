# Exact5 Run121 — integrated prequential run gate

**Disposition:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`  
**Classification:** `NO_EDGE_EVIDENCE`; `BLOCKED_PROVENANCE` remains active for missing or untrusted external evidence.

## Scope and preservation

Run121 builds a fail-closed cross-component verifier above the Run119 PMF/ledger primitives. It does not replay history, change V294/challengers, score a real draw, add an OOS target, write `main`, merge or promote.

- Base branch: `research/run119-pmf-custody-20261119`, HEAD `5c43c6ff284d14e66fecae70256d076769295906`.
- `main`: `424eee9dd906f8235541e97ae61026441083bbfe`.
- Canonical CSV blob on both refs: `2f5ff5bfbd779fe505736398e417b7211955958e`.
- Canonical CSV SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- V294 remains FROZEN.

## Run121 implementation

The downloadable package adds `src/origen/run_gate.py` and `verify_exact5_run()`. It binds the complete target manifest, signed ledger head, official schedule bytes, exact PMF manifest/payload, history/candidate/dependency/environment bytes, timestamp witness, custody attestation and official-result bytes/claims.

It rejects:
- Arbitrary or unbound SEALED hashes.
- Missing, extra, duplicate or reordered target/result/artifact sets.
- A ledger without a matching externally signed head.
- Non-Mexico-City or non-21:00 Classic close.
- Non-allowlisted Lotería Nacional schedule/results/mask paths.
- Hash mismatches for source, PMF, history, candidate spec, dependency lock and environment.
- History CSV row-count/max-ID mismatch, duplicate IDs, invalid five-number rows or dates after the target.
- Invalid Ed25519 signatures, role/key reuse, wrong claims or timestamp imprint mismatch.
- Candidate epoch changes.

The history snapshot may grow between prospective targets; candidate/spec/code/dependency/environment epoch must remain fixed.

## Limits that remain explicit

- Trust roots and key-to-identity mapping are supplied out of band; signatures against caller-supplied keys do not authenticate the trust roots themselves.
- The timestamp witness is an Ed25519-signed envelope, not an RFC3161 parser.
- The module hashes official HTML/PDF bytes and verifies a trusted custodian's signed parsed-result claims; it does not itself parse Lotería Nacional HTML/PDF.
- The target-manifest signer must independently attest that every expected Classic target is present. Contest-ID parity is never used to infer modality.
- Even a passing synthetic run returns research-only. Holm p-values, dual live score outputs, 100 untouched chronological OOS targets and the final edge decision remain separate gates.

## Local validation

Python 3.13.5, cryptography 46.0.4:
- 68/68 unittest tests passed.
- 68/68 pytest tests passed.
- compileall PASS.
- Includes 24 new Run121 gate tests, Run119 regression tests, Run120 counterexample reproductions and exhaustive 98,280/98,280 rank verification.
- All new Run121 fixtures use synthetic keys, synthetic CSV bytes and synthetic result bytes. They are not real evidence or OOS observations.

The full source/test/workflow package is attached separately as `Exact5_Run121_Integrated_Run_Gate_20261119.zip`, SHA-256:
`f173b3441e0f0b776ee69de2ed96aba44729890961c3e24d0a30eb72a2130fcb`.

**Repository integration status:** this branch checkpoint contains the Run121 report, attestation contract, package manifest/hash and official status-only overlay. The executable Run121 source/tests/workflow are in the verified ZIP but are not yet copied into GitHub repository paths. Do not describe the ZIP as a CI run or integrated repository code.

## Official source checkpoint — 2026-11-19 07:23:35 America/Mexico_City

- Dedicated Chispazo results page still shows 12382, 18/11/2026, `05 09 11 23 25`, with 19/11 as next draw.
- Mask index latest publication: 18/11/2026.
- Home index lists Chispazo 12383 at 15:00; the official schedule maps 15:00 to De las Tres.
- Clásico is scheduled at 21:00, but its 19/11 contest ID is not established. It remains null; no parity inference.
- No 19/11 result was published in the checked direct endpoints at capture time. No result was scored and no target counted.
- Browser-readable pages only; source bytes were not captured. SHA-256 remains NOT_CAPTURED.

Sources:
- https://www.loterianacional.gob.mx/Chispazo/Resultados
- https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- https://www.loterianacional.gob.mx/home/index
- https://www.loterianacional.gob.mx/Chispazo/Chispazo
