# PR #13 exact-head CI and ORIGEN trust-boundary recheck

**Observation:** 2026-11-23 23:55 America/Mexico_City / GitHub run timestamps 2026-11-24 UTC  
**Scope:** exact current heads of PR #13 and PR #26; structural parser and independent adapter review only.

## PR #13 — current head verified

- State: OPEN / DRAFT.
- Head: `2646bcddf52ce629a52f580f7535096a67c7ead1`.
- Base: `582e5e3794c1fe36b33f5cc8dbd08a4b03a3d69c`.
- Isolated ORIGEN run [45312809129](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/45312809129): completed successfully on that exact head; `unit-tests` job passed; log: **Ran 406 tests in 30.151s — OK**.
- Root CI run [45312809258](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/45312809258): completed successfully on that exact head; `compileall` passed; `pytest -q`: **608 passed, 2 skipped, 128 subtests passed in 71.94s**.
- The run metadata was checked through the GitHub Actions API; both runs are `pull_request` events and their `head_sha` equals the PR #13 head above.

## PR #26 — current head revalidated

- State: OPEN / DRAFT.
- Head: `8883320be0e2bd4c6ba892d7fdfe4246da171222`.
- Base: exact PR #13 head `2646bcddf52ce629a52f580f7535096a67c7ead1`.
- Isolated ORIGEN run [45334048418](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/45334048418): exact-head success; **423 tests in 33.188s — OK**.
- Root CI run [45334048335](https://github.com/mxjava/chispazo-exact5-lab/actions/runs/45334048335): exact-head success; `compileall` passed; **625 passed, 2 skipped, 128 subtests passed in 47.92s**.

## Structural trust-boundary audit

Inspected on the PR #26 head:

- `src/origen/physical_evidence_manifest_v1.py`: required artifact coverage; CLASSIC 21:00 target-slot check; artifact/signature/custody/time-proof cross-references; unique signature digests and one signature claim per subject per artifact; required Acta roles; exactly four distinct weighing-strip signers; literal separation of source, signer, custodian, time-authority and ledger IDs.
- `src/origen/trust_receipt_v1.py`: canonical bounded JSON; unique signer key IDs, subject IDs and signature digests; unique custodian subjects; signer/custodian separation; unique authority/event pairs; distinct generators and output-seal commitments; issuer, time-authority and ledger anti-alias checks.
- `src/origen/trust_receipt_v2.py`: delegates unchanged V1 invariants, requires three distinct timestamp-proof references, and structurally binds the receipt-attestation proof to the exact decoded signature bytes and each output-seal proof to its declared signature digest and creation time.
- `src/origen/independent_trust_adapter.py`: only `BLOCKED_PROVENANCE` exists; the adapter accepts exact non-empty bounded bytes and always returns that status. It has no `AUTHENTICATED` state and no caller-controlled trust roots or verifier callback.

No reproducible structural parser bypass was established in these inspected paths, so no speculative code change was made. The structural parser's declared digests, roles and times remain untrusted claims. This was a scoped review, not a claim that every CLI, pipeline or divergent branch has been exhaustively audited.

## Remaining external trust blockers

- Real original artifact bytes and immutable intake/custody.
- Independently provisioned and pinned institutional signer/TSA roots.
- Verification of detached signatures, role authorization, key validity and revocation.
- Actual RFC 3161/CMS token verification and trusted-time policy.
- Independently anchored append-only ledger and authenticated custody.
- Two independently sealed pre-close Classic outputs.

Passing CI proves the tested software contracts only; it does not authenticate any source, identity, timestamp, ledger or physical draw. Production remains **BLOCKED / RESEARCH_ONLY_NO_EDGE**.

## Follow-up — 2026-11-24 00:55 America/Mexico_City

### Official result and mask recheck

- The dedicated Chispazo results page still displayed 12392 dated 23-Nov-2026 as latest, combination **06 11 16 23 28**, and showed 24-Nov-2026 as the next draw date.
- Its historical table also displayed 12391 = **03 07 19 20 24** and 12392 = **06 11 16 23 28**.
- The official Mascarillas index's newest visible entry was **RESULTADOS 2026-11-23**. Opening its linked one-page PDF showed both contest IDs and combinations. The PDF text extraction did not label the two Chispazo modalities.
- The official Chispazo product page states De las Tres at 15:00 and Clásico at 21:00. Modality assignment is therefore schedule-cross-referenced; it is not claimed to be printed in the PDF text.
- No 24-Nov result, contest ID, or 24-Nov mask was visible at this observation. The observation predates both daily Chispazo slots.

Sources:
- https://www.loterianacional.gob.mx/Chispazo/Resultados
- https://www.loterianacional.gob.mx/Mascarillas/Mascarillas
- https://www.loterianacional.gob.mx/Documentos/juegos/Concursosysorteos/Mascarillas/resultados%202026-11-23.pdf?v=23112026215757
- https://www.loterianacional.gob.mx/Chispazo/Chispazo

Original HTML and PDF response bytes were not captured; no source-byte SHA-256 is claimed. The observation timestamp is local runtime metadata, not a trusted timestamp. No signed Acta, signed participation/cancellation file, CS-11 original, 28-sphere weighing strip, calibration certificate, machine-to-contest linkage, sphere-ID mapping, RFID trace, independent custody receipt, trusted timestamp or two pre-close output seals were obtained. This is public-results status, not authenticated physical provenance.

### Direct mapping-API trust-field rejection regression

A focused review of `physical_intake_v2.py` and its tests confirmed that caller-provided reference sets are only structural membership declarations and that the in-memory row API enforces an exact closed column set. Added `test_in_memory_rows_reject_untrusted_authentication_claims` to exercise attempts to inject `authenticated`, `authentication_status`, `provenance_status`, and `predictive_eligibility=EDGE_SUPPORTED` into a row. Each must be rejected as an unexpected column before classification.

This is regression coverage for an existing fail-closed behavior, not a new authentication feature or a claim that an exploit was present. No parser behavior, predictive model, V294, or canonical history was changed.

The PR #13 exact head remains `2646bcddf52ce629a52f580f7535096a67c7ead1`; its latest exact-head workflows remain successful (ORIGEN run 45312809129: 406 tests; root run 45312809258: 608 passed, 2 skipped, 128 subtests). PR #26 was at `3716bf59d040957829a3b533753ad29bd378ce50` before this coverage commit; exact-head CI for the new commit must be checked after push.
