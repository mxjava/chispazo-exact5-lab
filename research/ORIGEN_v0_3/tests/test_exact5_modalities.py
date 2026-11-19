import tempfile, unittest
from pathlib import Path
from origen.exact5_modalities import assign_modality, prequential_marginal_diagnostic, _v264_transition_signal, v264_full_mixture_classic_diagnostic

class ModalityTests(unittest.TestCase):
    def test_pre_transition_single_is_classic(self):
        rows=[{"contest":5922,"date":"2017-09-24","numbers":[1,2,3,4,5]}]
        labelled,summary=assign_modality(rows)
        self.assertEqual(labelled[0]["draw_type"],"CLASSIC")
        self.assertEqual(summary["pre_transition_single_draw_dates"],1)

    def test_post_transition_odd_three_even_classic(self):
        rows=[
            {"contest":5923,"date":"2017-09-25","numbers":[1,2,3,4,5]},
            {"contest":5924,"date":"2017-09-25","numbers":[2,3,4,5,6]},
        ]
        labelled,summary=assign_modality(rows)
        self.assertEqual([r["draw_type"] for r in labelled],["DE_LAS_TRES","CLASSIC"])
        self.assertEqual(summary["post_transition_complete_odd_even_days"],1)

    def test_reject_bad_post_transition_pair(self):
        rows=[
            {"contest":5923,"date":"2017-09-25","numbers":[1,2,3,4,5]},
            {"contest":5925,"date":"2017-09-25","numbers":[2,3,4,5,6]},
        ]
        with self.assertRaises(ValueError): assign_modality(rows)

    def test_reject_pre_transition_multiple_draws(self):
        rows=[
            {"contest":5921,"date":"2017-09-24","numbers":[1,2,3,4,5]},
            {"contest":5922,"date":"2017-09-24","numbers":[2,3,4,5,6]},
        ]
        with self.assertRaises(ValueError): assign_modality(rows)

    def test_v264_transition_excludes_current_context_row(self):
        draws=[
            {"contest":1,"numbers":[1,2,3,4,5]},
            {"contest":2,"numbers":[1,6,7,8,9]},
            {"contest":3,"numbers":[1,10,11,12,13]},
        ]
        signal=_v264_transition_signal(draws,2,window=800)
        # At t=2, range(1, t-1) is empty; no current-context leakage.
        self.assertEqual(sum(signal),0.0)

    def test_full_v264_mixture_uses_calendar_aligned_warmup_and_divergent_streams(self):
        rows=[]
        for i in range(8):
            day=f"2020-01-{i+1:02d}"
            odd=5923+2*i
            de_tres=[((i*3+j*2) % 28)+1 for j in range(5)]
            classic=[((i*5+j*3+1) % 28)+1 for j in range(5)]
            rows.append({"contest":odd,"date":day,"numbers":de_tres,"draw_type":"DE_LAS_TRES"})
            rows.append({"contest":odd+1,"date":day,"numbers":classic,"draw_type":"CLASSIC"})
        result=v264_full_mixture_classic_diagnostic(rows,warmup=2)
        self.assertEqual(result["classic_only"]["n"],6)
        self.assertEqual(result["pooled_stream_scored_on_same_classic_targets"]["n"],6)
        self.assertTrue(result["target_alignment_verified"])
        self.assertEqual(result["first_target_contest"],5928)
        self.assertTrue(result["posterior_prewarmed_on_all_pre_target_observations"])
        self.assertEqual(result["classic_stream_de_las_tres_updates_total"],0)
        self.assertEqual(result["pooled_stream_de_las_tres_updates_total"],3)
        self.assertEqual(result["pooled_stream_de_las_tres_updates_before_first_target"],2)
        self.assertGreater(result["posterior_trace_max_l1_difference_on_classic_targets"],0.0)
        self.assertGreater(result["posterior_trace_nonzero_difference_targets"],0)
        self.assertNotEqual(
            result["classic_only"]["cumulative_log_lift"],
            result["pooled_stream_scored_on_same_classic_targets"]["cumulative_log_lift"],
        )

    def test_fixed_prequential_output_is_not_evalue(self):
        rows=[]
        for i in range(802):
            day=f"2020-01-{(i%28)+1:02d}"
            odd=5923+2*i
            rows.append({"contest":odd,"date":day,"numbers":[1,2,3,4,5],"draw_type":"DE_LAS_TRES"})
            rows.append({"contest":odd+1,"date":day,"numbers":[1,2,3,4,5],"draw_type":"CLASSIC"})
        result=prequential_marginal_diagnostic(rows,warmup_classic=800,alpha=200)
        self.assertEqual(result["classic_only"]["n"],2)
        self.assertIn("not an anytime-valid e-value",result["warning"])

if __name__=="__main__": unittest.main()
