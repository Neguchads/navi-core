import pathlib
import shutil
import tempfile
import unittest
from navi_core import cli

class ScopedProfileTests(unittest.TestCase):
    def fixture(self,profile,directory,filename,content):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root=pathlib.Path(tmp.name)/"fixture";root.mkdir()
        target=root/directory;target.mkdir(parents=True)
        (target/filename).write_text(content,encoding="utf-8")
        if profile=="javascript-tooling":(root/"package.json").write_text('{"type":"module"}')
        cli.init(root,profile,"public")
        p=root/".navi/project.toml"
        p.write_text(p.read_text().replace("[verification]","[verification]\ntest_dir = "+repr(directory)),encoding="utf-8")
        return root
    def test_python_scope(self):
        root=self.fixture("python-tooling","integrations/portfolio","test_portfolio.py","import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n")
        self.assertEqual(cli.verify(root,True)["status"],"passed")
    def test_traversal_rejected(self):
        root=self.fixture("python-tooling","tests","test_a.py","")
        p=root/".navi/project.toml";p.write_text(p.read_text().replace("'tests'","'../tests'"))
        with self.assertRaises(cli.NaviError):cli.plan(root)
    def test_non_test_profile_rejects_scope(self):
        root=self.fixture("documentation","tests","test_a.py","")
        (root/"README.md").write_text("# fixture")
        with self.assertRaises(cli.NaviError):cli.plan(root)
    @unittest.skipUnless(shutil.which("node"),"Node required")
    def test_node_pass_and_failure(self):
        root=self.fixture("javascript-tooling","tests/brand","sample.mjs","import test from 'node:test'; import assert from 'node:assert/strict'; test('pass',()=>assert.equal(1,1));")
        self.assertEqual(cli.verify(root,True)["status"],"passed")
        (root/"tests/brand/sample.mjs").write_text("import test from 'node:test'; test('fail',()=>{throw Error('intentional')});")
        with self.assertRaises(cli.NaviError):cli.verify(root,True)
    @unittest.skipUnless(shutil.which("node"),"Node required")
    def test_node_all_skipped(self):
        root=self.fixture("javascript-tooling","tests","sample.mjs","import test from 'node:test'; test.skip('skipped',()=>{});")
        with self.assertRaises(cli.NaviError):cli.verify(root,True)
    def test_missing_scope(self):
        root=self.fixture("python-tooling","tests","test_a.py","")
        (root/"tests/test_a.py").unlink()
        with self.assertRaises(cli.NaviError):cli.plan(root)
