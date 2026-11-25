"""Repository-scoped instruction generation; no host config or skill execution."""
import hashlib
import json
from pathlib import Path
from .cli import NaviError, RES, load_manifest, validate

TARGETS = {"codex": "AGENTS.md", "claude": "CLAUDE.md",
           "copilot": ".github/copilot-instructions.md", "gemini": "GEMINI.md"}
CATEGORIES = ("architecture", "engineering", "verification", "knowledge")

def policy():
    raw = RES.joinpath("agents/policy.json").read_bytes()
    data = json.loads(raw)
    if data["schema_version"] != 1 or len({r["id"] for r in data["rules"]}) != len(data["rules"]):
        raise NaviError("Invalid canonical policy")
    return data, hashlib.sha256(raw).hexdigest()

def render(host, profile):
    if host not in TARGETS:
        raise NaviError("Unknown instruction host")
    p, digest = policy()
    lines = ["# NAVI repository instructions", "",
             f"<!-- NAVI policy {p['revision']} sha256:{digest}; host:{host} -->",
             "", f"Project profile: {profile}.", "",
             "These are advisory instructions, not a sandbox or an approval service.",
             "Read local repository documentation and applicable host instructions.", ""]
    for rule in p["rules"]:
        lines.append(f"- **{rule['id']} — {rule['title']}:** {rule['text']}")
    lines += ["", "Use the project-specific verification gate. Do not assume that a generic gate proves production readiness.", ""]
    if host == "copilot":
        from .copilot_free import INSTRUCTIONS
        lines += [INSTRUCTIONS]
    return "\n".join(lines).encode("utf-8")

def safe_target(root, rel):
    path = root / rel
    for part in (path, *path.parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise NaviError("Refusing linked adapter path: " + rel)
    if not path.resolve().is_relative_to(root):
        raise NaviError("Adapter path outside project")
    return path

def adapters(root, host=None, mode="plan"):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise NaviError("Project root must be a directory")
    if host not in (*TARGETS, "all", None) or mode not in ("plan", "check", "apply"):
        raise NaviError("Invalid adapter selection")
    manifest = load_manifest(root)
    profile = manifest["project"]["profile"]
    if host is None:
        preferred = manifest["agents"].get("host")
        if preferred in TARGETS:
            host = preferred
    if host is None:
        if mode != "plan":
            raise NaviError("Select one host explicitly (or all for an explicit compatibility operation)")
        return {"status": "planned", "mode": mode, "profile": profile,
                "supported_hosts": list(TARGETS), "files": [], "scope": "Choose one host; none required by Core"}
    selected = list(TARGETS) if host == "all" else [host]
    planned = []
    for name in selected:
        rel = TARGETS[name]
        path = safe_target(root, rel)
        expected = render(name, profile)
        if path.exists():
            # Never expose the existing file's text or digest in reports.
            same = path.is_file() and path.stat().st_size == len(expected) and path.read_bytes() == expected
            state = "current" if same else "conflict"
        else:
            state = "missing"
        planned.append((name, rel, expected, state))
    report = {"mode": mode, "profile": profile,
              "files": [{"host": name, "path": rel, "state": state,
                         "expected_sha256": hashlib.sha256(expected).hexdigest()}
                        for name, rel, expected, state in planned]}
    if any(state == "conflict" for _, _, _, state in planned):
        return {"status": "conflict", **report}
    if mode == "check":
        return {"status": "current" if all(state == "current" for _, _, _, state in planned) else "drift", **report}
    if mode == "plan":
        return {"status": "planned", **report}
    created = []
    try:
        for name, rel, expected, state in planned:
            if state == "current":
                continue
            path = safe_target(root, rel)
            path.parent.mkdir(parents=True, exist_ok=True)
            path = safe_target(root, rel)
            with path.open("xb") as f:
                f.write(expected)
            created.append(rel)
    except OSError as exc:
        # Concurrent changes must never be overwritten. Do not delete files to
        # roll back automatically: another process might have edited them.
        raise NaviError("Adapter creation interrupted; created: " + ", ".join(created)) from exc
    return {"status": "applied", **report, "created": created}

def list_skills(host=None, category=None):
    data = json.loads(RES.joinpath("agents/skills.json").read_text(encoding="utf-8"))
    seen = set()
    for record in data:
        contract = validate("skill", record["contract"])
        key = (contract["id"].casefold(), contract["version"])
        if key in seen or record["category"] not in CATEGORIES or record["handler"] is not None:
            raise NaviError("Invalid or duplicate candidate skill metadata")
        seen.add(key)
    matches = [record for record in data
               if (host is None or host in record["contract"]["hosts"])
               and (category is None or category == record["category"])]
    return {"status": "metadata-only", "skills": matches,
            "scope": "candidate metadata; no installed or executable handlers"}
