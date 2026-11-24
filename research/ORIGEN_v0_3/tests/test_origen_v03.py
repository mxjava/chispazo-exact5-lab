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
    def test_holm_rejects_boolean_p_values(self):
        for value in (False, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "invalid_p_value"):
                    holm_bonferroni({"boolean": value})

    def test_holm_rejects_non_string_hypothesis_ids(self):
        with self.assertRaisesRegex(ValueError, "invalid_p_value"):
            holm_bonferroni({1: 0.01})

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
    def test_boolean_probabilities_are_not_numeric_probabilities(self):
        for field, value in (("p_alt", True), ("p_alt", False), ("p_null", True), ("p_null", False)):
            with self.subTest(field=field, value=value):
                row = {"p_alt": 2 * P0, "p_null": P0}
                row[field] = value
                with self.assertRaisesRegex(ValueError, "must_be_finite"):
                    evaluate_log_scores(
                        [row], protocol_status="DRAFT",
                        family_p_values={"p": 0.5}, primary_test_id="p", gates={}
                    )

    def test_boolean_holm_p_value_cannot_manufacture_statistical_candidate(self):
        rows = [{"p_alt": 2 * P0, "p_null": P0} for _ in range(120)]
        gates = {key: True for key in REQUIRED_EDGE_GATES}
        with self.assertRaisesRegex(ValueError, "invalid_p_value"):
            evaluate_log_scores(
                rows, protocol_status="PREREGISTERED",
                family_p_values={"primary": False}, primary_test_id="primary",
                gates=gates, exact5_max_log_e_value=math.log(20)
            )

    def test_observation_dict_subclass_is_rejected(self):
        class SpoofedObservation(dict):
            pass

        with self.assertRaisesRegex(ValueError, "exact_dict"):
            evaluate_log_scores(
                [SpoofedObservation(p_alt=2 * P0, p_null=P0)],
                protocol_status="DRAFT", family_p_values={"p": 0.5},
                primary_test_id="p", gates={}
            )

    def test_gate_dict_subclass_is_rejected(self):
        class SpoofedGates(dict):
            def get(self, key, default=None):
                return True

        with self.assertRaisesRegex(ValueError, "exact_dict"):
            evaluate_log_scores(
                [{"p_alt": 2 * P0, "p_null": P0}],
                protocol_status="DRAFT", family_p_values={"p": 0.5},
                primary_test_id="p", gates=SpoofedGates()
            )

    def test_min_observations_rejects_comparison_overriding_int_subclass(self):
        class SpoofedMinimum(int):
            def __lt__(self, other):
                return False

        with self.assertRaisesRegex(ValueError, "positive_integer"):
            evaluate_log_scores(
                [{"p_alt": 2 * P0, "p_null": P0}],
                protocol_status="PREREGISTERED",
                family_p_values={"primary": 0.001},
                primary_test_id="primary",
                gates={key: True for key in REQUIRED_EDGE_GATES},
                exact5_max_log_e_value=math.log(20),
                min_observations=SpoofedMinimum(0),
            )

    def test_anytime_evalue_rejects_comparison_overriding_float_subclass(self):
        class SpoofedEValue(float):
            def __ge__(self, other):
                return True

        rows = [{"p_alt": 2 * P0, "p_null": P0} for _ in range(120)]
        result = evaluate_log_scores(
            rows,
            protocol_status="PREREGISTERED",
            family_p_values={"primary": 0.001},
            primary_test_id="primary",
            gates={key: True for key in REQUIRED_EDGE_GATES},
            exact5_max_log_e_value=SpoofedEValue(0.0),
        )
        self.assertFalse(result["exact5_threshold_20_crossed"])
        self.assertIn("exact5_anytime_e_value_ge_20", result["gates_failed"])
        self.assertEqual(result["state"], "NO_EDGE_EVIDENCE")

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


    def test_ledger_rejects_non_finite_numbers_on_append(self):
        from origen.search_ledger import append_event
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                event = {
                    "event_id": "nonfinite",
                    "timestamp_utc": "2026-01-01T00:00:00Z",
                    "event_type": "search",
                    "frame_id": "f",
                    "details": {"score": value},
                }
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaisesRegex(ValueError, "non_finite_number"):
                        append_event(Path(directory) / "ledger.jsonl", event)

    def test_ledger_rejects_non_exact_event_dict(self):
        class SpoofedEvent(dict):
            pass

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(TypeError, "exact_builtin_dict"):
                append_event(
                    Path(directory) / "ledger.jsonl",
                    SpoofedEvent(
                        event_id="spoofed",
                        timestamp_utc="2026-01-01T00:00:00Z",
                        event_type="search",
                        frame_id="f",
                        details={},
                    ),
                )

    def test_ledger_audit_rejects_duplicate_json_keys(self):
        from origen.search_ledger import audit_ledger
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_event(path, {
                "event_id": "duplicate-key",
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "event_type": "search",
                "frame_id": "f",
                "details": {},
            })
            line = path.read_text(encoding="utf-8").strip()
            needle = '"event_id":"duplicate-key"'
            self.assertIn(needle, line)
            path.write_text(
                line.replace(needle, needle + ',"event_id":"duplicate-key"', 1) + "\n",
                encoding="utf-8",
            )
            result = audit_ledger(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                "duplicate_json_key" in item.get("detail", "")
                for item in result["errors"]
            ))

    def test_ledger_audit_rejects_non_finite_json_constant_even_with_matching_hashes(self):
        import hashlib
        from origen.search_ledger import GENESIS, audit_ledger
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            event = {
                "event_id": "nan-event",
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "event_type": "search",
                "frame_id": "f",
                "details": {"score": float("nan")},
            }
            event_payload = json.dumps(
                event, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
            event_digest = hashlib.sha256(event_payload.encode("utf-8")).hexdigest()
            chain_digest = hashlib.sha256(
                (GENESIS + event_digest).encode("ascii")
            ).hexdigest()
            record = {
                "event": event,
                "event_sha256": event_digest,
                "previous_chain_sha256": GENESIS,
                "chain_sha256": chain_digest,
                "ledger_schema": "ORIGEN_CHAIN_V1",
            }
            path.write_text(
                json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            result = audit_ledger(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                "non_finite_json_constant" in item.get("detail", "")
                for item in result["errors"]
            ))

    def test_ledger_audit_rejects_noncanonical_record_serialization(self):
        from origen.search_ledger import audit_ledger
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_event(path, {
                "event_id": "noncanonical",
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "event_type": "search",
                "frame_id": "f",
                "details": {},
            })
            line = path.read_text(encoding="utf-8").strip()
            path.write_text(" " + line + "\n", encoding="utf-8")
            result = audit_ledger(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                item.get("detail") == "noncanonical_json_record"
                for item in result["errors"]
            ))

    def test_ledger_audit_rejects_unterminated_final_record_before_append(self):
        from origen.search_ledger import audit_ledger
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_event(path, {
                "event_id": "unterminated",
                "timestamp_utc": "2026-01-01T00:00:00Z",
                "event_type": "search",
                "frame_id": "f",
                "details": {},
            })
            path.write_text(path.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")
            result = audit_ledger(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                item["error"] == "unterminated_final_record"
                for item in result["errors"]
            ))
            with self.assertRaisesRegex(ValueError, "invalid_or_legacy_ledger"):
                append_event(path, {
                    "event_id": "next",
                    "timestamp_utc": "2026-01-01T00:01:00Z",
                    "event_type": "search",
                    "frame_id": "f",
                    "details": {},
                })


    def test_meta_audit_mixed_naive_and_aware_timestamps_blocks_without_crashing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_event(path, {
                "event_id": "prereg-naive",
                "timestamp_utc": "2026-01-01T00:00:00",
                "event_type": "protocol_sealed",
                "frame_id": "f",
                "details": {},
            })
            append_event(path, {
                "event_id": "access-aware",
                "timestamp_utc": "2026-01-01T00:01:00Z",
                "event_type": "outcome_access",
                "frame_id": "f",
                "details": {},
            })
            result = audit_search_path(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                item["type"] == "timestamp_without_timezone"
                for item in result["findings"]
            ))

    def test_meta_audit_rejects_unknown_negative_zero_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_event(path, {
                "event_id": "unknown-offset",
                "timestamp_utc": "2026-01-01T00:00:00-00:00",
                "event_type": "protocol_sealed",
                "frame_id": "f",
                "details": {},
            })
            result = audit_search_path(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                item["type"] == "timestamp_unknown_offset"
                for item in result["findings"]
            ))

    def test_meta_audit_rejects_non_utc_offset_in_utc_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            append_event(path, {
                "event_id": "local-offset",
                "timestamp_utc": "2026-01-01T01:00:00+01:00",
                "event_type": "protocol_sealed",
                "frame_id": "f",
                "details": {},
            })
            result = audit_search_path(path)
            self.assertEqual(result["state"], "BLOCKED")
            self.assertTrue(any(
                item["type"] == "timestamp_not_utc"
                for item in result["findings"]
            ))

if __name__=="__main__": unittest.main()
