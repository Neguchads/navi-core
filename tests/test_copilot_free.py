import datetime
import unittest
from navi_core import copilot_free as c, agent_bridge, cli

class CopilotFreeTests(unittest.TestCase):
    def options(self,**changes):
        args=dict(kind="small-fix",risk="low",visibility="public",files=2,lines=80,
                  used=65,estimate=5,checked_on=datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
                  paid_usage_blocked=True)
        args.update(changes)
        return args
    def test_at_budget_boundary(self):
        self.assertEqual(c.plan(**self.options())["provider"],"copilot-free")
    def test_exceeds_budget(self):
        for args in (dict(used=66),dict(estimate=6),dict(estimate=0),dict(used=100)):
            self.assertEqual(c.plan(**self.options(**args))["provider"],"local-review")
    def test_unknown_or_stale_usage(self):
        for args in (dict(used=None),dict(estimate=None),dict(checked_on="2000-01-01"),dict(paid_usage_blocked=False)):
            self.assertEqual(c.plan(**self.options(**args))["provider"],"local-review")
    def test_size_and_complexity(self):
        for args in (dict(files=3),dict(lines=81),dict(kind="complex")):
            self.assertEqual(c.plan(**self.options(**args))["provider"],"human-review")
    def test_privacy(self):
        for visibility in ("private","internal","unknown"):
            self.assertEqual(c.plan(**self.options(visibility=visibility))["provider"],"local-review")
    def test_risk(self):
        for risk in ("medium","high","critical"):
            self.assertEqual(c.plan(**self.options(risk=risk))["provider"],"human-review")
        self.assertEqual(c.plan(**self.options(kind="release"))["provider"],"human-review")
    def test_deterministic_first(self):
        self.assertEqual(c.plan(**self.options(kind="lint",used=None))["provider"],"deterministic")
    def test_invalid(self):
        for args in (dict(files=-1),dict(lines=True),dict(used=101),dict(estimate=-1)):
            with self.assertRaises(cli.NaviError):c.plan(**self.options(**args))
    def test_compact_adapter_matches(self):
        self.assertIn(c.INSTRUCTIONS.encode("utf-8"),agent_bridge.render("copilot","python-tooling"))
        self.assertIn(b"Provider independence",agent_bridge.render("copilot","python-tooling"))
        self.assertNotEqual(agent_bridge.render("codex","python-tooling"),c.INSTRUCTIONS.encode("utf-8"))

    def test_architecture_does_not_switch_provider(self):
        self.assertEqual(c.plan(**self.options(kind="architecture"))["provider"],"human-review")
