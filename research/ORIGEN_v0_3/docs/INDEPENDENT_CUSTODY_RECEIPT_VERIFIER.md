# Independent custody receipt verifier

Status: implementation contract; **not a custody certificate**.

## Purpose

The generator repository may create an originator-side commitment, but it cannot
self-certify independent custody. This verifier accepts a receipt only when the
receipt is structurally bound to the exact manifest and actual payload bytes,
names a separately configured custodian identity, records pre-close receipt and
independent retrieval, and carries a separately verifiable Sigstore bundle.

## Required files

- Original commitment manifest (existing project schema).
- Exact payload bytes delivered to the custodian.
- Exact archived official schedule-evidence bytes referenced by the manifest.
- Custodian-issued receipt JSON matching the schema below.
- Sigstore bundle for the receipt, signed by the custodian identity.
- Explicit trust configuration supplied out-of-band: exact certificate identity
  and OIDC issuer for the independent custodian.

## Receipt schema 1.1

Required keys (no extras, duplicate JSON keys refused):

```json
{
  "schema_version": "1.1",
  "receipt_type": "INDEPENDENT_CUSTODY_RECEIPT",
  "manifest_sha256": "64 lowercase hex characters: SHA-256 of the exact manifest bytes received by the custodian",
  "contest_id": 12399,
  "modality": "CLASSIC",
  "candidate_id": "candidate-A",
  "source_commit_sha": "40 lowercase hex characters",
  "payload_sha256": "64 lowercase hex characters",
  "payload_size_bytes": 1234,
  "received_at_utc": "2026-12-01T22:00:00Z",
  "official_close_at_utc": "2026-12-01T23:00:00Z",
  "originator_identity": "originator identity",
  "custodian_identity": "independent custodian identity",
  "retention_uri": "https://independent-retention.example/object",
  "retention_object_version": "immutable object version",
  "independent_retrieval_test": true
}
```

The values above are illustrative only; never use them as a real event.

The custodian must hash the **exact raw manifest bytes** it received and place
that digest in the signed `manifest_sha256` field.
The CLI captures manifest, receipt, payload, official schedule-evidence archive and bundle bytes once in memory; the same
receipt bytes are supplied to structural validation and Cosign, and the same bundle
bytes are supplied to Cosign and Rekor-time parsing. Temporary files are only the
Cosign CLI transport and are checked against the captured bytes after verification. The verifier compares this
digest with the captured manifest bytes before accepting any receipt fields.
The verifier now validates the exact manifest schema and semantics (positive contest ID, CLASSIC modality, source commit/hash formats, history cutoff strictly before target, IANA timezone, official gob.mx HTTPS schedule URL, safe archive path, and generation strictly before close). It also checks that the supplied schedule-evidence archive bytes match `schedule_source_sha256`, and that the payload is exactly 30 unique canonical LF lines of five distinct ascending values from 01 through 28. This binds every manifest field—including history cutoff/hash, candidate metadata, source commit, payload digest, schedule evidence digest, generation time, and official close—to the custodian's signature. Reformatting or changing even one manifest byte
after receipt invalidates the signature-bound digest. Receipt schema 1.0 is
superseded; only schema 1.1 is accepted by the current verifier.

## Invocation

```powershell
python -m src.validation.independent_custody `
  --manifest PATH_TO_COMMITMENT.json `
  --receipt PATH_TO_CUSTODIAN_RECEIPT.json `
  --payload PATH_TO_EXACT_PAYLOAD.bin `
  --schedule-evidence PATH_TO_OFFICIAL_SCHEDULE_ARCHIVE `
  --bundle PATH_TO_RECEIPT_BUNDLE.json `
  --custodian-identity "EXACT_TRUSTED_CERTIFICATE_IDENTITY" `
  --oidc-issuer "EXACT_TRUSTED_OIDC_ISSUER"
```

Exit codes: 0 only after byte/metadata validation, successful Cosign verification,
and a valid Rekor `integratedTime` from the verified bundle proving the signed
receipt entered the transparency log before official close; 2 for blocked
provenance. The claimed `received_at_utc` must not predate manifest generation,
and the verified Rekor time must not materially predate that claim. A structural
pass alone is explicitly not `CUSTODY_ACCEPTED`.

## Mandatory external controls

The identity and issuer must be agreed with the custodian out-of-band and pinned
by the project reviewer. A self-generated key, generator workflow identity,
GitHub artifact, or generator-controlled storage does not qualify. The custodian
must retain the payload outside the generator's administrative control and
demonstrate retrieval by contest, candidate and digest. Two witnessed dry-runs
and negative tests remain mandatory before any production use.

This tool does not prove that a claimed retention URI is immutable, that the
custodian is legally independent, or that physical draw evidence is authentic.
Those require external review and evidence. Prediction custody, physical
evidence certification and statistical edge are separate gates.


## Trusted timestamp boundary

A timestamp typed into the receipt is a signed custodian assertion, not a trusted
timestamp by itself. The verifier therefore requires Cosign to validate the
receipt signature and then requires exactly one valid `verificationMaterial.tlogEntries[].integratedTime`
from that same verified Sigstore bundle. The Rekor integrated time must be before
the official close and cannot materially predate the custodian's signed receipt
time. A missing transparency-log timestamp fails closed.

The repository-controlled workflow is separately named and labelled
`ORIGINATOR_BUILD_ATTESTATION_ONLY`. Its GitHub OIDC identity is not the
custodian identity and its artifact retention is not independent custody.

The archive hash check proves byte identity against the manifest, not that the archive is a semantically correct or authentic official schedule. The independent reviewer must still inspect the archived source and confirm that it actually supports the target, modality, date, timezone and close time. This also does not prove the legal independence of the custodian or the immutability/recoverability of the external retention location. Those require
independent contract/review and witnessed retrieval. The Boolean
`independent_retrieval_test` is a custodian assertion, not a substitute for
the witnessed test report and external audit evidence.
