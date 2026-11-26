import json
import tempfile
import unittest
from pathlib import Path
from navi_core import mastermind as m

class MastermindTests(unittest.TestCase):
    def test_catalog_complete_and_closed(self):
        data = m.catalog()
        self.assertEqual(len(data["entries"]), 167)
        self.assertFalse(data["installable"])
        self.assertTrue(all(not e["approved"] for e in data["entries"]))

    def test_deterministic_zero_agent_plan(self):
        a = m.resolve({"profile": "game-recomp"})
        self.assertEqual(a, m.resolve({"profile": "game-recomp"}))
        self.assertEqual(a["steps"], [])
        self.assertFalse(a["execution_allowed"])
        self.assertIn("morluto/rea", [e["preferred"] for e in a["candidates"]])

    def test_single_local(self):
        a = m.resolve({"mode": "single", "hosts": ["opencode"]})
        self.assertEqual([s["host"] for s in a["steps"]], ["opencode"] * 3)
        self.assertEqual(sum(s["access"] == "write" for s in a["steps"]), 1)

    def test_explicit_multi(self):
        config = {"mode": "multi", "hosts": ["claude", "codex"], "policy": "external_opt_in",
                  "roles": {"plan": "claude", "implement": "codex", "review": "claude"},
                  "engine": "conductor"}
        a = m.resolve(config)
        self.assertEqual([s["host"] for s in a["steps"]], ["claude", "codex", "claude"])
        self.assertFalse(a["parallel"])
        self.assertFalse(a["automatic_fallback"])
        self.assertIn("microsoft/conductor", [c["preferred"] for c in a["candidates"]])

    def test_reject_invalid(self):
        for config in (
            {"additional_budget_brl": 1}, {"additional_budget_brl": False},
            {"allow_billable_api": True}, {"allow_billable_api": 0},
            {"mode": "single", "hosts": ["codex"]},
            {"mode": "multi", "hosts": ["opencode", "aider"]},
            {"mode": "single", "hosts": ["opencode", "aider"]},
            {"mode": "none", "hosts": ["opencode"]},
            {"hosts": ["bad"]}, {"engine": "automatic"}, {"capabilities": ["unknown"]},
            {"fallback": True}, {"profile": []}, {"roles": {"plan": "codex"}},
            {"mode": "multi", "hosts": ["opencode", "aider"],
             "roles": {"plan": "opencode", "implement": "opencode", "review": "opencode"}},
        ):
            with self.subTest(config=config), self.assertRaises(ValueError):
                m.resolve(config)

    def test_reject_duplicate_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            p.write_text('{"mode":"none","mode":"multi"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                m.read_config(p)

    def test_doctor_no_spawn(self):
        from unittest.mock import patch
        with patch("shutil.which", return_value=None):
            self.assertTrue(all(not v for v in m.doctor()["tools"].values()))
