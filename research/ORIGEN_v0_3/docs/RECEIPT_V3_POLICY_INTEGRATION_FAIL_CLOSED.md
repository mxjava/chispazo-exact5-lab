# ORIGEN v0.3 — V3 receipt-policy integration (research only)

## Purpose

This module composes three existing checks in one fail-closed path:

1. Verify the original V3 signed trust-policy envelope against a caller-supplied Ed25519 root pin, expected key ID, sequence floor and verification time. The integration fixes the expected policy domain to `origen.chispazo.classic.provenance`; it does not accept a caller-selected modality/domain.
2. Verify the original receipt bytes with `verify_receipt_attestation` using the immutable `TrustPolicy` produced from those verified policy bytes.
3. Match the verified receipt issuer/key against the V3-signed authorization tuple `issuer_id + key_id + RECEIPT-ROOT-ATTESTER + TRUST-RECEIPT-ROOT-ATTESTATION`, then call `verify_independent_provenance(original_receipt_bytes)`.

The policy signature, receipt signature and role match are evaluated over original signed bytes. The bridge never accepts a caller-constructed `VerifiedTrustPolicyV3` or `CryptographicallyVerifiedReceipt` as an input.

## Fail-closed result

A successful root signature and signed role match produce only a diagnostic `ReceiptPolicyInspectionV3`. The independent adapter currently has only `BLOCKED_PROVENANCE`; the bridge asserts that exact status and returns it. There is no success enum and no path to production eligibility.

The status `SIGNED_POLICY_MATCH_ONLY_NOT_INSTITUTIONALLY_AUTHENTICATED` is deliberately explicit. A root-signed key/role authorization does not prove the legal identity, appointment, institutional authority or independence of the key holder.

## Adversarial coverage

Synthetic-key tests cover:
- valid V3 policy plus valid receipt root signature, still blocked;
- correct signature but missing receipt-attester role;
- correct role but missing receipt artifact-type authorization;
- correctly signed De las Tres domain rejected by the fixed CLASSIC path;
- sequence below the supplied floor;
- wrong root pin;
- tampered receipt bytes;
- stateful timezone offset sampled once across policy and receipt verification;
- no implicit V2-to-V3 policy fallback.

All keys and receipt fixtures are generated in tests. They are not institutional evidence.

## Remaining security boundary

The bridge does not authenticate:
- the root pin or root-key custody;
- the minimum sequence floor or anti-rollback persistence;
- the caller-supplied clock;
- key identity or institutional role delegation;
- OCSP/CRL revocation freshness;
- RFC 3161 token bytes, TSA chain, nonce or policy OID;
- ledger inclusion, consistency or independently witnessed head;
- nested physical signatures, custody receipts or physical artifact truth;
- the prospective statistical criteria.

The root pin, key ID, sequence floor and time are still caller inputs. The signed V3 policy is only cryptographically verified relative to those inputs. `verify_independent_provenance` remains the final independent kill switch and returns `BLOCKED_PROVENANCE`.

## Non-promotion

This is a research composition and synthetic test surface only. It does not provision trust, change V294, modify canonical history, tune models, seal outputs or enable production. Production remains:

`BLOCKED / RESEARCH_ONLY_NO_EDGE`


## Root/delegate key separation

The bridge rejects a policy whose delegated receipt-attester public key is byte-identical to the pinned policy-root public key. Without this rule, one private key could sign a policy authorizing itself and then sign the receipt, collapsing the intended root/delegate separation. A synthetic regression uses one Ed25519 key for both roles and requires rejection. This is a cryptographic separation-of-duties check only; it does not prove that distinct keys belong to distinct legal entities or administrative custodians.
