import tempfile
import unittest
from pathlib import Path
from navi_core import intelligence,control_center,runtime,cli

class IntelligenceTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name).resolve();self.root=self.base/"project";self.root.mkdir()
    def write(self,rel,code):
        p=self.root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(code,encoding="utf-8")
    def test_python_cycle_and_rule(self):
        self.write("pkg/__init__.py","")
        self.write("pkg/a.py","from . import b\n")
        self.write("pkg/b.py","import pkg.a\n")
        p={"schema_version":1,"source_root":".","forbid_cycles":True,"forbidden_imports":[{"from":"pkg.a","to":"pkg.b"}]}
        r=intelligence.analyze(self.root,p)
        self.assertEqual(r["status"],"violations")
        self.assertEqual(r["cycles"],[["pkg.a","pkg.b"]])
        self.assertEqual(len(r["violations"]),1)
        self.assertEqual(r["violations"][0]["line"],1)
    def test_read_only_no_code_execution(self):
        self.write("a.py","raise RuntimeError('must never execute')\nimport external\n")
        r=intelligence.analyze(self.root)
        self.assertEqual(r["status"],"inspected")
        self.assertEqual(r["unresolved_import_references"],1)
        self.assertEqual(len(list(self.root.iterdir())),1)
    def test_missing_rules_and_parse_errors(self):
        self.write("a.py","def broken(")
        p={"schema_version":1,"source_root":".","forbid_cycles":False,"forbidden_imports":[{"from":"a","to":"b"}]}
        r=intelligence.analyze(self.root,p)
        self.assertEqual(r["status"],"review-required")
        self.assertEqual(r["parse_or_scope_issues"][0]["reason"],"parse-failed")
        with self.assertRaises(cli.NaviError):intelligence.analyze(self.root,source_root="../")
    def test_src_layout_and_ignored_dirs(self):
        self.write("src/pkg/__init__.py","")
        self.write("src/pkg/a.py","from pkg import b")
        self.write("src/pkg/b.py","")
        self.write("src/.venv/bad.py","invalid python !")
        r=intelligence.analyze(self.root,source_root="src")
        self.assertEqual(r["modules"],3)
        self.assertEqual(r["edges"],1)
    def test_dashboard_metadata_and_escaping(self):
        self.write("README.md","# test")
        store=self.base/"private";store.mkdir()
        runtime.start(self.root,store,"task","none")
        config={"schema_version":1,"projects":[{"root":str(self.root),"profile":"documentation","store":str(store)}]}
        r=control_center.portfolio(config)
        self.assertEqual(r["projects"][0]["sessions"]["awaiting-brief"],1)
        page=control_center.render(r)
        self.assertNotIn(str(self.root),page)
        self.assertNotIn("task",page)
        r["projects"][0]["project"]="<script>alert(1)</script>"
        self.assertNotIn("<script>",control_center.render(r))
        path=self.base/"dashboard.html"
        control_center.save_html(path,r)
        self.assertTrue(path.is_file())
        with self.assertRaises(FileExistsError):control_center.save_html(path,r)
    def test_dashboard_refuses_git_output(self):
        (self.root/".git").mkdir()
        with self.assertRaises(cli.NaviError):control_center.save_html(self.root/"dashboard.html",{"core_version":"x","projects":[],"scope":"test"})
