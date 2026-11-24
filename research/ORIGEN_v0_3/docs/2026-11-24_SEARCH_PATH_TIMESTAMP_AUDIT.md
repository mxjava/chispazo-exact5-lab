# ORIGEN search-path timestamp audit — 2026-11-24

## Defect reproduced

The search-path auditor appended timezone-naive datetimes to its monotonicity
comparison list even after recording a blocker. If a later event carried an
aware UTC timestamp, Python raised TypeError while comparing naive and aware
datetime objects. The audit crashed instead of returning a fail-closed result.

The same parser also treated RFC 3339 -00:00 as an ordinary zero UTC offset,
although that notation means the local offset is unknown. In addition, the
field is named timestamp_utc but the old auditor accepted nonzero local offsets.

## Correction

- Only explicit, syntactically bounded timestamps with a known UTC offset enter
  the monotonicity comparison.
- Naive timestamps are blocked and excluded from comparisons.
- RFC 3339 -00:00 is blocked as timestamp_unknown_offset.
- Nonzero offsets are blocked as timestamp_not_utc.
- All accepted instants are normalized to timezone.utc before ordering.
- Three regressions cover naive/aware comparison crashes, unknown -00:00 and
  non-UTC offsets.

## Remaining limitation

A valid UTC timestamp string is still a self-declared local ledger value. This
check does not authenticate a clock, establish trusted time, or prove that an
event existed at the declared instant. Independent timestamping and custody
remain unavailable; the independent trust adapter stays fail-closed.
