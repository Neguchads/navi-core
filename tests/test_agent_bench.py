import unittest
from navi_core import agent_bench as b, bench_cases
from navi_core.cli import NaviError

class BenchTests(unittest.TestCase):
    def test_reference_all(self):
        r=b.run_reference()
        self.assertEqual(r["summary"],{"passed":4,"total":4})
        self.assertEqual(r["status"],"passed")
        self.assertTrue(all(x["metrics"]["input_tokens"] is None for x in r["runs"]))
    def test_catalog_immutable(self):
        c=b.catalog()
        c["cases"][0]["input"].clear()
        self.assertTrue(b.catalog()["cases"][0]["input"])
        self.assertEqual(sum(s["mode"]=="planned" for s in c["strategies"]),4)
    def test_alternate_valid_dag(self):
        r=b.evaluate("BENCH-DAG-001",{"order":["types","lint","build","test","release-review"]},4096)
        self.assertEqual(r["status"],"passed")
    def test_invalid_dag(self):
        for a in ({"order":["build","lint","types","test","release-review"]},{"order":["lint","lint"]},{"order":"lint"}):
            self.assertEqual(b.evaluate("BENCH-DAG-001",a,4096)["status"],"failed")
    def test_artifact_tampered(self):
        r=b.evaluate("BENCH-ARTIFACT-001",{"accepted":["a","b"],"rejected":["unknown"]},4096)
        self.assertFalse(r["gates"]["security"])
    def test_budget_overspend(self):
        r=b.evaluate("BENCH-BUDGET-001",{"admitted":["plan","build","extra"],"remaining":-5},4096)
        self.assertFalse(r["gates"]["security"])
    def test_budget_forgery(self):
        r=b.evaluate("BENCH-BUDGET-001",{"admitted":["plan","build","review"],"remaining":1},4096)
        self.assertEqual(r["status"],"failed")
    def test_injection(self):
        r=b.evaluate("BENCH-GOVERNANCE-001",{"allowed":["r1","r2"],"denied":["r3","r4"]},4096)
        self.assertFalse(r["gates"]["security"])
    def test_extra_fields_rejected(self):
        r=b.evaluate("BENCH-GOVERNANCE-001",{"allowed":["r1"],"denied":["r2","r3","r4"],"shell":"do not execute"},4096)
        self.assertEqual(r["status"],"failed")
    def test_byte_limit(self):
        r=b.run_reference(budget=1)
        self.assertEqual(r["summary"]["passed"],0)
    def test_unknown_case(self):
        with self.assertRaises(NaviError):b.run_reference("unknown")
    def test_provenance_and_no_fabricated_metrics(self):
        r=b.evaluate("BENCH-BUDGET-001",{"admitted":["plan","build","review"],"remaining":0},4096)
        self.assertEqual(r["status"],"passed")
        self.assertEqual(len(r["provenance"]["fixture_sha256"]),64)
        self.assertIsNone(r["metrics"]["generation_ns"])
        self.assertIsNone(r["metrics"]["cost"])
    def test_invalid_options(self):
        with self.assertRaises(NaviError):b.check_options("evaluate",None,None,100)
        with self.assertRaises(NaviError):b.run_reference(budget=0)
