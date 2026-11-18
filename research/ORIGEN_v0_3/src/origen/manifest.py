"""Create and verify portable SHA-256 manifests for research artifacts."""
from __future__ import annotations
import hashlib
from pathlib import Path

def sha256_file(path: str | Path) -> str:
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def create_manifest(paths: list[str | Path], base_dir: str | Path | None = None) -> dict:
    base=Path(base_dir).resolve() if base_dir else None; entries=[]
    for raw in sorted((Path(p) for p in paths),key=lambda p:str(p)):
        if not raw.is_file(): raise FileNotFoundError(raw)
        label=str(raw.resolve().relative_to(base)) if base else str(raw)
        entries.append({"path":label,"size_bytes":raw.stat().st_size,"sha256":sha256_file(raw)})
    return {"algorithm":"sha256","files":entries}

def verify_manifest(manifest: dict, base_dir: str | Path) -> dict:
    base=Path(base_dir).resolve(); errors=[]; checked=0
    for item in manifest.get("files",[]):
        rel=Path(item["path"]); candidate=(base/rel).resolve()
        if base not in candidate.parents and candidate!=base:
            errors.append({"path":item.get("path"),"error":"path_escape"}); continue
        if not candidate.is_file():
            errors.append({"path":item.get("path"),"error":"missing_file"}); continue
        checked+=1; actual=sha256_file(candidate)
        if actual!=item.get("sha256") or candidate.stat().st_size!=item.get("size_bytes"):
            errors.append({"path":item.get("path"),"error":"hash_or_size_mismatch","actual_sha256":actual})
    return {"checked":checked,"errors":errors,"state":"PASS" if checked==len(manifest.get("files",[])) and not errors else "BLOCKED"}
