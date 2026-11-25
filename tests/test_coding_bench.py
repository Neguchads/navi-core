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
        self.assertEqual(len(bench.TESTS),12)
