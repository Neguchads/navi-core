"""Read-only NAVI ecosystem audit of explicitly selected local Git revisions."""
import json
import re
import subprocess
from pathlib import Path

from .cli import NaviError

REGISTRY = {
    "navi-core": ("main", "engineering core"),
    "navi-graphify": ("v8", "public catalog and graph producer"),
    "navi-githomepage": ("main", "public renderer"),
    "navi-abyss": ("main", "visual reference"),
    "Neguchads": ("main", "public publication"),
}
CONSUMERS = tuple(name for name in REGISTRY if name != "navi-core")
PUBLISHERS = ("navi-graphify", "navi-githomepage", "navi-abyss")
SHA = re.compile(r"[a-f0-9]{40}")
WORKFLOW = ".github/workflows/navi-pilot.yml"

def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True,
        timeout=15, text=True, encoding="utf-8",
    ).stdout.strip()

def _read(root, revision, path):
    ref = revision + ":" + path
    if int(_git(root, "cat-file", "-s", ref)) > 65536:
        raise NaviError("Integration manifest too large")
    return _git(root, "show", ref)

def _pins(raw):
    # Recognize the exact canonical workflow syntax, not arbitrary YAML.
    uses = re.findall(r"(?m)^\s*uses: Neguchads/navi-core/\.github/workflows/reusable-ci\.yml@([a-f0-9]{40})\s*$", raw)
    values = re.findall(r"(?m)^\s*core_sha: ([a-f0-9]{40})\s*$", raw)
    if len(uses) != 1 or len(values) != 1:
        raise NaviError("Missing or ambiguous canonical Core pins")
    return uses[0], values[0]

def _unique(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise NaviError("Duplicate integration pin")
        result[k] = v
    return result

def audit(workspace, core_sha):
    if not isinstance(core_sha, str) or not SHA.fullmatch(core_sha):
        raise NaviError("Expected reviewed full Core SHA")
    workspace = Path(workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise NaviError("Expected workspace directory")
    rows = {}
    for name, (branch, role) in REGISTRY.items():
        root = workspace / name
        row = {"repository": "Neguchads/" + name, "default_branch": branch,
               "role": role, "commit": None, "core_pin": None, "state": "unavailable"}
        rows[name] = row
        try:
            if root.is_symlink() or (hasattr(root, "is_junction") and root.is_junction()):
                raise NaviError("Linked checkout not accepted")
            if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
                raise NaviError("Expected checkout root")
            revision = _git(root, "rev-parse", "--verify", "HEAD")
            if not SHA.fullmatch(revision):
                raise NaviError("Invalid Git revision")
            row["commit"] = revision
            if name == "navi-core":
                row["state"] = "aligned" if revision == core_sha else "review-required"
            else:
                first, second = _pins(_read(root, revision, WORKFLOW))
                row["core_pin"] = first
                row["state"] = "aligned" if first == second == core_sha else "drift"
        except (OSError, ValueError, subprocess.SubprocessError, NaviError):
            row["state"] = "unavailable" if row["commit"] is None else "invalid"
    universe = {"state": "unavailable", "sources": []}
    profile = rows["Neguchads"]["commit"]
    if profile:
        try:
            pins = json.loads(_read(workspace / "Neguchads", profile, "docs/universe-pins.json"), object_pairs_hook=_unique)
            if not isinstance(pins, dict) or set(pins) != set(PUBLISHERS) or any(not isinstance(v,str) or not SHA.fullmatch(v) for v in pins.values()):
                raise NaviError("Invalid Universe pins")
            for name in PUBLISHERS:
                observed = rows[name]["commit"]
                universe["sources"].append({"repository": name, "pin": pins[name],
                    "checkout": observed, "state": "unavailable" if observed is None else
                    ("aligned" if observed == pins[name] else "review-required")})
            universe["state"] = "aligned" if all(x["state"] == "aligned" for x in universe["sources"]) else "review-required"
        except (OSError, ValueError, subprocess.SubprocessError, NaviError):
            universe["state"] = "invalid"
    aligned = all(x["state"] == "aligned" for x in rows.values()) and universe["state"] == "aligned"
    return {"schema_version": 1, "status": "aligned" if aligned else "review-required",
            "expected_core": core_sha, "repositories": list(rows.values()), "universe": universe,
            "scope": "Local committed revisions only; no remote identity, CI, release, or security certification. No mutation or network."}
