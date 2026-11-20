# V320 — Historical Classic Draw Atlas Result

**Run:** GitHub Actions `44530552664`  
**Commit:** `549f83b7e7a2a2791b3825be0672600388758954`  
**Artifact:** `exact5-v320-historical-draw-atlas` (`14533521025`)  
**Artifact SHA-256:** `9eb6d622315ff072c62bd473afddb095fbaa8b5419a508b6f243f0f291ee820d`

## Execution result

- V320 unit tests: PASS.
- Full historical atlas build: PASS.
- Artifact upload: PASS.
- Source SHA-256 verified by workflow: `5a977558c57b6579258d4d6991d3d33fe97e742bc25f59e194ebc8b71928218a`.
- Source rows: 10,887.
- Classic rows: 7,723; contests 1363–12248.
- Enumerated universe: exactly 98,280 unique 5-of-28 combinations.
- Output atlas: 7,723 Classic rows; 4,388,472 bytes.

## Weekday descriptive profile

| Weekday | Classic draws | Mean sum | Mean range | Mean odd count | Mean prime count |
|---|---:|---:|---:|---:|---:|
| Monday | 1,103 | 72.6854 | 19.5621 | 2.4896 | 1.5993 |
| Tuesday | 1,103 | 72.8277 | 19.3436 | 2.5195 | 1.6201 |
| Wednesday | 1,103 | 73.2121 | 19.5168 | 2.5322 | 1.5630 |
| Thursday | 1,103 | 72.7652 | 19.3436 | 2.4733 | 1.5694 |
| Friday | 1,104 | 72.3478 | 19.1866 | 2.5308 | 1.6495 |
| Saturday | 1,104 | 72.6621 | 19.1431 | 2.4882 | 1.6178 |
| Sunday | 1,103 | 72.3690 | 19.0771 | 2.5503 | 1.6020 |

The near-equal weekday sample counts are expected because the game is held daily. The displayed mean differences are descriptive only; they do not establish a weekday effect, predictive advantage, or physical change. No weekday predictive model is promoted from these summaries.

## Integrity and limitations

The canonical CSV was read-only and its SHA-256 was checked before processing. The atlas contains only the canonical history through contest 12249; the last Classic row is 12248. Modality assignment continues to carry its documented structural-provenance limitation and is not a row-by-row official audit of every historical contest. The atlas does not establish an advantage over uniform random selection.

## Decision

`DESCRIPTIVE_ATLAS_COMPLETE`; weekday predictive effect remains **untested**. Next gate: a preregistered weekday × feature omnibus test with multiplicity control, followed by an expanding-window prospective log-score comparison against uniform. No change to V294 and no writes to `main`.
