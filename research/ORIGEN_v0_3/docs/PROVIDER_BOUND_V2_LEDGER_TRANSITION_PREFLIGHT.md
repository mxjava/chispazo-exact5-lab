# ORIGEN v0.3 — provider-bound V2 ledger transition preflight

**Classification:** RESEARCH ONLY / FAIL CLOSED. Fixtures are synthetic. A successful inspection remains `BLOCKED_PROVENANCE`.

## Gap addressed

The V2 transition verifier composed timestamp-bundle inclusion and RFC 6962 consistency, but its trust pins, policy floor, expected nonce, verification time and accepted old watermark were separate function arguments. The provider already owns the authoritative snapshot, physical trust context, three-nonce challenge and accepted ledger watermark. A caller could accidentally combine a valid proof with values taken from different provider generations.

## New provider-bound adapter

`inspect_provider_bound_transparency_ledger_bundle_transition_v2` now:

1. Reads and validates exactly one deployment snapshot.
2. Reads the physical trust context and checks its generation and canonical digest against that snapshot.
3. Binds the context's policy root/key/floor to the deployment snapshot.
4. Binds the accepted ledger/witness watermark identities to the provider-owned log and registry pins, and rejects an accepted witness-registry sequence below `minimum_registry_sequence`. Because this preflight does not ingest a new signed registry transition, it cannot bootstrap a watermark that is below the configured floor.
5. Requires the distinct nested-signature-bundle TSA root/fingerprint/OID triple.
6. Reads one provider-issued timestamp challenge and checks its domain, backend, state/root/context generations, digest, third nonce and full clock-uncertainty/lease interval.
7. Derives the old checkpoint size/root/digest, log key/IDs, policy root/floor, TSA pin, nonce and earliest verification time from those provider reads.
8. Calls the V2 inclusion + RFC 6962 continuity verifier using those derived values.

No independent trust pin, old watermark, nonce or verification clock is accepted as a separate request parameter.

## Adversarial tests

Synthetic tests cover a valid provider-bound transition at the registry floor, a below-floor accepted registry watermark, context digest drift, log-key/watermark identity drift, missing third nonce, challenge expiry inside the clock uncertainty interval, trusted-time rollback, missing independently provisioned genesis watermark, old-checkpoint substitution and provider snapshot outage. The policy/ledger/provider fixture is built from one shared synthetic key set so it cannot accidentally combine unrelated ephemeral roots. Every failure occurs before any CAS call; the adapter itself never calls CAS.

## Security boundary

This is an application-side provider-bound preflight, not the complete V2 deployment composition. It does not consume the nonce challenge or advance provider state. The provider must independently reload authoritative state, re-verify the exact manifest, nested signatures, RFC 3161 token, policy/receipt/custody signatures, ledger inclusion and consistency, registry and witness statements, revocation state and quorum policy, then atomically consume all three nonces and advance the exact watermark in one linearizable CAS transaction.

The provider implementation, out-of-band trust provisioning, anti-rollback storage, trusted clock, TSA authority, independent witness quorum and physical custody remain unauthenticated. No production provider is included. Production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.
