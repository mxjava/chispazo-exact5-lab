import json
import math
import tempfile
import unittest
from pathlib import Path
from origen.multiplicity import holm_bonferroni
from origen.evaluation import chronological_split, rolling_origin_folds, evaluate_log_scores
from origen.null_benchmark import benchmark_nulls
from origen.diversity import frame_diversity
from origen.manifest import create_manifest, verify_manifest
from origen.protocol import validate_protocol
from origen.catalog import generate_frames
from origen.search_ledger import append_event
from origen.meta_audit import audit_search_path
from origen.registry import append_frames, audit_registry
from origen.critics import critique_bundle
from origen.nulls import shuffled_rows, within_row_permutation, independent_uniform_draws

P0 = 1.0 / 98280.0
REQUIRED_EDGE_GATES = (
    "preregistered", "untouched_prospective", "independent_custody",
    "data_integrity_pass", "two_prospective_outputs", "pmf_custody_verified",
    "complete_target_ledger", "official_modality_verified", "preclose_snapshot_verified",
)

class TestORIGENV03(unittest.TestCase):
    def test_holm_monotone(self):
        r=holm_bonferroni({"a":.01,"b":.04,"c":.03}); self.assertEqual(r["family_size"],3)
        self.assertAlmostEqual(r["results"]["a"]["p_adjusted"],.03)
        self.assertAlmostEqual(r["results"]["c"]["p_adjusted"],.06)
    def test_holm_rejects_bad(self):
        with self.assertRaises(ValueError): holm_bonferroni({"x":1.2})
    def test_chronological_split(self):
        s=chronological_split(10,6,2); self.assertEqual(s["evaluation_indices"],[6,7]); self.assertEqual(s["unused_future_indices"],[8,9])
    def test_rolling_origin(self):
        f=rolling_origin_folds(11,5,3); self.assertEqual(f[0]["test_indices"],[5,6,7]); self.assertEqual(f[1]["test_indices"],[8,9,10])
    def test_invalid_split(self):
        with self.assertRaises(ValueError): chronological_split(5,6)
    def test_gates_block(self):
        rows=[{"p_alt":2*P0,"p_null":P0} for _ in range(120)]
        r=evaluate_log_scores(rows,protocol_status="DRAFT",family_p_values={"p":.001},primary_test_id="p",gates={})
        self.assertEqual(r["state"],"BLOCKED_PROVENANCE")
    def test_custody_failure_blocks(self):
        rows=[{"p_alt":2*P0,"p_null":P0} for _ in range(120)]
        g={"preregistered":True,"untouched_prospective":True,"independent_custody":False,"data_integrity_pass":True,"two_prospective_outputs":True}
        r=evaluate_log_scores(rows,protocol_status="PREREGISTERED",family_p_values={"p":.001},primary_test_id="p",gates=g)
        self.assertEqual(r["state"],"BLOCKED_PROVENANCE")
    def test_all_gates_only_yield_candidate(self):
        rows=[{"p_alt":2*P0,"p_null":P0} for _ in range(120)]
        g={k:True for k in REQUIRED_EDGE_GATES}
        r=evaluate_log_scores(rows,protocol_status="PREREGISTERED",family_p_values={"p":.001},primary_test_id="p",gates=g,exact5_max_log_e_value=math.log(20))
        self.assertEqual(r["state"],"STATISTICAL_SIGNAL_REQUIRES_EXTERNAL_AUDIT")
        self.assertFalse(r["edge_certified"]); self.assertFalse(r["promotion_authorized"])
    def test_bad_probability(self):
        with self.assertRaises(ValueError): evaluate_log_scores([{"p_alt":0,"p_null":P0}],protocol_status="DRAFT",family_p_values={"p":.5},primary_test_id="p",gates={})
    def test_primary_family_required(self):
        with self.assertRaises(ValueError): evaluate_log_scores([{"p_alt":2*P0,"p_null":P0}],protocol_status="DRAFT",family_p_values={"x":.5},primary_test_id="p",gates={})
    def test_null_must_be_exact_uniform_five_of_28(self):
        with self.assertRaisesRegex(ValueError, "1_over_98280"):
            evaluate_log_scores([{"p_alt":2*P0,"p_null":.2}],protocol_status="DRAFT",family_p_values={"p":.5},primary_test_id="p",gates={})
    def test_exact5_anytime_evalue_is_mandatory_for_candidate(self):
        rows=[{"p_alt":2*P0,"p_null":P0} for _ in range(120)]
        gates={k:True for k in REQUIRED_EDGE_GATES}
        result=evaluate_log_scores(rows,protocol_status="PREREGISTERED",family_p_values={"p":.001},primary_test_id="p",gates=gates)
        self.assertEqual(result["state"],"NO_EDGE_EVIDENCE")
        self.assertIn("exact5_anytime_e_value_ge_20",result["gates_failed"])
    def test_sign_fraction_is_descriptive_not_inferential(self):
        rows=[{"p_alt":2*P0,"p_null":P0} for _ in range(120)]
        result=evaluate_log_scores(rows,protocol_status="DRAFT",family_p_values={"p":.5},primary_test_id="p",gates={})
        self.assertNotIn("sign_test_one_sided_p",result)
        self.assertEqual(result["multiplicity"]["family_size"],1)
    def test_null_plus_one(self):
        r=benchmark_nulls(2,{"m":[0,.5,1]}); self.assertAlmostEqual(r["nulls"]["m"]["empirical_p"],.25)
    def test_null_empty_rejected(self):
        with self.assertRaises(ValueError): benchmark_nulls(1,{"empty":[]})
    def test_diversity_warning(self):
        fs=[{"lens":x,"representation":x,"observables":["u","v"]} for x in "abc"]
        r=frame_diversity(fs); self.assertEqual(r["mean_observable_jaccard"],1); self.assertTrue(r["low_diversity_warning"])
    def test_manifest_tamper(self):
        with tempfile.TemporaryDirectory() as d:
            b=Path(d); p=b/"x.csv"; p.write_text("a,b\n1,2\n"); m=create_manifest([p],b)
            self.assertEqual(verify_manifest(m,b)["state"],"PASS"); p.write_text("changed")
            self.assertEqual(verify_manifest(m,b)["state"],"BLOCKED")
    def test_catalog_generates_unique(self):
        fs=generate_frames("chispazo",12); self.assertEqual(len(fs),12); self.assertEqual(len({f.frame_id for f in fs}),12)
    def test_protocol_missing(self):
        self.assertTrue(any(x.startswith("missing:") for x in validate_protocol({})))
    def test_meta_adaptation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"ledger.jsonl"
            for i,t in enumerate(("protocol_sealed","outcome_access","metric_changed")):
                append_event(p,{"event_id":str(i),"timestamp_utc":f"2026-01-01T00:0{i}:00Z","event_type":t,"frame_id":"f","details":{}})
            r=audit_search_path(p); self.assertEqual(r["state"],"REVIEW_REQUIRED")
            self.assertTrue(any(x["type"]=="post_outcome_adaptation" for x in r["findings"]))
    def test_meta_outcome_before_prereg(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"l.jsonl"; append_event(p,{"event_id":"1","timestamp_utc":"2026-01-01T00:00:00Z","event_type":"outcome_access","frame_id":"f","details":{}})
            self.assertEqual(audit_search_path(p)["state"],"BLOCKED")
    def test_protocol_fields(self):
        self.assertTrue(any(x.startswith("missing:") for x in validate_protocol({})))
    def test_null_controls(self):
        rows=[[1,2,3,4,5],[6,7,8,9,10]]
        self.assertEqual(shuffled_rows(rows,9),shuffled_rows(rows,9))
        self.assertEqual([set(x) for x in within_row_permutation(rows,9)],[set(x) for x in rows])
        self.assertTrue(all(len(x)==5 for x in independent_uniform_draws(10,seed=4)))
    def test_registry_append_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"r.jsonl"; f=generate_frames("x",3)
            self.assertEqual(append_frames(p,f),3); self.assertEqual(append_frames(p,f),0); self.assertEqual(audit_registry(p)["state"],"PASS")
    def test_no_auto_promotion(self):
        self.assertFalse(critique_bundle(generate_frames("x",1)[0])["meta_observer"]["promotion_authorized"])
    def test_count_bounds(self):
        with self.assertRaises(ValueError): generate_frames("x",0)
        with self.assertRaises(ValueError): generate_frames("x",1001)
    def test_registry_duplicate_detected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"r.jsonl"; row=generate_frames("x",1)[0].to_dict()
            p.write_text(json.dumps(row)+"\n"+json.dumps(row)+"\n")
            self.assertEqual(audit_registry(p)["state"],"BLOCKED")

    def test_ledger_hash_chain_detects_interior_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"ledger.jsonl"
            for i in range(3):
                append_event(p,{"event_id":str(i),"timestamp_utc":f"2026-01-01T00:0{i}:00Z","event_type":"search","frame_id":"f","details":{"i":i}})
            lines=p.read_text().splitlines()
            p.write_text(chr(10).join([lines[0], lines[2], ""]))
            from origen.search_ledger import audit_ledger
            self.assertEqual(audit_ledger(p)["state"],"BLOCKED")
            self.assertTrue(any(e["error"]=="chain_link_mismatch" for e in audit_ledger(p)["errors"]))

    def test_ledger_rejects_duplicate_event_id(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"ledger.jsonl"
            event={"event_id":"same","timestamp_utc":"2026-01-01T00:00:00Z","event_type":"search","frame_id":"f","details":{}}
            append_event(p,event)
            with self.assertRaises(ValueError): append_event(p,event)

if __name__=="__main__": unittest.main()
