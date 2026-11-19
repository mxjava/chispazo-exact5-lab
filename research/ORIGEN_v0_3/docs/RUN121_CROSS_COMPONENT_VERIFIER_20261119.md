# Exact5 Run121 — cross-component provenance verifier

**Disposition:** `BLOCKED / RESEARCH_ONLY_NO_EDGE`  
**Branch:** `research/run121-cross-component-verifier-20261119`  
**Scope:** integrate the Run119 PMF and target-ledger reference modules and add one fail-closed verifier. No historical replay, no candidate retuning, no prediction generation, no actual draw scoring, no canonical-history write, no `main` write, no merge, and no promotion.

## Run121 package contents

- `src/origen/pmf_custody.py` and `src/origen/target_ledger.py` from the Run119 reference archive.
- Their original tests, preserved as separate test modules.
- `src/origen/run_verifier.py`, a new cross-component verifier.
- `tests/test_run_verifier.py`, with synthetic signed fixtures and adversarial cases.
- A dedicated GitHub Actions workflow for these three test modules.
- `cryptography>=44.0` as an explicit package dependency for Ed25519 signature verification.
- A fresh status-only official-source overlay for 19 Nov 2026.

**Repository integration status:** the source modules, tests, workflow and dependency update are packaged and locally validated, but are not yet committed as executable files to the GitHub branch. The isolated Run121 branch contains this report, package manifest and official status overlay only. This distinction is intentional; no CI result is claimed for code that is not yet in GitHub.

## Run120 findings addressed in the package

| Finding | Run121 control |
|---|---|
| Arbitrary SEALED manifest hash | Exact PMF-manifest bytes must hash to the ledger's `payload_manifest_sha256`; the manifest and payload are verified together |
| Scoring a subset | PMF, result and history artifact key sets must equal the complete SEALED target set; non-SEALED targets remain visible and block sequence scoring |
| Wrong Classic close time | Every target must use `America/Mexico_City` and 21:00 local; IDs are never classified by parity |
| Nonofficial schedule URI/timezone | HTTPS host must be `loterianacional.gob.mx` or a subdomain; schedule source bytes and signed target-index extraction are hash-bound; timezone is fixed |
| Unbound result hash | Exact official result-source bytes are hashed and compared with a signed extraction attestation containing target ID, date, modality and numbers |

Additional controls:

- The trust store is canonical JSON and must match a caller-supplied SHA-256 pin held out of band.
- Ed25519 signatures are checked for schedule attestor, ledger notary, PMF custodian, history auditor, result attestor and timestamp authority roles. A principal cannot hold multiple trust-store roles.
- Timestamp attestations bind the signed payload hash and exact UTC timestamp. These are custom signed timestamp envelopes, not RFC 3161 tokens.
- PMF custody signatures bind the candidate, source commit, dependency/environment hashes, schedule, full PMF metadata, history cutoff and generator/custodian timestamps.
- Classic history snapshots require explicit `MODALIDAD=CLASSIC`, an accepted official modality-provenance value, an official source URI and a source SHA reference for every row. `PROVISIONAL_DERIVED` is rejected. Every history row must predate the target draw date.
- An independent history-attestor signature binds the complete snapshot hash, row count, maximum contest ID and a canonical manifest of row-level source references.
- Every later target's history must contain all earlier targets' already verified results with identical date, numbers, source URI and source hash.
- Candidate identity, candidate-spec hash, source commit, dependency lock, environment manifest and timezone remain fixed through the scored sequence.

## Validation

Local Python 3.13.5:

- PMF custody: 24 passed.
- Target ledger: 17 passed.
- Cross-component verifier: 21 passed.
- **Total: 62 passed.**
- `compileall`: PASS.
- Editable install/import: PASS using installed build backend with `--no-build-isolation --no-deps`. The environment could not fetch isolated build dependencies because outbound package-index DNS was unavailable.

All successful-path signatures and source bytes in tests are synthetic fixtures only. They are not official Lotería Nacional captures, external keys, real custody, real timestamps, PMFs or Exact5 scores.

## Explicit limitations

- The trust-store hash must be independently pinned outside this repository.
- Lotería Nacional source documents are not assumed to carry a digital signature. A trusted independent attestor signs extracted fields and captured official bytes; parser correctness and attestor identity remain trust assumptions.
- The history auditor attests that it checked each referenced historical source. The verifier validates snapshot bytes, row schema, source-reference manifest and auditor signature, but does **not** independently download/re-hash every historical PDF byte referenced by every row.
- The batch target manifest must be attested before the earliest target close. The official site does not publish 100 future contest IDs in advance; a live 100-draw study still needs an append-only per-target target-index/ledger-anchor protocol.
- The module computes the Exact5 likelihood-ratio process only after provenance gates pass. It does not verify the full preregistered hypothesis family, Holm correction, two independent live score outputs, 100 untouched OOS targets, or the final edge decision. It always returns `edge_certified=false` and `promotion_authorized=false`.
- No real trust anchors or artifacts were supplied; no real sequence was verified or scored.

## Preserved state

- V294: FROZEN.
- Canonical CSV was not edited. Blob: `2f5ff5bfbd779fe505736398e417b7211955958e`; SHA-256: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- No write to `main`, no merge, no promotion, no historical PMF/rank/score rebuild.
- Run53–56 and previously closed runs remain closed.

**Classification:** `MODEL_IMPLEMENTATION_DEFECT` — cross-component verifier packaged and synthetic-tested; `BLOCKED_PROVENANCE` — no real trust store/custody/source captures; `NO_EDGE_EVIDENCE` — no new OOS score. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
