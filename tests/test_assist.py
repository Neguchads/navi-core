import json
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
