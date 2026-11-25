# ORIGEN trust-policy V3

Research-only synthetic interface. The root-signed V3 envelope binds each issuer key to explicit roles and artifact types. The verifier checks the tuple (subject, key, role, artifact type) before accepting a nested signature. This is only a policy match relative to a caller-supplied root; it does not authenticate institutional identity, delegation, clock, revocation, ledger or custody. Every result remains BLOCKED_PROVENANCE. V294, canonical history and main are unchanged.
