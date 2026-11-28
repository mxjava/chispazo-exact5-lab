# ORIGEN v0.3 — V2 ledger transition composition

**Classification:** RESEARCH ONLY / FAIL CLOSED. All fixtures are synthetic. Every successful result remains BLOCKED_PROVENANCE.

## Gap addressed

The V2 bundle verifier validated the exact sidecar, RFC 3161 token, V2 ledger leaf, new signed checkpoint and inclusion proof. It deliberately did not verify the append-only transition from the previously accepted checkpoint. The V1 consistency verifier already performs that cryptographic check, but there was no V2 composition binding its output to the same new checkpoint used by V2 inclusion.

## New composition

The function verify_transparency_ledger_bundle_transition_v2 composes:

1. The V2 sidecar/token/leaf/new-checkpoint inclusion verifier.
2. The existing signed-checkpoint consistency verifier for both checkpoints and the RFC 6962 proof.
3. Exact comparison of the old checkpoint digest, tree size and root against the caller's accepted watermark.
4. Exact equality of the new checkpoint digest and tree size across both verifier results.
5. Strict tree-size growth for an evidence advance; same-size idempotence is not accepted.

The same exact raw_signed_checkpoint_bytes argument is passed to both verifiers. The function does not accept a caller-created inspection object in place of source bytes.

## Security boundary

The verifier still receives the log key, monotonic floor, policy root, TSA root/OID, nonce and verification clock from its caller. It does not authenticate those inputs, verify independent witness quorum, prove global log gossip, verify physical custody, or operate inside the provider's linearizable CAS transaction. It is not yet wired into the full V2 custody/ledger/witness deployment composition. The provider must independently repeat all cryptographic checks and atomically bind the resulting watermark and three nonce consumptions.

No institutional provisioning or physical source authenticity is claimed. Production remains BLOCKED / RESEARCH_ONLY_NO_EDGE.
