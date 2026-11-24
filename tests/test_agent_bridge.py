import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
from navi_core import cli, agent_bridge as bridge

class AgentBridgeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)/"fixture"
        self.root.mkdir()
        (self.root/"README.md").write_text("# test", encoding="utf-8")
        cli.init(self.root,"documentation","private")

    def test_plan_no_writes(self):
        result = bridge.adapters(self.root)
        self.assertEqual(result["status"],"planned")
        self.assertEqual(len(result["files"]),3)
        self.assertFalse((self.root/"AGENTS.md").exists())
        self.assertFalse((self.root/".github").exists())

    def test_create_and_check_all(self):
        result = bridge.adapters(self.root,mode="apply")
        self.assertEqual(len(result["created"]),3)
        self.assertEqual(bridge.adapters(self.root,mode="check")["status"],"current")
        self.assertEqual(bridge.adapters(self.root,mode="apply")["created"],[])

    def test_existing_conflict_blocks_every_write(self):
        path = self.root/"CLAUDE.md"
        path.write_text("private local instructions",encoding="utf-8")
        result=bridge.adapters(self.root,mode="apply")
        self.assertEqual(result["status"],"conflict")
        self.assertNotIn("private local instructions",json.dumps(result))
        self.assertEqual(path.read_text(encoding="utf-8"),"private local instructions")
        self.assertFalse((self.root/"AGENTS.md").exists())

    def test_check_missing(self):
        self.assertEqual(bridge.adapters(self.root,mode="check")["status"],"drift")

    def test_host_selection(self):
        result = bridge.adapters(self.root,host="copilot",mode="apply")
        self.assertEqual(result["created"],[".github/copilot-instructions.md"])
        self.assertFalse((self.root/"AGENTS.md").exists())

    def test_manual_edit_detected(self):
        bridge.adapters(self.root,mode="apply")
        (self.root/"AGENTS.md").write_text("changed",encoding="utf-8")
        self.assertEqual(bridge.adapters(self.root,mode="check")["status"],"conflict")

    def test_symlink_guard(self):
        outside=self.root.parent/"outside"
        outside.mkdir()
        try:
            (self.root/".github").symlink_to(outside,target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaises(cli.NaviError):
            bridge.adapters(self.root,mode="apply")
        self.assertFalse((outside/"copilot-instructions.md").exists())

    def test_registry_metadata_only(self):
        data=bridge.list_skills("codex","verification")
        self.assertEqual(data["status"],"metadata-only")
        self.assertEqual(len(data["skills"]),3)
        self.assertTrue(all(s["handler"] is None and s["contract"]["status"]=="candidate" for s in data["skills"]))

    def test_deterministic_policy(self):
        first=bridge.render("codex","documentation")
        self.assertEqual(first,bridge.render("codex","documentation"))
        self.assertNotEqual(first,bridge.render("claude","documentation"))
        self.assertIn(b"sha256:",first)

    def test_cli_check_exit(self):
        with patch("builtins.print"):
            self.assertEqual(cli.main(["agents","--root",str(self.root),"--mode","check"]),1)
            self.assertEqual(cli.main(["agents","--root",str(self.root),"--mode","apply"]),0)
            self.assertEqual(cli.main(["agents","--root",str(self.root),"--mode","check"]),0)
