from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json

REQUIRED = {
    "protocol_id", "frame_id", "created_utc", "data_scope",
    "primary_outcome", "primary_score", "null_model",
    "alternative_model", "evaluation_design", "horizon",
    "stopping_rule", "multiplicity_family", "exclusion_rules",
    "custody_sha256", "status", "version"
}

def canonical(obj: dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def validate_protocol(obj: dict[str, Any]) -> list[str]:
    errors = []
    missing = REQUIRED - set(obj)
    if missing:
        errors.append("missing:" + ",".join(sorted(missing)))
    for field in ("frame_id", "data_scope", "primary_outcome", "primary_score",
                  "null_model", "alternative_model", "evaluation_design",
                  "horizon", "stopping_rule", "multiplicity_family"):
        if not obj.get(field):
            errors.append("empty:" + field)
    if obj.get("status") not in {"DRAFT", "PREREGISTERED", "CLOSED", "VOID"}:
        errors.append("invalid_status")
    digest = obj.get("custody_sha256", "")
    if digest and (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower())):
        errors.append("invalid_custody_sha256")
    return errors

def seal_protocol(obj: dict[str, Any]) -> dict[str, Any]:
    clean = dict(obj)
    errors = validate_protocol(clean)
    if errors:
        raise ValueError(";".join(errors))
    clean["protocol_sha256"] = hashlib.sha256(canonical(clean).encode("utf-8")).hexdigest()
    return clean

def append_protocol(path: str | Path, obj: dict[str, Any]) -> str:
    sealed = seal_protocol(obj)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("protocol_id") == sealed["protocol_id"]:
                raise ValueError("protocol_id_already_exists")
    with p.open("a", encoding="utf-8", newline="\n") as f:
        f.write(canonical(sealed) + "\n")
    return sealed["protocol_sha256"]
