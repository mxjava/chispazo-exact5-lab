import argparse, json
from pathlib import Path
from .catalog import generate_frames
from .registry import append_frames, audit_registry
from .critics import critique_bundle
from .protocol import validate_protocol
from .search_ledger import audit_ledger
from .multiplicity import holm_bonferroni
from .evaluation import chronological_split, rolling_origin_folds, evaluate_log_scores
from .null_benchmark import benchmark_nulls
from .diversity import frame_diversity
from .manifest import create_manifest, verify_manifest
from .meta_audit import audit_search_path
from .physical_intake import validate_physical_csv


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_object_key")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise ValueError("non_finite_json_constant")


def _strict_json_loads(text):
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_json_constant,
    )


def _load(path):
    try:
        with open(path, encoding="utf-8") as stream:
            return _strict_json_loads(stream.read())
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError) as exc:
        raise ValueError("input_file_must_be_valid_unambiguous_finite_json") from exc


def _frames(path):
    out = []
    for no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(_strict_json_loads(line))
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError) as exc:
                raise ValueError(f"invalid_json_line_{no}") from exc
    return out


def main():
    parser = argparse.ArgumentParser(prog="origen")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("propose", help="generate alternative research frames"); p.add_argument("--domain", required=True); p.add_argument("--count", type=int, default=10); p.add_argument("--out", required=True); p.add_argument("--critique", action="store_true")
    a = sub.add_parser("audit"); a.add_argument("--registry", required=True)
    v = sub.add_parser("validate-protocol"); v.add_argument("--file", required=True)
    l = sub.add_parser("audit-ledger"); l.add_argument("--ledger", required=True)
    ml = sub.add_parser("audit-search-path"); ml.add_argument("--ledger", required=True)
    pi = sub.add_parser("validate-physical", help="validate V1 source-draw structure; not target pre-close eligibility"); pi.add_argument("--file", required=True)
    h = sub.add_parser("holm"); h.add_argument("--file", required=True)
    s = sub.add_parser("split"); s.add_argument("--n", type=int, required=True); s.add_argument("--warmup", type=int, required=True); s.add_argument("--evaluation-size", type=int); s.add_argument("--rolling", action="store_true"); s.add_argument("--horizon", type=int, default=100)
    e = sub.add_parser("evaluate"); e.add_argument("--file", required=True)
    b = sub.add_parser("benchmark-nulls"); b.add_argument("--file", required=True)
    d = sub.add_parser("diversity"); d.add_argument("--registry", required=True)
    m = sub.add_parser("manifest"); m.add_argument("--base", required=True); m.add_argument("--files", nargs="+"); m.add_argument("--verify"); m.add_argument("--out")
    args = parser.parse_args()
    if args.command == "propose":
        frames = generate_frames(args.domain, args.count); added = append_frames(args.out, frames)
        result = {"generated": len(frames), "added": added, "registry": args.out, "critique": [critique_bundle(x) for x in frames] if args.critique else None}
    elif args.command == "audit": result = audit_registry(args.registry)
    elif args.command == "validate-protocol":
        errors = validate_protocol(_load(args.file)); result = {"state": "PASS" if not errors else "BLOCKED", "errors": errors}
    elif args.command == "audit-ledger": result = audit_ledger(args.ledger)
    elif args.command == "audit-search-path": result = audit_search_path(args.ledger)
    elif args.command == "validate-physical": result = validate_physical_csv(args.file)
    elif args.command == "holm":
        obj = _load(args.file); result = holm_bonferroni(obj["p_values"], obj.get("alpha", 0.05))
    elif args.command == "split":
        result = rolling_origin_folds(args.n, args.warmup, args.horizon) if args.rolling else chronological_split(args.n, args.warmup, args.evaluation_size)
    elif args.command == "evaluate":
        obj = _load(args.file); result = evaluate_log_scores(obj["observations"], protocol_status=obj["protocol_status"], family_p_values=obj["family_p_values"], primary_test_id=obj["primary_test_id"], gates=obj.get("gates", {}), min_observations=obj.get("min_observations", 100), alpha=obj.get("alpha", 0.05))
    elif args.command == "benchmark-nulls":
        obj = _load(args.file); result = benchmark_nulls(obj["observed_statistic"], obj["null_statistics"], obj.get("direction", "greater"))
    elif args.command == "diversity": result = frame_diversity(_frames(args.registry))
    elif args.command == "manifest":
        if args.verify: result = verify_manifest(_load(args.verify), args.base)
        else:
            if not args.files: parser.error("manifest requires --files or --verify")
            result = create_manifest([Path(args.base) / x for x in args.files], args.base)
            if args.out: Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    else: raise RuntimeError("unhandled_command")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
