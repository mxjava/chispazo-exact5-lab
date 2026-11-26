## Signed policy and receipt-attestation composition (2026-11-26)
- Added a private composition path that verifies the signed trust-policy envelope against a deployment-owned bootstrap snapshot, then passes the resulting `VerifiedTrustPolicy.policy` directly into `verify_receipt_attestation`.
- Added a single-snapshot UTC normalization for the bootstrap clock so a stateful caller-supplied `tzinfo` cannot make the policy and receipt verifiers observe different instants.
- The bootstrap provider still returns `None`; no institutional root, anti-rollback store or trusted clock is provisioned. The public `verify_independent_provenance` remains `BLOCKED_PROVENANCE` even when synthetic root/receipt signatures verify, because nested signatures, original bytes, RFC 3161, ledger, custody and two pre-close seals remain unverified.
- Added synthetic-only adversarial composition tests, including bootstrap-store outage fail-closed coverage, and deployment provisioning/anti-rollback documentation. No test key is a production trust anchor.
- PR #99 draft based on PR #41; exact-head CI pending for the final commit.

## Acta role separation and official 13:10 status refresh (2026-11-24)
- Physical manifest regression: all four required DRAW-ACTA roles could reuse one subject_id; parser now requires distinct declared subjects for the General Directorate, Sales Operations, IT and SEGOB roles.
- Test commit: `3e1384b76db02319c44f9de88baf28ed04197726`; implementation commit: `d8c7b0e8e5ed433f25549aecddb374424d64d41a`.
- Added official status-only overlay and review at 13:10 America/Mexico_City. Official home index showed Chispazo contest 12393 at 15:00 (schedule-inferred De las Tres); results page still ended at 12392 from 23-Nov; mask index still ended at 23-Nov. No 24-Nov result or mask was visible.
- Official 23-Nov mask labels 12391 De las Tres (03 07 19 20 24) and 12392 Clásico (06 11 16 23 28). Original PDF bytes not captured; SHA-256 remains NOT_CAPTURED.
- No primary physical evidence was obtained. The 13:10 overlay is status-only and must not be treated as a draw result or appended to canonical history.
- GitHub Contents API commits from the connected app did not yield workflow-run records for the new HEAD in the available Actions query; exact-head CI remains unverified in this execution.

## Acta subject-uniqueness regression correction (2026-11-24)
- The new regression initially expected a later Acta role-separation error, but CI demonstrated that the existing earlier invariant already rejects a subject declaring multiple signatures for the same artifact (`a subject may declare only one signature per artifact`). The purported gap was therefore not reproducible; the added parser check was redundant and has been removed.
- Retained the adversarial test with the assertion aligned to the actual existing guard.
- Removed redundant parser change commit: `76b32ab4093f0c3f555f842709076ea2533a3925`; corrected test commit: `a3ed13081c489fd873259af0e940e3f4c3633328`.
- This cycle does not claim a new security defect was closed.

## Official home-index schedule supplement — 2026-11-24 13:05 America/Mexico_City
- Added status-only overlay `data/official-overlays/2026-11-24_1305_official_status_only.json` and review `docs/OFFICIAL_STATUS_REFRESH_20261124_1305.md`.
- The official home index displayed the “Ilumina tu suerte” Chispazo card for 24-Nov at 15:00, contest **12393**. The official product schedule maps 15:00 to **De las Tres**, so 12393 is **schedule-inferred**, not result- or mask-confirmed. No 24-Nov Clásico contest ID was visible or inferred.
- The dedicated results page still ended at 12392 (23-Nov) and showed no 24-Nov outcome; the mask index still listed 23-Nov as newest.
- The 23-Nov official mask visually labels 12391 as De las Tres (03 07 19 20 24) and 12392 as Clásico (06 11 16 23 28). Original PDF bytes were not captured; SHA-256 remains `NOT_CAPTURED`.
- No Acta, CS-11, Tira de Pesaje, sphere measurements, calibration, independent custody, trusted timestamp or pre-close seal was obtained.

## One calibration certificate, one validity window in V2 intake (2026-11-24)
- Reproduced a structural inconsistency: 28 sphere rows could share one `scale_id` and one `calibration_certificate_sha256` while declaring different calibration-validity windows. Each row independently covered its measurement, so the target incorrectly remained `STRUCTURAL_PRE_CLOSE_ONLY`.
- Regression-only commit `b68b86d8e75a7b151a1a39f52367b77424dcc59c` failed the isolated suite on `test_one_scale_certificate_cannot_claim_conflicting_validity_windows` (424 tests, one expected red test; run [45465355219](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/45465355219)).
- Fix commit `366ed75d49625fbb9995401c2fd376747b58a160` now requires one distinct parsed calibration-validity window per target group. A conflict maps to `METROLOGY_CONFIGURATION_CONFLICT` / `BLOCKED_CONTINUITY`.
- This binds declarations to one scale/certificate pair only. The parser still does not read or authenticate the certificate bytes, issuer, metrology traceability, or calibration validity.

## Custody writer rejects rehashed structurally invalid records (2026-11-24)
- Found that `write_record_exclusive()` checked only the exact field set and record digest. A caller could mutate a built record to claim a 15:00 Mexico City close under CLASSIC (or a non-prior history cutoff), recompute the public digest, and occupy an exclusive ledger path with a record that the verifier would later reject.
- Added writer-side structural validation before directory creation/file creation: schema and exact scalar types, Classic modality and 21:00:00 Mexico City slot, pre-close timestamp ordering, prior-history cutoff, fixed 30-line declaration, hash declaration consistency, generator/custodian separation and canonical record digest.
- The writer still cannot verify actual portfolio bytes because its API receives no portfolio argument; byte binding remains the verifier's responsibility. This is structural storage hygiene, not independent provenance.
- Implementation commit: `513cd956d135177a05a973d5f80d49e688ab7a2b`; adversarial test commit: `3090ca6f9fba202f562b873c7bd97bf340829e1a`.
- Added regressions for a rehashed 15:00 (De las Tres) slot mislabeled as Classic and a rehashed non-prior history cutoff. Both must fail before a file is created.
- Exact-head CI will be recorded after the documentation commit completes.

## Cross-role source identity separation and Classic custody slot binding (2026-11-23)
- Closed a physical-manifest identity-domain gap: an artifact `source_id` could reuse a signer subject, custodian subject, or trusted-time authority ID. The parser now rejects those cross-role aliases while continuing to allow the same source organization ID across multiple artifacts.
- Closed a custody schedule gap: `build_seal_record` and `verify_seal_record` accepted a 15:00 local close (De las Tres) under a `CLASSIC` label. Both boundaries now require exactly 21:00:00 in `America/Mexico_City`.
- Added adversarial tests for source-ID aliases, legitimate repeated source IDs, builder rejection of the 15:00 slot, and verifier rejection even after an attacker recomputes the record digest.
- Source identity implementation/test commits: `68b89643c27cf91a2eda2c02830a322d6340bbbf` / `a16f74674b2c0ad993755ab646063b104eab2711`.
- Custody slot implementation/test commits: `745bc2e539ab0e6c62fb67d2c356f436804c74f8` / `71812c6eecc6f4170c3fbdf67a474fab7922f7f3`; late-receipt fixture correction: `2e1007da891c03ca082ebde387bf0db204e5c664`.
- Exact-head CI on `2e1007da891c03ca082ebde387bf0db204e5c664`: isolated ORIGEN **406 tests OK**; root CI `compileall` passed and `pytest -q` **608 passed, 2 skipped, 128 subtests passed**. Push and pull-request workflow runs both succeeded.
- These remain structural checks only. They do not authenticate identities, clock sources, timestamps, signatures, physical custody or official draw assignment.

## Official status refresh — 2026-11-23 19:59 America/Mexico_City
- Added status-only overlay `data/official-overlays/2026-11-23_1959_official_status_only.json`.
- The dedicated results page publishes 12391 = 03 07 19 20 24; the official home index places 12391 at 15:00 and shows 12392 at 21:00 without a winning combination. The product schedule maps 15:00 to De las Tres and 21:00 to Clásico, so 12391 is schedule-inferred De las Tres and 12392 remains provisional pending its result or mask.
- The official mask index still lists 22-Nov as latest. Visual review of the 22-Nov PDF confirms 12389 as De las Tres and 12390 as Clásico, but no 23-Nov mask or original PDF bytes were captured; PDF SHA-256 remains `NOT_CAPTURED`.
- Direct review of SGVO-PRO-05 revision 39 confirms 15:00 close for De las Tres, 21:00 close for nocturnal draws, and per-draw weighing after automatic sales close. This is process evidence, not proof of any specific draw's physical records.
- No signed Acta, signed participation file, CS-11, 28-measurement strip, scale calibration, machine-to-contest linkage, RFID log, independent custody receipt, trusted timestamp or two pre-close seals were obtained. Eligibility remains BLOCKED.

## V317.1 lagged intake sequence gate (2026-11-23)
- Added explicit source/target ordinals from an official Classic-only sequence manifest to the V2 physical intake contract. Contest IDs alone are insufficient because Lotería Nacional publishes two Chispazo draws per day (De las Tres at 15:00 and Clásico at 21:00).
- V2 now rejects a target unless its Classic-only ordinal is exactly the source ordinal plus one, requires a manifest reference and SHA-256, and checks caller-declared manifest-reference membership. This is structural validation only: the module does not authenticate the manifest issuer, completeness, signature, timestamp, or custody.
- Updated the V2 draft CSV template, V317.1 proposal, and adversarial tests for skipped Classic sequence ordinals, missing manifest declaration, and malformed manifest digest.
- CI is running on the updated research head. No outcome scoring, beta search, production use, main write, merge, or promotion.

## V317 official timing compatibility blocker (2026-11-23)
- Reconciled V317 with SGVO-PRO-05 Rev. 39 activity flow. The official sequence verifies SICAL sales as closed before the “Pesaje y Colocación de las Esferas” activity; the weighing strip is then checked, signed, attached to the Acta and the spheres are loaded before extraction.
- Same-draw mass is therefore post-close and cannot be represented as a pre-close feature for that same draw. V2's source-to-later-target temporal split can only support a lagged experiment if exact set, sphere-ID mapping and machine continuity to the target are independently proven and the evidence is sealed before target close. Since the procedure requires weighing each draw, prior mass cannot be carried forward by assumption.
- Added `docs/V317_OFFICIAL_TIMING_COMPATIBILITY_AUDIT_20261123.md`; V317 remains BLOCKED until a separately versioned, pre-outcome timing estimand is independently reviewed. No silent reinterpretation, beta tuning or outcome scoring.

## Extreme-mass test assertion correction (2026-11-23)
- CI on `7d5c8573f9867c433edbbee8ee83f28aeda6d283` exposed two test expectation errors: a broad text replacement had reversed the existing positive-beta monotonicity assertion and left the new extreme-mass assertion reversed.
- Restored the existing ascending-mass expectation and changed only the extreme fixture's final 1.0 g sphere to expect a lower log weight than the 1e308 g spheres. Test commit: `d65b87e6cb0bf5add4067a68ac8eae05ed62a567`. Exact-head CI is pending.

## Stable mass centering correction after exact-head CI failure (2026-11-23)
- Exact-head CI on `b7fcf53fbbde20ce027e40487db1b9f4145c0404` exposed an overflow in the new extreme-finite-mass regression: summing 27 finite offsets near 1e308 overflowed `math.fsum` before division.
- Corrected the numerical path by normalizing offsets by their maximum before computing the mean and population standard deviation. This preserves the z-score under positive affine scaling and avoids the intermediate sum overflow.
- Fix commit: `3f7e5a8c9903af33b4428bb3944b80bc6fe45970`. The next CI run passed the former overflow point but exposed an incorrectly directed test assertion: the 1.0 g sphere is lighter than the 1e308 g spheres and must receive the lower log weight for positive beta. Corrected the assertion in test commit `fa427b2c6a0b7cf6b117e41fafb67b283212d9a5`; exact-head CI for the resulting PR head is pending.
- No predictive parameter, preregistration, V294, or historical data change.

## Official procedure reconciliation and 23-Nov status snapshot (2026-11-23 14:51 America/Mexico_City)
- Added `docs/OFFICIAL_PROCEDURE_RECONCILIATION_20261123_1451.md` and status-only overlay `data/official-overlays/2026-11-23_1451_official_status_only.json`.
- Re-reviewed current Normateca: SGVO-PRO-05 Rev. 39 (last updated 20-Mar-2026) directly governs electronic draws. Policy 6 requires per-draw weighing and gives Smartballs 4.25–5.25 g / 0.30 g max spread and Ping Pong 2.30–3.00 g / 0.15 g max spread; policy 25 requires scale calibration at least annually. Policies 8, 9 and 11 establish pre-draw participation-file custody, 15:00 De las Tres / 21:00 nocturnal close, and the Acta attachment matrix including CS-11 and Tira de Pesaje.
- New applicability safeguard: SGVO-PRO-34 Rev. 01 is explicitly limited to Sorteos Tradicionales and is not a Chispazo specification. Its wooden maple-ball 3.0 g ±0.8 g rules must not be imported into the electronic-draw intake.
- At 14:51, official results still ended at 12390 (22-Nov); the 23-Nov 15:00 home card showed 12391 but did not explicitly identify the product, so it remains unassigned. Official mask index latest was 22-Nov; no 23-Nov result, Classic contest ID, or draw-specific primary physical records were visible.
- Original PDF bytes for SGVO-PRO-05, SGVO-PRO-34 and the 22-Nov mask were not captured; hashes remain `NOT_CAPTURED`. No authenticity or draw-specific compliance is inferred from the public procedure.
- No main write, merge, promotion, canonical append, or V294 change; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Custody timestamp unknown-offset rejection (2026-11-23)
- Closed a temporal-interpretation gap: RFC 3339 `-00:00` denotes an unknown local offset, not a known UTC offset. The custody parser now rejects it rather than normalizing it to UTC.
- Added adversarial coverage for all three custody timestamps at both record-build and record-verification boundaries.
- Structural timestamp semantics only; this does not authenticate the clock, trusted-time token, signer, or custodian identity.

## Bounded custody record reads (2026-11-23)
- Closed a reproducible resource-boundary gap in `read_record`: the prior `stat()` then `read_bytes()` sequence could read an unbounded file if it grew after the size check.
- The parser now performs one bounded binary read of at most `MAX_CUSTODY_RECORD_BYTES + 1` and rejects the extra byte before JSON depth scanning or decoding.
- Added an adversarial regression with an oversized file while forbidding the old pre-read `stat()` and unbounded `read_bytes()` path.
- Code commit: `78f434b0a1e8469a4be69d06c802c376f3f7daa2`; test commit: `9b359bd0efd565877b496af586b66f59a384d699`. CI was started on the test commit; exact-head outcomes will be recorded in the PR discussion after completion.
- This is a local resource bound only; it does not authenticate source identity, signatures, timestamps, or custody.

## Official status refresh — 2026-11-23 13:58 America/Mexico_City
- Added status-only overlay `data/official-overlays/2026-11-23_1358_official_status_only.json` and review `docs/OFFICIAL_STATUS_REFRESH_20261123_1358.md`.
- Official results still end at 12390 (22-Nov); the 23-Nov 15:00 home-index card shows 12391 but does not explicitly identify Chispazo or its modality, so it is not assigned. The official schedule remains De las Tres 15:00 / Clásico 21:00.
- Official mask index latest is 22-Nov. No 23-Nov mask or draw-specific primary physical records were obtained; original PDF bytes and SHA-256 remain `NOT_CAPTURED`.
- No canonical append, V294 change, main write, merge, promotion, or eligibility change.

## Physical manifest MIME semantic binding (2026-11-23)
- Closed a structural declaration gap: the v1 manifest accepted any syntactically valid MIME string for any artifact type, so a draw recording could be declared as application/pdf or a non-recording artifact as video/mp4.
- The parser now requires DRAW-RECORDING-FULL and DRAW-RECORDING-EDITED to declare video/* and rejects video/* for all non-recording artifact types.
- Added adversarial regressions for both directions. This validates only the declared MIME/type pairing; it does not inspect original bytes or authenticate source provenance.
- Code commit: `47e56b9b6ff20697c7c53829cf50d1fb741abeb5`; test commit: `aa2487d66420399a6d78d7d9927152a2d184be86`. Final CI will be recorded against the resulting PR head after documentation and source-status overlay commits.

## Physical manifest signer/custodian separation (2026-11-23)
- Fixed a structural trust-boundary gap: the physical manifest previously prevented a trusted-time authority from aliasing signers/custodians but did not prevent the same declared subject ID from acting as both artifact signer and archive custodian.
- The parser now rejects any intersection between signer subject IDs and custodian subject IDs; added a regression that mutates a valid fixture to self-custody an artifact under a signer identity.
- This checks literal identifiers only. It does not authenticate legal identities, roles, or actual organizational independence; the independent adapter remains fail-closed.

## Correct Classic slot binding in physical intake V2 (2026-11-23)
- Audit found the V2 physical-intake guard was applied to `source_draw_at` and `target_draw_at`, although the temporal contract defines these as actual extraction timestamps and SGVO-PRO-05 revision 39, policy 9, sets the automatic sales close for nocturnal draws at 21:00.
- Moved the exact 21:00:00 America/Mexico_City check to `draw_close_at` and `target_draw_close_at`. Actual extraction timestamps remain governed by chronology and may follow the close; no unsupported upper bound is inferred from the inspector attendance window.
- Updated fixtures to use 21:00 sales close, then measurement/signature/extraction after close. Added regressions proving that 15:00 De las Tres close and 21:00:59 close timestamps are rejected while actual Classic extraction after 21:00 is accepted.
- Structural schedule correction only. It does not authenticate event clocks, signatures, physical records, custody or independent trust; no model or V294 change.

## Exact Classic slot precision in ORIGEN V1 and V2 (2026-11-23)
- Hardened both schedule guards to require **21:00:00 exactly** in `America/Mexico_City`, including zero seconds and microseconds. The prior hour/minute-only comparison accepted a declared 21:00:59 timestamp as the Classic draw slot.
- V1 receipt regression cases reject 15:00 (De las Tres), 20:59, 21:00:59 and 22:00; the valid 21:00:00 fixture remains accepted. V2 physical-intake regression rejects a 21:00:59 target draw time.
- Commits: V1 parser `5c874e5a56c2a819955fc0cae686d30772095e51`; V2 schedule helper `565b81bca214fa81199bd2666d7c2549e851a877`; V1 test `8c94eaba33d9f7ed78430da39cbc34b93559fe82`; V2 test `aa1582671f80d9a07fd8f1635891068ce91e3559`.
- CI on test commit `aa1582671f80d9a07fd8f1635891068ce91e3559`: isolated ORIGEN run `45170718622` passed **333 tests**; root CI run `45170718667` passed `compileall` and `pytest -q` (**535 passed, 2 skipped, 100 subtests passed**).
- The fixed slot is a structural schedule guard, not an authenticated schedule feed. If Lotería Nacional authorizes a schedule change, the code policy must be versioned and independently reviewed before accepting the new slot.

## Official procedure evidence baseline — 2026-11-23
- Directly reviewed the official **SGVO-PRO-05, Procedimiento Sorteos Electrónicos**, revision **39**, published 20-Mar-2026, 38 pages, footer DN-07 Version 09.
- It specifies automatic sales close at 15:00 for De las Tres and 21:00 for nocturnal draws; the Chispazo product page maps those slots to De las Tres and Clásico respectively.
- The Chispazo Acta attachment matrix lists the Sumario de sorteo (cierre de venta), CS-11, Sumario de sorteo and Tira de Pesaje. The Tira de Pesaje requires signatures from the weighing responsible person, Dirección de Operación de Concursos, Juegos y Sorteos representative, Dirección General representative and SEGOB inspector. Participation/cancellation file signatures and safe custody are also required by the procedure.
- These are official process requirements, not evidence that contest 12390 records were produced or independently preserved. Procedure PDF original bytes and SHA-256 were not captured.

## Classic schedule binding in trust receipt V1 (2026-11-23)
- The V1 trust-receipt parser now requires a declared `CLASSIC` target close timestamp to resolve to the official **21:00 America/Mexico_City** slot. Previously, the parser accepted any valid UTC close time while still labeling the target CLASSIC; that allowed a 15:00 De las Tres time or an arbitrary late close to satisfy the structural pre-close comparison.
- Added an adversarial test covering 15:00, 20:59 and 22:00 local close claims. This aligns the V1 receipt target boundary with the existing V2 physical-intake schedule check.
- The check is a schedule-consistency guard only. It does not authenticate the contest ID, official schedule source, clock, timestamp token, receipt signature, or physical evidence.
- Code commit: `f5ac7da6c424149c62f7de9f66b70546ca1d3958`; test commit: `ab035c87e5289ebad6f86060816b9469ea530844`. CI on test commit `ab035c87e5289ebad6f86060816b9469ea530844` passed: isolated ORIGEN run `45170098787` (**332 tests**); root CI run `45170099100` passed `compileall` and `pytest -q` (**534 passed, 2 skipped, 99 subtests passed**). Subsequent commits in this entry add only status documentation and do not change executable code.

## Official status refresh — 2026-11-23 05:57 America/Mexico_City
- Official results page still publishes 12390 = 01 06 09 19 23 and 12389 = 01 15 17 22 25; it shows 23-Nov as the next draw date but no 23-Nov result.
- Official mask index lists 22-Nov as newest. The one-page 22-Nov PDF was opened and visually confirms 12389 as De las Tres and 12390 as Clásico. The official product page maps those modalities to 15:00 and 21:00 respectively.
- The opened home-index rendering shows 22-Nov 21:00 / 12390, not a 23-Nov card. A search-index snippet separately mentions 23-Nov 15:00 / 12391, but it conflicts with the opened rendering and does not explicitly identify the product; it is retained as unconfirmed and not added to the target register. No 23-Nov Clásico ID is inferred.
- No new draw-specific primary physical records were obtained. The official PDF was browser-rendered but direct download failed; original bytes and SHA-256 remain `NOT_CAPTURED`. Overlay: `data/official-overlays/2026-11-23_0557_official_status_only.json`.
- No canonical append, V294 change, main write, merge, promotion or eligibility change.

## Ledger-anchor transition integrity (2026-11-23)
- The unverified trust-receipt parser now rejects a ledger anchor whose resulting head digest is identical to its previous head digest. A declared append must represent a state transition; otherwise the receipt could claim an entry without advancing the committed head.
- Added an adversarial regression test and documented the invariant.
- This is structural consistency only. It does not verify the ledger entry, inclusion proof, external head anchoring, or ledger operator identity.

## Official 22-Nov mask status refresh (observed 2026-11-23 01:52 America/Mexico_City)
- The official mask index now lists the 22-Nov PDF. Visual review confirms contest 12389 is Chispazo De las tres (15:00 slot) and contest 12390 is Chispazo Clásico (21:00 slot); the clock times come from the official product schedule, not printed PDF times.
- The official Chispazo results page shows 12390 = 01 06 09 19 23 and 12389 = 01 15 17 22 25. The opened commercializer page rendered 12389 as latest, so the endpoint discrepancy is retained.
- No 23-Nov result or contest ID was visible; no ID was inferred. Original PDF bytes could not be downloaded; SHA-256 remains NOT_CAPTURED. Public mask data is status-only, not authenticated physical provenance or pre-close evidence.

## Trusted-time authority identity separation (2026-11-23)
- The unverified receipt parser now rejects exact identifier collisions between any declared trusted-time authority and the receipt issuer, signers, custodians, or output generators.
- Added adversarial coverage for all four collision classes and documented the rule in the adapter specification.
- This blocks literal role aliasing only; it does not prove distinct real-world entities, authenticate a TSA/RFC 3161 token, or provision independent trust roots.

# Changelog

## Output-seal signer-reference binding (2026-11-22)
- The unverified trust-receipt parser now requires each output-seal signature digest to resolve to a declared signer signature digest, and rejects duplicate signer signature digests to keep that structural reference unambiguous.
- Updated the synthetic fixture with two distinct signer claims and added adversarial tests for an unreferenced seal signature and aliased signer signature digests.
- This is structural reference integrity only. It does not verify signature bytes, key ownership, signer roles, institutional identity, trusted time, or physical custody; the independent adapter remains fail-closed.

## 0.3.0
- Added chronological and expanding-window evaluation splits.
- Added paired prequential log-score summaries and exact sign testing.
- Applied Holm-Bonferroni to the complete declared family, including ORIGEN's internal sign test.
- Added adversarial-null empirical benchmarking.
- Added frame diversity diagnostics.
- Added SHA-256 manifests and tamper verification.
- Added MetaObserver search-path audit for preregistration ordering and post-outcome adaptation.
- Added CLI interfaces, examples, and 28 unit tests.
- Kept research-only classification; no automatic prediction, promotion, or repository mutation.

## 0.3.1 research hardening (2026-11-19)
- Added pre-close custody record verification with exact schema, candidate-specification hash binding, independent generator/custodian identities, strict UTC ordering, and hash-linked ledger verification.
- Added adversarial tests for altered bytes, record mutation, duplicate targets, deleted/reordered ledger entries, invalid timestamps, and exclusive file creation.
- Implemented the preregistered V316 identity-resolved temporal persistence omnibus: 8,140 statistics across 20 lags, all 28 number identities, all 378 pair identities, and aggregate overlap.
- V316 uses packed-bit pair counts with an independent nested-loop reference oracle; frozen source digest, Classic sample count/boundaries, PCG64 seed 3162026, and 1,999 null simulations are enforced.
- Added an isolated GitHub Actions workflow for the V316 confirmatory historical falsification run. Its output remains research-only and cannot establish prospective predictive edge.
- No change to V294, canonical history, or main; PR remains draft and unmerged.

- Completed frozen V316: 7,723 Classic draws, 8,140-cell maximum family, 1,999 simulations, seed 3162026; observed max |z|=3.70796 vs null 95th percentile 5.85308, Monte Carlo p=0.9995. No rejection and no predictive edge. Report: docs/V316_IDENTITY_PERSISTENCE_RESULT_20261119.md.

## Physical intake validator v1 (2026-11-19)
- Added a long-form physical evidence template with one row per physical sphere and contest; header-only, no fabricated data.
- Added strict validator for 28-sphere completeness, unique physical IDs, exact 1–28 mapping, pre-close timestamps, calibration coverage, units, positive finite mass/resolution, SHA-256-shaped provenance identifiers and within-contest consistency.
- Quarantine labels are explicit; validator does not repair data or estimate bias.
- Added CLI: `origen validate-physical --file <csv>`.
- Added 13 adversarial intake tests. Awaiting final GitHub Actions result on the latest branch head.

## V317 physical-mass Plackett–Luce preregistration (2026-11-19)
- Added exact unordered five-set likelihood for sequential weighted sampling without replacement; no arbitrary draw order is assumed.
- Added log-likelihood ratio against exact uniform 5-of-28 and the corresponding prequential e-process design.
- Added tests against all 120 permutations for a chosen set, normalization over all 98,280 possible sets, uniform beta=0 recovery, and invalid input rejection.
- Preregistered the physical mass test; beta must be independently calibrated on equivalent equipment and frozen before Chispazo outcome labels are inspected. No primary measurements/beta calibration exist; V317 remains blocked, no predictions.

## V318 combinatorial-shape omnibus (2026-11-19)
- Preregistered seven fixed result-only shape families before replay.
- Added exact 98,280-set category probability enumeration and one global Monte Carlo max-statistic test over all categories/families.
- Added adversarial tests for set encoding, feature contracts, exact probability normalization, frozen simulation/source guards and sample-size guards.
- Added isolated GitHub Actions workflow to run unit tests and the 1,999-replicate canonical Classic replay.
- No physical sphere masses or mapping are inferred from the historical winning-number file; no predictive or causal claim is permitted.

### V318 result (2026-11-19)
- Full suite: 140 tests passed; frozen canonical replay and artifact upload succeeded (run 44446819621).
- Global maximum z=2.7721; null q95=4.4837; Monte Carlo p=0.7855 (1,570/1,999 exceedances). `NO_REJECTION`.
- No shape family or category is promoted; no prediction or physical-bias claim.

## V319 fixed-era contrast (2026-11-19)
- Preregistered one fixed era split at 2022-03-10, inherited from V265 rather than selected by this replay.
- Implemented a single max-statistic over 28 number identities, 378 pair identities and 184 V318 shape categories, calibrated using 1,999 pairs of independent uniform era sequences.
- Added numerical, shape, frozen-seed, source-hash and minimum-sample tests plus an isolated workflow.
- A result can indicate only a historical era difference, not a causal machine effect or predictive edge.

### V312 full static mixture result (2026-11-19)
- Canonical Classic-only replay completed successfully (run 44446737614): 7,723 draws, 800 warm-up, 6,923 scored targets.
- Mean log-lift -0.0262296890 nats; cumulative -181.5881; positive fraction 36.07%. Candidate underperformed uniform; no edge.

### V319 result (2026-11-19)
- 146 tests passed; full fixed-era replay and artifact upload succeeded (run 44447156133).
- Era A n=6,075; era B n=1,648; global max z=4.3320; null q95=6.8491; Monte Carlo p=0.1820. `NO_ERA_DIFFERENCE_DETECTED`.
- No causal equipment attribution or predictive signal.


## Trust-receipt timestamp binding and official 22-Nov refresh (2026-11-22)
- The unverified receipt parser now requires the trusted-time proof selected by `receipt_attestation.timestamp_proof_sha256` to carry the same `event_at_utc` as `receipt_attestation.signed_at_utc`. This is an internal consistency check only; it does not verify an RFC 3161 token or authenticate the clock/authority.
- Corrected the synthetic valid fixture and added an adversarial regression test for a one-second mismatch.
- Added status-only overlay `data/official-overlays/2026-11-22_2158_official_status_only.json`. Official Home index places contest 12389 at 15:00 and contest 12390 at 21:00; the official product page maps those slots to De las Tres and Clásico respectively.
- At the 21:58 local observation, official results endpoints still showed 12389 (01 15 17 22 25) and no 12390 combination; the mask index still listed 21-Nov as newest. Contest 12389 is schedule-slot matched to De las Tres, not same-day-mask confirmed.
- No 22-Nov original mask bytes, signed draw act, signed participation file, CS-11, weighing strip, measurements, calibration certificate, trusted timestamp, independent custody receipt, or pre-close seal were obtained. No canonical append, V294 change, main write, merge, or promotion.
- Validation of the parser/test change on commit `7e710244c0975a552aac4399f8a371d1f4287f81`: isolated ORIGEN run `45109181485` passed **323 tests**; root CI run `45109181527` passed `compileall` and `pytest -q` (**525 passed, 2 skipped, 92 subtests passed**). The subsequent overlay/changelog commits are data/documentation only and do not alter executable code; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Trust-receipt JSON depth bound (2026-11-23)
- Added a byte-level, string-aware nesting scan before JSON decoding/canonical re-serialization; receipts deeper than 64 nested objects/arrays are rejected before recursive codec work.
- Added adversarial tests for over-depth input and bracket characters inside strings. The limit is a parser resource bound, not an authentication or provenance claim.
- Pending CI on the updated PR #13 head.

## Official status refresh — 2026-11-23 04:56 America/Mexico_City
- Added status-only overlay `data/official-overlays/2026-11-23_0456_official_status_only.json` and review `docs/OFFICIAL_STATUS_REFRESH_20261123_0456.md`.
- Official results page and 22-Nov mask continue to show 12390 = Classic (01 06 09 19 23) and 12389 = De las Tres (01 15 17 22 25). Mask index latest remains 22-Nov.
- Home index shows a 23-Nov 15:00 card numbered 12391, but the rendered card does not explicitly name the product; it is not bound to the Chispazo target register. No 23-Nov 21:00 Classic contest ID or result was visible.
- No new draw-specific primary physical evidence was obtained. The official 22-Nov PDF could be browser-rendered but not downloaded as original bytes; SHA-256 remains NOT_CAPTURED. SGVO-PRO-05 revision 39 remains procedural reference only.
- No canonical append, V294 change, main write, merge, promotion, prospective score, or eligibility change.
