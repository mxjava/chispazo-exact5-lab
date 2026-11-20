from dataclasses import asdict, dataclass
@dataclass
class Critique:
    agent: str
    frame_id: str
    severity: str
    findings: list[str]
    required_evidence: list[str]
    verdict: str

def alpha_review(frame):
    return Critique("ALPHA",frame.frame_id,"EXPLORATORY",["This is a research question, not evidence of a real effect.","Define a scoring rule and sampling unit."],["Frozen protocol","Untouched prospective observations","Reproducible scoring code"],"PROPOSE_TEST")

def omega_review(frame):
    return Critique("OMEGA",frame.frame_id,"HIGH",["Check outcome-informed selection.","Check leakage, multiplicity, provenance, nonstationarity and matched nulls.","Retrospective fit is insufficient."],["Complete search-path log","Negative controls","Multiplicity correction","Independent provenance","Prospective replication"],"HOLD_PENDING_EVIDENCE")

def critique_bundle(frame):
    a,o=alpha_review(frame),omega_review(frame)
    return {"alpha":asdict(a),"omega":asdict(o),"meta_observer":{"frame_id":frame.frame_id,"audit_state":"RESEARCH_ONLY","decision":"ALLOW_PROTOCOL_DESIGN_ONLY","metric_change_rule":"Post-outcome metric changes are exploratory only.","promotion_authorized":False}}
