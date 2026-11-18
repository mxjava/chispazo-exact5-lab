import tempfile, unittest
from pathlib import Path
from origen.exact5_modalities import assign_modality, prequential_marginal_diagnostic

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
