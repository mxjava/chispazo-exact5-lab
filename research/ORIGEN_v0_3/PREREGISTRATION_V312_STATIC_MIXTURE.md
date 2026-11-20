# V312 — preregistered static expert mixture (research-only)

Status: SPECIFICATION FROZEN; NOT EVALUATED; NOT A PREDICTIVE CLAIM.

## Motivation
The V264 28-expert Bayesian mixture collapsed numerically to the uniform expert during its initial 800-Classic warm-up (median effective experts 1.0; median uniform posterior mass 1.0). This candidate removes online posterior adaptation entirely. It tests whether the fixed expert family contains aggregate information without cumulative posterior collapse.

## Frozen candidate
- Universe: 28 numbers; each draw is an unordered set of 5 distinct numbers.
- Expert family: exactly the 27 non-uniform V264 experts: frequency windows 50/200/800; EWMA half-lives 16/32/64; hotgap, duegap, transition; beta values 0.15/0.30/0.60.
- Uniform probability: 1 / C(28,5).
- Each non-uniform expert uses the V264 normalized set probability and elementary-symmetric-polynomial denominator (sampling without replacement).
- Predictive distribution: 50% uniform + 50% arithmetic mean of the 27 non-uniform expert distributions. Fixed weights; no posterior learning, retuning, or modality pooling.
- Data stream: Classic draws only. De las Tres observations are excluded from features, warm-up, scoring, and updates.
- Warm-up: first 800 chronologically available Classic draws; score all subsequent Classic draws.
- Leakage guard: features at target t use only Classic rows strictly earlier than t; transition context excludes the current context row.
- Missing/invalid records: fail closed; no imputation or synthetic draws.
- Output: per-target log-lift against uniform, cumulative and mean log-lift, positive fraction, exact target IDs, feature cutoff IDs, source SHA-256 and code commit.

## Prospective protocol
- This file is the preregistration anchor; do not alter candidate weights or feature family after observing evaluation outcomes.
- Begin prospective evaluation only after independent custody is configured and two sealed prediction outputs are generated before their corresponding draw close.
- Minimum 100 untouched prospective Classic targets. Keep a chronological holdout; no reuse for model selection.
- Report paired log-score difference versus uniform with a prespecified one-sided test and Holm correction for the single primary candidate family; also maintain the separate Exact5 anytime e-process gate (threshold 20).
- Any implementation change creates a new candidate ID and a new prospective start; no retroactive relabeling.
- Retrospective replay may be used only for implementation integrity and leakage tests, never to select this candidate or claim edge.
- Classification remains RESEARCH_ONLY until all independent prospective gates pass.

## Explicit non-claims
This candidate is not expected to beat uniform, is not a guaranteed improvement, and is not V294. The 50/50 safety mixture provides a fixed floor of half the uniform probability for every valid combination; it does not establish predictive advantage.

## Invariants
- V294 remains frozen and untouched.
- Canonical data/history/Chispazo_through_12249.csv remains byte-for-byte unchanged.
- No writes to main; no merge or promotion from this research branch.
