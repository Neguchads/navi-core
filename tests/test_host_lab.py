import json
from pathlib import Path
import tempfile
import unittest
from navi_core import host_lab,cli

class HostLabTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name).resolve()/"lab"
        self.assertEqual(host_lab.create(self.root)["status"],"prepared")
        self.expected=json.loads((self.root/"expected.json").read_text())["hosts"]
    def answer(self,host):
        return {"challenge":self.expected[host]["challenge"],"order":["lint","compile","test"]}
    def test_each_host(self):
        for host in host_lab.HOSTS:
            self.assertEqual(host_lab.check(self.root,host,self.answer(host),"manual-fixture")["status"],"passed")
    def test_cross_host_rejected(self):
        self.assertEqual(host_lab.check(self.root,"claude",self.answer("codex"),"fixture")["status"],"failed")
    def test_wrong_answer(self):
        a=self.answer("codex");a["order"].reverse()
        self.assertEqual(host_lab.check(self.root,"codex",a,"fixture")["status"],"failed")
    def test_changed_workspace(self):
        (self.root/"codex"/"AGENTS.md").write_text("modified")
        self.assertFalse(host_lab.check(self.root,"codex",self.answer("codex"),"fixture")["gates"]["workspace_integrity"])
    def test_refuses_overwrite(self):
        with self.assertRaises(cli.NaviError):host_lab.create(self.root)
    def test_challenge_not_in_prompt(self):
        prompt=(self.root/"PROMPT.txt").read_text()
        self.assertTrue(all(x["challenge"] not in prompt for x in self.expected.values()))

    def test_single_host_lab(self):
        for host in host_lab.HOSTS:
            with self.subTest(host=host):
                root=self.root.parent/("only-"+host)
                self.assertEqual(host_lab.create(root,host)["hosts"],[host])
                expected=json.loads((root/"expected.json").read_text())["hosts"]
                self.assertEqual(list(expected),[host])
                answer={"challenge":expected[host]["challenge"],"order":["lint","compile","test"]}
                self.assertEqual(host_lab.check(root,host,answer,"manual-fixture")["status"],"passed")
                for other in host_lab.HOSTS:
                    self.assertEqual((root/other).exists(),other==host)

    def test_refuses_linked_parent(self):
        real=self.root.parent/"real"
        real.mkdir()
        linked=self.root.parent/"alias"
        try:
            linked.symlink_to(real,target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaises(cli.NaviError):
            host_lab.create(linked/"new","gemini")
        self.assertFalse((real/"new").exists())
