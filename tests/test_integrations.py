import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

from navi_core import integrations, sbom
from navi_core.cli import NaviError

def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()

def commit(root, files):
    for name, contents in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    git(root, "add", ".")
    git(root, "-c", "user.name=NAVI Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-m", "fixture")
    return git(root, "rev-parse", "HEAD")

class IntegrationTest(unittest.TestCase):
    def test_real_git_revisions_and_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            for name in integrations.REGISTRY:
                root = workspace / name
                root.mkdir()
                git(root, "init", "--template=")
            core = commit(workspace / "navi-core", {"README.md": "fixture"})
            workflow = ("jobs:\n  verify:\n    uses: Neguchads/navi-core/.github/workflows/reusable-ci.yml@" +
                        core + "\n    with:\n      core_sha: " + core + "\n")
            pins = {}
            for name in integrations.PUBLISHERS:
                pins[name] = commit(workspace / name, {integrations.WORKFLOW: workflow})
            commit(workspace / "Neguchads", {integrations.WORKFLOW: workflow,
                   "docs/universe-pins.json": json.dumps(pins)})
            good = integrations.audit(workspace, core)
            self.assertEqual(good["status"], "aligned")
            self.assertNotIn(tmp, json.dumps(good))
            # An uncommitted file must not affect the committed-revision report.
            path = workspace / "navi-abyss" / integrations.WORKFLOW
            path.write_text("modified", encoding="utf-8")
            self.assertEqual(integrations.audit(workspace, core)["status"], "aligned")
            commit(workspace / "navi-abyss", {integrations.WORKFLOW: workflow.replace(core, "a"*40, 1)})
            drift = integrations.audit(workspace, core)
            self.assertEqual(drift["status"], "review-required")
            self.assertEqual(drift["universe"]["state"], "review-required")
            self.assertEqual(next(x for x in drift["repositories"] if x["repository"].endswith("/navi-abyss"))["state"], "drift")
    def test_invalid_and_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(integrations.audit(tmp, "a"*40)["status"], "review-required")
            with self.assertRaises(NaviError):
                integrations.audit(tmp, "main")
        with self.assertRaises(NaviError):
            integrations._pins("# no workflow")

class SbomTest(unittest.TestCase):
    def test_inventory(self):
        dist = SimpleNamespace(metadata={"Name":"Example_Package","License-Expression":"MIT"}, version="1.0")
        result = sbom.inventory([dist])
        self.assertEqual(result["bomFormat"], "CycloneDX")
        self.assertEqual(result["components"][0]["name"], "example-package")
        self.assertEqual(result["components"][0]["properties"][0]["value"], "MIT")
        with self.assertRaises(NaviError):
            sbom.inventory([dist, dist])
