from __future__ import annotations

import argparse


BLOCKED_REASON = (
    "BLOCKED: canonical-history append is disabled. A result URL and five numbers "
    "do not authenticate an official Chispazo result. Article 8 of the Chispazo "
    "regulation makes website and result-mask publications informational only; "
    "the official result is the signed Article 15 Acta. Re-enable append only "
    "after an independently reviewed verifier validates the original Acta bytes, "
    "required signatures/authority, draw identity and modality, supporting records, "
    "and custody. This command made no file changes."
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Append one Chispazo result only after independent official-Acta "
            "verification. Currently fail-closed and disabled."
        )
    )
    parser.add_argument("--history", required=True)
    parser.add_argument("--contest", required=True, type=int)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--numbers", required=True, nargs=5, type=int)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--provenance", default="data/history/provenance.csv")
    parser.parse_args()

    raise SystemExit(BLOCKED_REASON)


if __name__ == "__main__":
    raise SystemExit(main())
