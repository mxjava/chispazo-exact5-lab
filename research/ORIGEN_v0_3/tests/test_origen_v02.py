import tempfile, unittest
from pathlib import Path
from origen.protocol import validate_protocol, seal_protocol, append_protocol
from origen.search_ledger import append_event, audit_ledger

class V02CompatibilityTests(unittest.TestCase):
    def protocol(self):
        return {"protocol_id":"P-001","frame_id":"ORG-demo","created_utc":"2026-01-01T00:00:00Z","data_scope":"future untouched observations","primary_outcome":"exact set","primary_score":"prequential log score","null_model":"uniform combinations","alternative_model":"frozen candidate","evaluation_design":"chronological","horizon":"100 observations","stopping_rule":"fixed horizon","multiplicity_family":"all frames in preregistered batch","exclusion_rules":[],"custody_sha256":"a"*64,"status":"PREREGISTERED","version":"0.2.0"}
    def test_protocol_seal(self):
        obj=self.protocol(); self.assertEqual(validate_protocol(obj),[]); self.assertEqual(len(seal_protocol(obj)["protocol_sha256"]),64)
    def test_bad_custody_hash(self):
        obj=self.protocol(); obj["custody_sha256"]="bad"; self.assertIn("invalid_custody_sha256",validate_protocol(obj))
    def test_protocol_append_only(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"p.jsonl"; append_protocol(p,self.protocol())
            with self.assertRaises(ValueError): append_protocol(p,self.protocol())
    def test_ledger_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"l.jsonl"; e={"event_id":"E1","timestamp_utc":"2026-01-01T00:00:00Z","event_type":"FRAME_PROPOSED","frame_id":"ORG-demo","details":{}}
            append_event(p,e); self.assertEqual(audit_ledger(p)["state"],"PASS")
    def test_ledger_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"l.jsonl"; e={"event_id":"E1","timestamp_utc":"2026-01-01T00:00:00Z","event_type":"FRAME_PROPOSED","frame_id":"ORG-demo","details":{}}
            append_event(p,e); p.write_text(p.read_text().replace("ORG-demo","changed"))
            self.assertEqual(audit_ledger(p)["state"],"BLOCKED")
if __name__=="__main__": unittest.main()
