# PROYECTO ORIGEN v0.3 — Auditable Research Engine

ORIGEN is a research framework for generating alternative representations of a problem, preregistering tests, tracking the full search path, evaluating chronological score streams, correcting multiplicity, and trying to falsify apparent discoveries.

It is **not** an autonomous truth engine, a lottery predictor, or a model-promotion system. A result marked `EDGE_SUPPORTED` means the supplied score stream passed this package's explicit statistical and declared evidence gates; it does not mean ORIGEN independently verified the external truth of the supplied custody assertions.

## v0.3 capabilities

- Ten distinct initial research lenses and deterministic frame IDs.
- Alpha / Omega / MetaObserver critique contracts.
- Append-only research-frame registry and hash-chained-by-event search ledger (each event individually hashed; not a cryptographic signature or independent custody service).
- Preregistration schema and protocol content hashes.
- Chronological holdout splitting and expanding-window rolling-origin folds; no randomized split.
- Paired prequential log-score comparison (`p_alt` vs `p_null`) with positive-rate, median and exact one-sided sign test.
- Holm-Bonferroni family-wise correction over the full supplied hypothesis family, with ORIGEN's computed sign test automatically included in that same family.
- Empirical adversarial-null benchmarking with finite-simulation +1 correction.
- Search diversity diagnostics based on lenses, representations and observable Jaccard overlap.
- SHA-256 file manifests and tamper verification.
- Signed trust-policy envelope verification and root Ed25519 receipt-attestation verification, composed behind an unprovisioned deployment bootstrap; public independent provenance remains fail-closed.
- Pre-close custody record verification and ordered hash-chain audit (without pretending to provide signatures or trusted timestamps).
- V316 identity-resolved persistence omnibus across 8,140 preregistered statistics, with packed-bit pair counting and reference-oracle tests.
- MetaObserver search-path audit: checks timestamp ordering, protocol-before-outcome access and flags post-outcome adaptation.
- CLI commands for all core functions.

## Installation / execution

Python 3.10+. Core research utilities use the standard library; the ORIGEN cryptographic verification path requires `cryptography>=42.0.0,<47.0.0`, and the isolated package declares `tzdata>=2025.2`.

```powershell
$env:PYTHONPATH = '.\src'
python -m unittest discover -s .\tests -v
python -m origen.cli propose --domain chispazo --count 30 --out .\research\origen_frames.jsonl --critique
python -m origen.cli diversity --registry .\research\origen_frames.jsonl
python -m origen.cli audit --registry .\research\origen_frames.jsonl
```

## Evaluation input contract

`origen evaluate --file evaluation.json` expects a JSON object with:

```json
{
  "protocol_status": "PREREGISTERED",
  "primary_test_id": "primary_log_lift",
  "family_p_values": {"primary_log_lift": 0.001, "all_other_attempts": 0.02},
  "min_observations": 100,
  "alpha": 0.05,
  "gates": {
    "preregistered": true,
    "untouched_prospective": true,
    "independent_custody": true,
    "data_integrity_pass": true,
    "two_prospective_outputs": true
  },
  "observations": [
    {"p_alt": 0.00001, "p_null": 0.00002}
  ]
}
```

Each `p_alt` and `p_null` is the probability assigned to the *same realized outcome* by the alternative and null, respectively, for that observation. Both must be finite and in `(0,1]`. This is a scoring-stream evaluator; it does not generate predictions or certify that those probabilities were computed without leakage. `family_p_values` must include every other hypothesis in the predeclared family, not merely the winning test; ORIGEN inserts its computed sign-test p-value into that same Holm family automatically.

`EDGE_SUPPORTED` is intentionally difficult to reach: at least 100 observations by default, positive mean log lift, a primary Holm-adjusted p-value below alpha, a one-sided sign test below alpha, `PREREGISTERED` status, and every evidence gate true. This utility does not verify the truth of user-supplied booleans. Missing statistical support produces `NO_EDGE_EVIDENCE`; failed data-integrity or custody gates produce `BLOCKED_PROVENANCE`.

## CLI examples

```powershell
python -m origen.cli split --n 1000 --warmup 800
python -m origen.cli split --n 1000 --warmup 800 --rolling --horizon 50
python -m origen.cli holm --file .\research\p_values.json
python -m origen.cli evaluate --file .\research\evaluation.json
python -m origen.cli benchmark-nulls --file .\research\null_benchmark.json
python -m origen.cli manifest --base .\data --files history.csv protocol.json --out .\research\manifest.json
python -m origen.cli manifest --base .\data --verify .\research\manifest.json
```

## Exact5 non-interference constraints

- Do not change frozen V294 or its parameterization.
- Do not edit, normalize, re-export, or overwrite `data/history/Chispazo_through_12249.csv`.
- Do not write to `main`, promote a model, or overwrite any existing V264/V265/V266 evidence.
- Run ORIGEN experiments in a separate research overlay/worktree and preserve original artifacts byte-for-byte.
- A retrospective pattern is exploratory. No claim of predictive edge without the predeclared prospective evidence gates.

## Known limitations

- No automatic access to official data or the user's GitHub repository.
- No institutional trust roots, rollback-resistant policy-sequence store, authenticated clock/TSA, or external independent custody are provisioned. The Ed25519 verifiers are research primitives and do not authenticate embedded physical claims or complete provenance.
- No guarantee that supplied p-values represent the complete search family; the protocol and search ledger must be independently audited.
- The exact sign test checks direction consistency, not model calibration or stationarity.
- Adversarial-null quality depends on the null generators and full discovery pipeline supplied by the research team.
- The framework cannot prove that a random process has no structure; it can report that tested claims failed to establish evidence under specified tests.


### Physical evidence intake v1
- Added a long-form 28-sphere-per-contest template at `data/physical-metadata/PHYSICAL_EVIDENCE_LONG_FORM_TEMPLATE_V1.csv`; it is header-only and contains no observations.
- Added `origen.physical_intake` and CLI command `origen validate-physical --file <csv>` to enforce mapping, timestamps, calibration interval, source hashes, 28-row completeness and quarantine rules.
- Legacy wide template is unchanged and is insufficient by itself for physical-sphere identity linkage. Structural validity does not authenticate records or establish bias.
- See `docs/PHYSICAL_SPHERE_INTAKE_VALIDATOR_V1.md` and `docs/PHYSICAL_EVIDENCE_INTAKE_PROTOCOL_V1.md`.

### V317 physical-mass mechanism (preregistered; blocked)
- Added exact unordered Plackett–Luce likelihood for sequential weighted sampling without replacement and tests against all 120 orders plus normalization across all 98,280 five-number sets.
- Added `PREREGISTRATION_V317_PHYSICAL_MASS_PLACKETT_LUCE.md`. The signed beta must come from independent machine-equivalent physical calibration before any Chispazo outcomes are inspected. No Chispazo physical measurements or beta calibration are currently present; V317 is blocked and produces no picks.

### V318 combinatorial-shape omnibus (frozen replay)
- Added a preregistered, single max-statistic test over seven fixed result-only shape families: sum, range, odd count, prime count, consecutive-adjacent-pair count, low/high split, and three-band occupancy.
- Null calibration enumerates all 98,280 five-sets for exact category probabilities and simulates 1,999 complete independent uniform Classic sequences. This tests shape departures not directly covered as a joint family by V313–V316.
- This is historical falsification only. It cannot recover sphere masses or establish physical bias; no feature/category may be promoted from a rejection without separate prospective validation.
- See `PREREGISTRATION_V318_COMBINATORIAL_SHAPE_OMNIBUS.md`.

- V318 completed with 140 tests passing and canonical replay success. Its global max-statistic was 2.7721 versus null 95th percentile 4.4837; Monte Carlo p=0.7855 (1,570/1,999 null replicates at least as extreme). Decision: `NO_REJECTION`. See `docs/V318_COMBINATORIAL_SHAPE_RESULT_20261119.md`.

### V319 fixed-era contrast (frozen replay)
- Adds one fixed pre/post contrast at 2022-03-10, inherited from the existing V265 regime boundary (not a verified machine identity). It compares number, pair and all V318 shape-category proportions under a single global Monte Carlo max-statistic.
- The question is whether the result distribution differs across this historical boundary; any rejection is historical only and cannot be attributed to a machine or sphere set without equipment records.
- See `PREREGISTRATION_V319_FIXED_ERA_CONTRAST.md`.

- V312 full fixed 27-expert static mixture replay completed successfully: 6,923 Classic targets, mean log-lift -0.0262296890 nats, cumulative -181.5881, positive fraction 36.07%. It underperformed uniform; see `docs/V312_STATIC_MIXTURE_RESULT_20261119.md`.

- V319 completed: 6,075 Classic draws before 2022-03-10 and 1,648 on/after. Global 590-category max-statistic p=0.1820 (363/1,999 null replicates >= observed); no era difference detected. This does not identify or establish a machine change. See `docs/V319_FIXED_ERA_CONTRAST_RESULT_20261119.md`.
