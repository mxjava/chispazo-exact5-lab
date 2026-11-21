# Exact5 — External cryptographic attestation path (Sigstore/Rekor)

Date: 2026-11-20
Status: WORKFLOW COMMITTED; EXECUTION AND EXTERNAL CERTIFICATION PENDING
Branch: fix/origen-v03-integrity-guards-20261120

## Objective

Create independently verifiable evidence that a public commitment manifest existed before the official sales close, without exposing the 30-line prediction portfolio. The proposed mechanism signs the manifest using a short-lived keyless identity from GitHub Actions OIDC and submits the signed artifact to Sigstore's public Rekor transparency log. The returned bundle contains signature/transparency-log verification material.

Official references:
- Sigstore Rekor overview: https://docs.sigstore.dev/logging/overview/
- Sigstore signing and verification CLI: https://docs.sigstore.dev/logging/cli/
- Rekor API schema (entry, integratedTime, signedEntryTimestamp, inclusion proof): https://github.com/sigstore/rekor/blob/main/openapi.yaml
- OpenTimestamps timestamp proof: https://opentimestamps.org/
- RFC 3161 trusted timestamp protocol: https://www.rfc-editor.org/rfc/rfc3161

## Architecture

1. Generate the portfolio and preserve its exact bytes privately.
2. Create a public commitment manifest containing only hashes and non-sensitive metadata. Do not include the combinations, plaintext ticket, or a reversible encoding.
3. Commit the manifest to the research branch before sales close. The manifest records the generation time, target, modality, candidate commit, history cutoff/hash, portfolio SHA-256, and authoritative scheduled close.
4. Push the single manifest to data/prospective-commitments/<contest-id>.json on the research branch while the sales-close time is still in the future. The push event starts the workflow; workflow_dispatch is also available when the workflow is enabled on the default branch.
5. The workflow checks out full Git history (required to verify older source commits), evaluates the complete push range (`github.event.before` through `GITHUB_SHA`, with a root-commit fallback) rather than only the final commit, and restricts both push and manual-dispatch manifests to `data/prospective-commitments/*.json`. Before reading either the manifest or archived schedule, it checks the Git tree and requires exactly one regular blob (`100644`/`100755`), refusing symlinks and non-regular objects. It validates strict JSON (including duplicate-key rejection), schema version, positive integer contest ID, exact CLASSIC/status values, SHA-256 formats, IANA timezone, HTTPS official schedule-source reference, and the SHA-256 of the archived schedule evidence committed under `data/schedule-evidence/`; it also checks source-commit existence/ancestry, history cutoff, chronology, and that the current time is before close. `scheduled_close_at_utc` is required to carry UTC offset zero (`Z` or `+00:00`); the separate `timezone` field identifies the local IANA zone used to interpret the official schedule. It then signs the manifest with GitHub Actions OIDC using Cosign. Cosign submits the signed entry to Rekor and produces a bundle.
6. The workflow verifies the bundle against the expected GitHub workflow identity and OIDC issuer, then retains the manifest and bundle as an artifact.
7. An independent reviewer downloads the manifest and bundle, verifies the signature/transparency-log proof, checks Rekor's integrated time against the official sales-close source, and independently hashes the private payload when it is released after close.
8. For stronger redundancy, submit the same manifest hash to OpenTimestamps and retain the .ots proof; later verify it after Bitcoin anchoring completes.

## Additional workflow hardening (2026-11-21)

- The push trigger inspects all commits in the push range, not just the tip commit, so a manifest committed earlier in a multi-commit push is still discovered. Initial/root pushes use a root-aware diff.
- Both the manifest and schedule archive must be regular Git blobs; symlinks and non-regular Git objects are rejected before filesystem reads. The schedule archive must also remain under `data/schedule-evidence/` and match its declared SHA-256.
- These are code-level safeguards. They have not yet been exercised by a real attestation run or a negative-test matrix against GitHub Actions; do not report them as runtime-verified until CI or a controlled test proves execution.

## Important limits

- Rekor provides a public append-only transparency log, signed log metadata, and inclusion proofs. Its integrated time is evidence of log inclusion, not a legal finding about the lottery schedule and not a human witness.
- The GitHub OIDC certificate identifies the workflow/repository identity. It does not establish that the repository owner is independent of the prediction generator.
- A workflow artifact with finite retention is not permanent custody. Keep a separate copy of the bundle, manifest, and encrypted portfolio in storage controlled by a genuinely independent reviewer.
- OpenTimestamps proofs may be pending until a calendar aggregates the request into a Bitcoin transaction; do not treat a pending proof as a completed blockchain timestamp.
- RFC 3161 is another valid route only when using a TSA whose policy, certificate chain, and validation status are checked. A timestamp token proves existence at a time; it does not prove content truth or independence of the generator.
- No service can retrospectively timestamp a past draw as pre-close. The workflow deliberately refuses to attest after the recorded close.
- This workflow does not certify predictive edge, does not start the 100-draw evaluation counter by itself, and does not replace the need for independent result auditing.

## Acceptance criteria for first real target

- [ ] Official target contest and sales-close timestamp verified from Lotería Nacional source and preserved.
- [ ] Candidate, configuration, score, and failure rules frozen before the target.
- [ ] Manifest and private payload created before close; payload hash independently recomputed.
- [ ] Manifest includes `schedule_source_url`, `schedule_source_sha256`, and `schedule_source_archive_path`; the archive exists under `data/schedule-evidence/` and its bytes match the digest.
- [ ] Manifest uses schema version `1.0`, positive integer `contest_id`, unique JSON keys, UTC `generated_at_utc` and UTC `scheduled_close_at_utc`, and the exact workflow branch identity.
- [ ] Workflow run completed before close.
- [ ] Cosign keyless verification succeeds for the exact workflow identity and GitHub OIDC issuer.
- [ ] Rekor entry, integrated time, signed entry timestamp, and inclusion proof are independently retrievable and validate.
- [ ] Rekor integrated time is strictly earlier than official sales close.
- [ ] Independent reviewer stores the payload and proofs separately and signs a receipt.
- [ ] Optional OpenTimestamps proof reaches a verifiable anchored state.
- [ ] No late, failed, or missing target is omitted from the ledger.

## Classification

Until a real pre-close workflow run and independent reviewer receipt exist: BLOCKED_PROVENANCE.
After successful Rekor attestation but before independent external retention/review: CRYPTOGRAPHIC_COMMITMENT_VERIFIED / INDEPENDENT_CUSTODY_PENDING.
Only after all acceptance criteria: PROSPECTIVE_CUSTODY_CERTIFIED for that specific target. This is a custody certification only, never an edge/prediction certification.

## Manifest template

An intentionally inert example is stored at `research/ORIGEN_v0_3/templates/prospective_commitment.example.json`. It has `TEMPLATE_ONLY` values, invalid contest/timestamp/hash placeholders, and is outside the workflow trigger path. It must never be copied unchanged into `data/prospective-commitments/` or represented as a real forecast.

## Protected invariants

- V294 remains frozen.
- Canonical historical CSV remains byte-for-byte unchanged.
- No writes to main, no merge, no promotion.
- No retroactive pre-close claims.
