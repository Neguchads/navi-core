import importlib.util
import pathlib
import unittest
from navi_core.cli import NaviError
p=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"coding_bench.py"
spec=importlib.util.spec_from_file_location("coding_bench",p)
bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench)
class CodingBenchTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(bench.validate_source(bench.CASE["source"]),bench.CASE["source"])
    def test_rejects_io(self):
        for code in ("import os\ndef page(items,offset,limit): return []","def page(items,offset,limit): return open('x')","def page(items,offset,limit): return items.__class__","def page(items,offset,limit): return eval('1')"):
            with self.assertRaises(NaviError):bench.validate_source(code)
    def test_rejects_decorator_and_default(self):
        for code in ("@len\ndef page(items,offset,limit): return []","def page(items,offset,limit=1): return []","def page(items,offset,limit):\n def inner(): return 1\n return []"):
            with self.assertRaises(NaviError):bench.validate_source(code)
    def test_expected_not_prompt(self):
        self.assertNotIn("tests",bench.CASE)
        self.assertEqual(len(bench.CASE["examples"]),3)
        self.assertNotIn(bench.TESTS[4][0],[x["input"] for x in bench.CASE["examples"]])
        self.assertEqual(len(bench.TESTS),12)

    def test_development_feedback_only(self):
        from unittest.mock import patch
        good="def page(items, offset, limit): return {'items': [], 'next_offset': None}"
        good_result={"status":"passed","passed":12,"total":12}
        bad_result={"status":"failed","passed":0,"total":12}
        dev_result={"status":"failed","failed_case_indices":[0],"reason":None}
        with patch.object(bench,"verify",side_effect=[good_result,bad_result,good_result,good_result,dev_result,good_result]) as verify, patch.object(bench,"request",return_value=(good,{"input_tokens":1,"output_tokens":1})) as request:
            report=bench.run("sha256:"+"a"*64,1)
            self.assertEqual(report["status"],"passed")
            self.assertEqual(request.call_count,3)
            self.assertEqual(request.call_args.args[3]["failed_example_indices"],[0])
            self.assertEqual(verify.call_args_list[4].args[2],[(x["input"],x["output"]) for x in bench.CASE["examples"]])
    def test_adaptive_skips_review_when_development_passes(self):
        from unittest.mock import patch
        source=bench.CASE["source"]
        ok={"status":"passed","passed":12,"total":12}
        with patch.object(bench,"verify",side_effect=[ok,{"status":"failed"},ok,ok,ok,ok]), patch.object(bench,"request",return_value=(source,{"input_tokens":1,"output_tokens":1})) as request:
            report=bench.run("sha256:"+"a"*64,1)
            self.assertEqual(report["status"],"passed")
            self.assertEqual(request.call_count,2)
