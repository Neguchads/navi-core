import pathlib
import tempfile
import unittest
from navi_core import cli

class StdlibPilotTests(unittest.TestCase):
    def project(self,text):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=pathlib.Path(tmp.name)/"fixture";root.mkdir()
        (root/"tests").mkdir()
        (root/"tests"/"test_fixture.py").write_text(text,encoding="utf-8")
        cli.init(root,"python-tooling","public")
        return root
    def test_standalone_stdlib_without_packaging(self):
        root=self.project("import unittest\nclass T(unittest.TestCase):\n def test_real(self): self.assertEqual(1,1)\n")
        self.assertEqual(cli.detect(root),["python-tooling"])
        self.assertEqual(cli.verify(root,True)["status"],"passed")
    def test_all_skipped_never_pass(self):
        root=self.project("import unittest\nclass T(unittest.TestCase):\n @unittest.skip('unavailable')\n def test_unavailable(self): pass\n")
        with self.assertRaises(cli.NaviError):cli.verify(root,True)
    def test_failed_test_never_passes(self):
        root=self.project("import unittest\nclass T(unittest.TestCase):\n def test_bad(self): self.fail('negative fixture')\n")
        with self.assertRaises(cli.NaviError):cli.verify(root,True)
