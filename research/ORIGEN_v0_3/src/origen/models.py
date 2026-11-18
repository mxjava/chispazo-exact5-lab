from dataclasses import dataclass, asdict
import hashlib, json

@dataclass(frozen=True)
class Frame:
    frame_id: str
    domain: str
    lens: str
    representation: str
    assumptions: list[str]
    observables: list[str]
    falsifiable_claim: str
    null_or_rival: str
    prospective_test: str
    failure_conditions: list[str]
    status: str = "PROPOSED"
    version: str = "0.1.0"
    def to_dict(self): return asdict(self)

def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def make_frame(**kwargs):
    payload = dict(kwargs); payload.pop("frame_id", None)
    fid = "ORG-" + hashlib.sha256(canonical_json(payload).encode()).hexdigest()[:16]
    return Frame(frame_id=fid, **payload)
