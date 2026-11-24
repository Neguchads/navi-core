import pathlib
import shutil
import subprocess
import tempfile
import unittest
from navi_core import cli, engineering_proof as p

@unittest.skipUnless(shutil.which("git"),"Git required")
class EngineeringProofTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=pathlib.Path(tmp.name)/"fixture";self.root.mkdir()
        self.out=pathlib.Path(tmp.name)/"receipt"
        (self.root/"README.md").write_text("# fixture",encoding="utf-8")
        cli.init(self.root,"documentation","private")
        for args in (("init","-q"),("add","."),("-c","user.name=Fixture","-c","user.email=fixture@example.invalid","-c","commit.gpgsign=false","commit","-qm","fixture")):
            subprocess.run(["git","-C",str(self.root),*args],check=True,capture_output=True)
    def test_actual_installed_gate_and_tamper(self):
        self.assertEqual(p.capture(self.root,self.out,60)["status"],"passed")
        self.assertEqual(p.check(self.out)["status"],"passed")
        (self.out/"verification.log").write_text("modified")
        self.assertEqual(p.check(self.out)["status"],"failed")
    def test_dirty_tree_blocked(self):
        (self.root/"README.md").write_text("modified")
        with self.assertRaises(cli.NaviError):p.capture(self.root,self.out)
        self.assertFalse(self.out.exists())
    def test_output_inside_tree_blocked(self):
        with self.assertRaises(cli.NaviError):p.capture(self.root,self.root/"receipt")
    def test_failed_gate_receipt(self):
        (self.root/"README.md").write_text("[missing](absent.md)")
        subprocess.run(["git","-C",str(self.root),"-c","user.name=Fixture","-c","user.email=fixture@example.invalid","-c","commit.gpgsign=false","commit","-qam","broken fixture"],check=True,capture_output=True)
        self.assertEqual(p.capture(self.root,self.out,60)["status"],"failed")
        self.assertEqual(p.check(self.out)["status"],"failed")
