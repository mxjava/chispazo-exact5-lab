# ORIGEN v0.3 architecture

```text
Problem domain
  └─ Frame catalog / alternative representations
      ├─ Alpha: search for plausible signal and testable claims
      ├─ Omega: construct matched nulls and attack assumptions
      └─ MetaObserver: inspect provenance, multiplicity and search-path completeness
            ↓
      Preregistration + append-only search ledger
            ↓
      Chronological / rolling-origin evaluation
            ├─ Paired prequential log scores
            ├─ Exact sign test
            ├─ Holm-Bonferroni across declared family
            └─ Adversarial-null benchmarks
            ↓
      Gate-based classification + SHA-256 artifact manifest
```

The package separates proposal, protocol, observations, scoring, correction, null benchmarking and custody assertions. No generated frame or critique can authorize its own promotion. External custody and protocol truth remain responsibilities of independent systems and reviewers.
