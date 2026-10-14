from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def load_json_object(path: Path | str) -> dict[str, Any]:
    """Load a JSON object while rejecting duplicate keys at every nesting level."""
    source = Path(path)
    try:
        raw = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read JSON file {source}: {exc}") from exc

    try:
        value = json.loads(raw, object_pairs_hook=_object_without_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {source}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {source}")
    return value
