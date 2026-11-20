import json, tempfile, unittest
from pathlib import Path
from origen.catalog import generate_frames
from origen.registry import append_frames, audit_registry
from origen.critics import critique_bundle

class BaseCompatibilityTests(unittest.TestCase):
    def test_deterministic_ids(self):
        self.assertEqual(generate_frames("x",1)[0].frame_id,generate_frames("x",1)[0].frame_id)
    def test_append_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"r.jsonl"; f=generate_frames("x",2)
            self.assertEqual(append_frames(p,f),2); self.assertEqual(append_frames(p,f),0); self.assertEqual(audit_registry(p)["state"],"PASS")
    def test_critique_never_promotes(self):
        self.assertFalse(critique_bundle(generate_frames("x",1)[0])["meta_observer"]["promotion_authorized"])
if __name__=="__main__": unittest.main()
