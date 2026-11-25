import json
import unittest
from unittest.mock import patch
from navi_core import paired_bench as p, agent_bench, bench_cases, cli

MODEL="local:9b"
CASE="BENCH-DAG-001"
def response(case=CASE,**kw):
    out={"done":True,"model":MODEL,"eval_count":10,"prompt_eval_count":40,
         "response":json.dumps(agent_bench.solve(case,bench_cases.CASES[case]["input"]))}
    out.update(kw);return out

class PairedTests(unittest.TestCase):
    def test_plan_no_transport(self):
        with patch("navi_core.providers._request") as req:
            r=p.run(MODEL)
            self.assertEqual(r["planned_trials"],24)
            self.assertEqual(r["planned_requests"],36)
            req.assert_not_called()
    def test_real_call_contract_and_equal_caps_mocked(self):
        with patch("navi_core.providers._request",return_value=response()) as req:
            r=p.run(MODEL,CASE,2,101,1000,60,execute=True)
            self.assertEqual(r["status"],"passed")
            self.assertEqual(r["paired"]["both_pass"],2)
            self.assertEqual(req.call_count,6)
            self.assertEqual([c.args[0]["options"]["num_predict"] for c in req.call_args_list],[101,50,51,50,51,101])
            self.assertIn("untrusted_draft",json.loads(req.call_args_list[2].args[0]["prompt"]))
    def test_mismatched_model_blocks(self):
        with patch("navi_core.providers._request",return_value=response(model="different:9b")) as req:
            r=p.run(MODEL,CASE,2,execute=True)
            self.assertEqual(r["status"],"blocked")
            self.assertEqual(req.call_count,1)
            self.assertEqual(r["paired"]["complete_pairs"],0)
    def test_input_over_budget_stops(self):
        with patch("navi_core.providers._request",return_value=response(prompt_eval_count=101)) as req:
            r=p.run(MODEL,CASE,2,max_input=100,execute=True)
            self.assertEqual(r["status"],"blocked")
            self.assertEqual(req.call_count,1)
    def test_output_over_budget_stops(self):
        with patch("navi_core.providers._request",return_value=response(eval_count=513)):
            r=p.run(MODEL,CASE,2,execute=True)
            self.assertEqual(r["status"],"blocked")
    def test_duplicate_keys_stop(self):
        with patch("navi_core.providers._request",return_value=response(response='{"order":[],"order":[]}')):
            self.assertEqual(p.run(MODEL,CASE,1,execute=True)["status"],"blocked")
    def test_gate_failure_not_hidden(self):
        with patch("navi_core.providers._request",return_value=response("BENCH-GOVERNANCE-001",response='{"allowed":["r2"],"denied":["r1","r3","r4"]}')) as req:
            r=p.run(MODEL,"BENCH-GOVERNANCE-001",1,execute=True)
            self.assertTrue(r["stopped_early"])
            self.assertFalse(r["runs"][0]["gates"]["security"])
            self.assertEqual(req.call_count,1)
    def test_invalid_options(self):
        for model,kwargs in [("local",{}),(MODEL,{"trials":0}),(MODEL,{"max_output":1}),("cloud:latest",{})]:
            with self.assertRaises(cli.NaviError):p.run(model,**kwargs)
