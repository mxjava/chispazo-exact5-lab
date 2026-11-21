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
- Custodian-issued receipt JSON matching the schema below.
- Sigstore bundle for the receipt, signed by the custodian identity.
- Explicit trust configuration supplied out-of-band: exact certificate identity
  and OIDC issuer for the independent custodian.

## Receipt schema 1.0

Required keys (no extras, duplicate JSON keys refused):

```json
{
  "schema_version": "1.0",
  "receipt_type": "INDEPENDENT_CUSTODY_RECEIPT",
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

## Invocation

```powershell
python -m src.validation.independent_custody `
  --manifest PATH_TO_COMMITMENT.json `
  --receipt PATH_TO_CUSTODIAN_RECEIPT.json `
  --payload PATH_TO_EXACT_PAYLOAD.bin `
  --bundle PATH_TO_RECEIPT_BUNDLE.json `
  --custodian-identity "EXACT_TRUSTED_CERTIFICATE_IDENTITY" `
  --oidc-issuer "EXACT_TRUSTED_OIDC_ISSUER"
```

Exit codes: 0 only after byte/metadata validation **and** successful cosign
verification; 2 for blocked provenance. A structural pass alone is explicitly
not `CUSTODY_ACCEPTED`.

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
