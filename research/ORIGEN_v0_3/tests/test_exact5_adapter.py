import csv,tempfile,unittest
from pathlib import Path
from origen.exact5_adapter import load_and_audit_history,descriptive_diagnostics,build_research_packet
class Exact5AdapterTests(unittest.TestCase):
 def make(self,p,rows):
  with p.open("w",newline="",encoding="utf-8") as f:
   w=csv.writer(f); w.writerow(["CONCURSO","R1","R2","R3","R4","R5","FECHA"]); w.writerows(rows)
 def test_order(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"h.csv"; self.make(p,[[2,1,2,3,4,5,"x"],[1,2,3,4,5,6,"x"]]); r=load_and_audit_history(p,None); self.assertEqual([x["contest"] for x in r["chronological_draws"]],[1,2])
 def test_hash(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"h.csv"; self.make(p,[[1,1,2,3,4,5,"x"]])
   with self.assertRaises(ValueError): load_and_audit_history(p,"0"*64)
 def test_duplicate(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"h.csv"; self.make(p,[[1,1,2,3,4,5,"x"],[1,2,3,4,5,6,"x"]])
   with self.assertRaises(ValueError): load_and_audit_history(p,None)
 def test_noncontiguous(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"h.csv"; self.make(p,[[1,1,2,3,4,5,"x"],[3,2,3,4,5,6,"x"]])
   with self.assertRaises(ValueError): load_and_audit_history(p,None)
 def test_bad_draw(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"h.csv"; self.make(p,[[1,1,1,3,4,5,"x"]])
   with self.assertRaises(ValueError): load_and_audit_history(p,None)
 def test_diagnostics(self):
  r=descriptive_diagnostics([{"numbers":[1,2,3,4,5]},{"numbers":[1,3,5,7,9]}]); self.assertEqual(r["draws"],2); self.assertIn("Descriptive",r["interpretation"])
 def test_no_promotion(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"h.csv"; self.make(p,[[1,1,2,3,4,5,"x"],[2,2,3,4,5,6,"x"]]); r=build_research_packet(p,Path(d)/"out",None)
   self.assertEqual(r["classification"],"RESEARCH_ONLY_NO_EDGE"); self.assertFalse(r["model_promotion"]); self.assertFalse(r["v294_modified"])
if __name__=="__main__": unittest.main()
