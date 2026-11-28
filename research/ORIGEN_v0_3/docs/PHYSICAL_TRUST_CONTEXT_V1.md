# ORIGEN v0.3 — provider-owned physical trust context v1

**Classification:** executable fail-closed interface contract / RESEARCH ONLY. No institutional trust context or production provider is provisioned by this change.

## Problem closed at the application boundary

The physical custody/ledger/witness verifier previously accepted these trust decisions as ordinary caller keyword arguments: policy-root key and sequence floor, policy TSA root/fingerprint/OID, custody TSA root/fingerprint, transparency-log key and identifiers, and witness-registry root/identifier/sequence floor.

The deployment-composition entry point now rejects those arguments if the evidence submitter supplies them. It obtains a typed `PhysicalTrustContextV1` only through the provider's `read_physical_trust_context(policy_domain="origen.chispazo.classic.physical")` method and constructs the verifier arguments itself. Missing provider support, wrong context type, malformed keys, or certificate-fingerprint mismatch fails closed before physical verification.

## Context fields

The frozen context binds:
- policy TSA root DER bytes, exact SHA-256 and authorized policy OID;
- physical policy root Ed25519 key, key ID and minimum accepted sequence;
- custody TSA root DER bytes and exact SHA-256;
- transparency-log Ed25519 key, log ID and key ID;
- witness-registry Ed25519 root key, key ID, registry ID and minimum sequence.

Request-specific nonces and evidence bytes remain request inputs; they are not trust anchors. The verification instant still comes from the deployment provider's single authenticated clock snapshot.

## V2 nested-signature timestamp trust pin

The V1 context now has an optional all-or-none triple for the nested-signature bundle TSA: exact root-certificate DER, its lowercase SHA-256 fingerprint, and the canonical numeric policy OID. When present, the fingerprint and policy OID are included in the provider-context digest, and the deployment composition copies the exact fields before hashing/using the context. Legacy V1 contexts may omit all three fields. A V2 bundle-timestamp composition must require the complete triple; it must not fall back to the policy or custody TSA root implicitly.

This addition is only a provider-owned transport pin. It does not establish that the provider loaded it from an authenticated institutional source, that the TSA is authorized by Lotería Nacional, or that current revocation is checked.

## Important security boundary

A Python Protocol, frozen dataclass, repository commit, environment variable or synthetic provider does not prove institutional provisioning. The provider must load this context from a separately administered trust store with authenticated provisioning records, two-person approval, key rotation/revocation controls and rollback-resistant state. The interface added here does not implement that infrastructure.

The Incode PSC material remains only a public-metadata candidate: the actual DER certificates, current TSA policy/practices bytes, path validation, revocation evidence and live RFC 3161 response have not been captured and verified. No Incode certificate fingerprint is pinned by this change. No public Lotería Nacional signing key or authorization for a third-party TSA to attest Chispazo physical events has been established.

## Verification contract

- The evidence submitter cannot override trust roots, key IDs, policy OIDs or sequence floors through `physical_verification_kwargs`.
- The provider's deployment snapshot supplies one clock instant shared by physical and deployment verification.
- The provider-owned physical context is fetched before physical verification; absent context means no verification and no CAS.
- Physical verification must succeed before the deployment provider's monotonic compare-and-advance.
- Outputs remain `BLOCKED_PROVENANCE`; production remains `BLOCKED / RESEARCH_ONLY_NO_EDGE`.

## Remaining external gates

1. Implement and independently assess a real provider method backed by a protected trust store.
2. Obtain original Incode certificate DER and policy/practice objects from authenticated sources; hash and validate chain, EKU, Key Usage, validity and revocation.
3. Obtain authorization for the TSA policy OID and endpoint, and validate a live nonce-bound RFC 3161 response.
4. Provision and independently witness log and registry roots, identifiers, rotation/revocation state and monotonic floors.
5. Obtain Lotería Nacional's institutional signature verification material and authentic draw-specific acts, CS-11, weighing strips and custody receipts.
6. Independently validate operational separation and custody; synthetic tests cannot satisfy these gates.
