import json
from pathlib import Path
import tempfile
import unittest
from navi_core import assist, cli

class AssistTests(unittest.TestCase):
    def handoff(self,**changes):
        data={"schema_version":1,"objective":"Export CSV","revision":None,"state":"in-progress",
              "completed":[],"blockers":[],"decisions":[],"next_steps":["Run test"],"rollback":"",
              "acceptance":[],"verification":[]}
        data.update(changes)
        return data
    def test_portable_public_packet(self):
        p=assist.packet("game-recomp")
        self.assertEqual(p["profile"],"game-recomp")
        self.assertFalse(p["capabilities"]["private_context_included"])
        self.assertIn("handoff",p["contracts"])
        self.assertIn("P11",assist.render("game-recomp"))
        with self.assertRaises(cli.NaviError):assist.packet("missing")
    def test_in_progress_and_blocked(self):
        self.assertEqual(assist.check_handoff(self.handoff())["status"],"valid")
        self.assertEqual(assist.check_handoff(self.handoff(next_steps=[]))["status"],"review-required")
        self.assertEqual(assist.check_handoff(self.handoff(state="blocked"))["status"],"review-required")
        self.assertEqual(assist.check_handoff(self.handoff(state="blocked",blockers=["missing input"]))["status"],"valid")
    def test_no_false_complete(self):
        self.assertEqual(assist.check_handoff(self.handoff(state="complete"))["status"],"review-required")
        self.assertEqual(assist.check_handoff(self.handoff(state="complete",acceptance=[
            {"criterion":"CSV","status":"passed","evidence":"test output"}]))["status"],"valid")
        self.assertEqual(assist.check_handoff(self.handoff(state="complete",acceptance=[
            {"criterion":"CSV","status":"not-run","evidence":""}]))["status"],"review-required")
        self.assertEqual(assist.check_handoff(self.handoff(verification=[
            {"command":"test","status":"passed","exit_code":1,"evidence":"wrong"}]))["status"],"review-required")
    def test_reject_unknown_private_fields(self):
        with self.assertRaises(cli.NaviError):assist.check_handoff(self.handoff(raw_prompt="not allowed"))

    def test_managed_workflow_refuses_unclear_task(self):
        brief={"schema_version":1,"goal":"","deliverable":"docs","complexity":"nontrivial",
               "acceptance":["documents exist"],"constraints_state":"known","ambiguity":"none",
               "questions":[],"risk":"low","approved":False}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()/"project";root.mkdir()
            self.assertEqual(assist.prepare(root,brief,"documentation")["status"],"clarify")
            self.assertEqual(assist.workflow(root,brief,"scaffold","documentation",apply=True)["status"],"clarify")
            self.assertEqual(list(root.iterdir()),[])
            brief["goal"]="Prepare documentation"
            self.assertEqual(assist.prepare(root,brief,"documentation")["status"],"ready")
            self.assertEqual(assist.workflow(root,brief,"scaffold","documentation",apply=True)["status"],"applied")
            self.assertTrue((root/"docs/HANDOFF.md").is_file())
    def test_complete_cannot_hide_failed_verification(self):
        data=self.handoff(state="complete",acceptance=[{"criterion":"CSV","status":"passed","evidence":"file"}],
                          verification=[{"command":"test","status":"failed","exit_code":1,"evidence":"failure"}])
        self.assertEqual(assist.check_handoff(data)["status"],"review-required")

    def test_cli_portable_packet(self):
        from contextlib import redirect_stdout
        from io import StringIO
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(cli.main(["assist","--profile","documentation"]),0)
        self.assertIn("handoff",json.loads(output.getvalue())["contracts"])
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(cli.main(["assist","--profile","documentation","--format","markdown"]),0)
        self.assertIn("P11",output.getvalue())
