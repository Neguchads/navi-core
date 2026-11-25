import pathlib
import tempfile
import unittest
from unittest.mock import patch
from navi_core import providers, governance, cli

class FoundationTests(unittest.TestCase):
    def test_provider_plan_no_io(self):
        with patch("navi_core.providers._request") as call:
            self.assertEqual(providers.plan()["status"],"planned")
            call.assert_not_called()
    def test_provider_cloud_and_budget_rejected(self):
        for model in ("model:cloud","https://example.org",""):
            with self.assertRaises(cli.NaviError):providers.plan(model)
        with self.assertRaises(cli.NaviError):providers.plan(max_output=0)
    def test_provider_requires_explicit_case(self):
        with self.assertRaises(cli.NaviError):providers.run("local:9b",None)
    def test_provider_mocked_response(self):
        response={"done":True,"model":"local:9b","eval_count":20,"prompt_eval_count":90,
                  "response":'{"order":["lint","types","build","test","release-review"]}'}
        with patch("navi_core.providers._request",return_value=response) as req:
            result=providers.run("local:9b","BENCH-DAG-001")
            self.assertEqual(result["status"],"passed")
            self.assertEqual(result["metrics"]["output_tokens"],20)
            self.assertEqual(req.call_args.args[0]["options"]["num_predict"],512)
            self.assertFalse(result["provider"]["hard_deadline"])
    def test_provider_overbudget(self):
        with patch("navi_core.providers._request",return_value={"done":True,"model":"local:9b","response":"{}","eval_count":513,"prompt_eval_count":1}):
            with self.assertRaises(cli.NaviError):providers.run("local:9b","BENCH-DAG-001")
    def test_provider_failed_gate(self):
        with patch("navi_core.providers._request",return_value={"done":True,"model":"local:9b","response":'{"allowed":["r2"],"denied":["r1","r3","r4"]}',"eval_count":10,"prompt_eval_count":50}):
            self.assertEqual(providers.run("local:9b","BENCH-GOVERNANCE-001")["status"],"failed")
    def test_proof_recomputes(self):
        p=governance.proof("BENCH-BUDGET-001",{"admitted":["plan","build","extra"],"remaining":-5},4096)
        self.assertEqual(p["status"],"failed")
        self.assertEqual(len(p["evidence_sha256"]),64)
    def test_public_status_no_private_inputs(self):
        d=governance.public_status()
        self.assertEqual(d["synthetic_reference"],{"passed":4,"total":4})
        self.assertIsNone(d["real_agent_comparison"])
        self.assertIsNone(d["security_certification"])
    def test_preflight_and_rollout_no_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)/"fixture";root.mkdir()
            (root/"README.md").write_text("# fixture",encoding="utf-8")
            cli.init(root,"documentation","private")
            before={p.relative_to(root).as_posix() for p in root.rglob("*")}
            self.assertEqual(governance.preflight(root)["status"],"preflight-only")
            p=governance.rollout(root,"a"*40)
            self.assertEqual(p["status"],"planned")
            self.assertEqual(p["proposed_workflow"]["permissions"],{"contents":"read"})
            self.assertEqual(before,{p.relative_to(root).as_posix() for p in root.rglob("*")})
            with self.assertRaises(cli.NaviError):governance.rollout(root,"main")
