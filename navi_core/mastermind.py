"""Mastermind advisory resolver: no execution, installation, credentials or network."""
from __future__ import annotations

import hashlib
import json
import shutil
from importlib.resources import files
from pathlib import Path

ROLES = ("plan", "implement", "review")
HOSTS = {
    "opencode": ("local", "opencode"),
    "aider": ("local", "aider"),
    "codex": ("external", "codex"),
    "claude": ("external", "claude"),
    "gemini": ("external", "gemini"),
    "copilot": ("external", "copilot"),
}
CAPABILITIES = {
    "workflow": ("microsoft/conductor", "dbos-inc/dbos-transact-py", "langchain-ai/langgraph", "temporalio/temporal"),
    "agent-protocol": ("agentclientprotocol/agent-client-protocol",),
    "tool-protocol": ("modelcontextprotocol/modelcontextprotocol", "modelcontextprotocol/python-sdk"),
    "skills": ("agentskills/agentskills", "agentsmd/agents.md"),
    "specification": ("github/spec-kit", "fission-ai/openspec"),
    "methodology": ("obra/superpowers", "bmad-code-org/bmad-method"),
    "structure": ("graphify-labs/graphify", "tree-sitter/tree-sitter"),
    "symbols": ("oraios/serena", "sourcegraph/scip"),
    "documentation": ("upstash/context7", "docling-project/docling"),
    "memory": ("sqlite/sqlite", "topoteretes/cognee", "garrytan/gbrain"),
    "compression": ("microsoft/llmlingua", "yamadashy/repomix"),
    "reverse-engineering": ("morluto/rea", "nationalSecurityagency/ghidra".lower()),
    "binary-testing": ("angr/angr", "unicorn-engine/unicorn"),
    "browser-test": ("microsoft/playwright",),
    "evaluation": ("promptfoo/promptfoo", "ukgovernmentbeis/inspect_ai"),
    "secrets-scan": ("gitleaks/gitleaks",),
    "dependency-scan": ("google/osv-scanner", "aquasecurity/trivy"),
    "sbom": ("anchore/syft",),
    "license-review": ("fsfe/reuse-tool", "aboutcode-org/scancode-toolkit"),
    "policy": ("open-policy-agent/opa",),
    "telemetry": ("open-telemetry/opentelemetry-python",),
    "local-inference": ("ollama/ollama", "ggml-org/llama.cpp"),
    "distribution": ("astral-sh/uv",),
}
PROFILES = {
    "general": ("specification", "structure", "symbols", "secrets-scan"),
    "backend": ("specification", "symbols", "dependency-scan", "secrets-scan"),
    "web": ("specification", "symbols", "browser-test", "dependency-scan"),
    "game-recomp": ("structure", "symbols", "reverse-engineering", "binary-testing", "secrets-scan"),
    "documentation": ("documentation",),
    "security": ("secrets-scan", "dependency-scan", "sbom", "license-review", "policy"),
}

def _require(condition, message):
    if not condition:
        raise ValueError(message)

def catalog():
    data = json.loads(files("navi_core").joinpath("agents/mastermind-catalog.json").read_text(encoding="utf-8"))
    entries = data["entries"]
    ids = {entry["id"] for entry in entries}
    _require(len(ids) == len(entries) and data["installable"] is False, "Invalid catalog")
    _require(all(entry["approved"] is False and entry["revision"] is None and entry["sha256"] is None for entry in entries), "Unexpected catalog approval")
    _require(all(set(values) <= ids for values in CAPABILITIES.values()), "Unregistered capability")
    return data

def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "Duplicate configuration key")
        result[key] = value
    return result

def read_config(path):
    path = Path(path)
    _require(path.is_file() and not path.is_symlink(), "Expected a regular configuration file")
    with path.open("rb") as stream:
        raw = stream.read(65537)
    _require(len(raw) <= 65536, "Configuration too large")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)

def resolve(config):
    _require(type(config) is dict, "Expected configuration object")
    allowed = {"mode", "hosts", "roles", "policy", "additional_budget_brl", "allow_billable_api", "engine", "profile", "capabilities"}
    _require(set(config) <= allowed, "Unknown configuration keys")
    mode = config.get("mode", "none")
    hosts = config.get("hosts", [])
    policy = config.get("policy", "strict_oss")
    engine = config.get("engine", "direct")
    profile = config.get("profile", "general")
    _require(type(mode) is str and mode in ("none", "single", "multi"), "Invalid agent mode")
    _require(type(hosts) is list and all(type(h) is str and h in HOSTS for h in hosts), "Invalid host list")
    _require(len(set(hosts)) == len(hosts), "Duplicate hosts")
    _require((mode == "none" and not hosts) or (mode == "single" and len(hosts) == 1) or (mode == "multi" and 2 <= len(hosts) <= len(HOSTS)), "Host count does not match mode")
    _require(type(policy) is str and policy in ("strict_oss", "external_opt_in"), "Invalid policy")
    _require(type(config.get("additional_budget_brl", 0)) is int and config.get("additional_budget_brl", 0) == 0, "Additional budget must be zero")
    _require(config.get("allow_billable_api", False) is False, "Billable APIs are forbidden")
    _require(type(engine) is str and engine in ("direct", "conductor"), "Unknown engine")
    _require(type(profile) is str and profile in PROFILES, "Unknown profile")
    _require(policy != "strict_oss" or all(HOSTS[h][0] == "local" for h in hosts), "External host requires explicit external_opt_in")
    roles = config.get("roles", {} if mode == "none" else ({r: hosts[0] for r in ROLES} if mode == "single" else None))
    _require(type(roles) is dict, "Explicit multi-agent role assignment required")
    _require(set(roles) == (set() if mode == "none" else set(ROLES)), "Expected plan, implement and review roles")
    _require(all(type(h) is str and h in hosts for h in roles.values()), "Role host must be selected")
    _require(set(roles.values()) == set(hosts), "All selected agents must have a role")
    # Exactly one writer, sequential handoff; no automatic fallback or provider switch.
    extra = config.get("capabilities", [])
    _require(type(extra) is list and all(type(c) is str and c in CAPABILITIES for c in extra), "Unknown capability")
    wanted = list(dict.fromkeys([*PROFILES[profile], *extra] + (["workflow"] if engine == "conductor" else [])))
    data = catalog()
    by_id = {e["id"]: e for e in data["entries"]}
    proposed = []
    for capability in wanted:
        options = CAPABILITIES[capability]
        proposed.append({"capability": capability, "preferred": options[0], "alternatives": list(options[1:]), "classification": by_id[options[0]]["classification"], "state": "review-required", "execution_allowed": False})
    steps = [{"role": r, "host": roles[r], "access": "write" if r == "implement" else "read-only"} for r in ROLES if r in roles]
    result = {"schema_version": 1, "status": "planned", "execution_allowed": False,
              "mode": mode, "policy": policy, "hosts": hosts, "steps": steps,
              "engine": engine, "profile": profile, "additional_budget_brl": 0,
              "allow_billable_api": False, "automatic_fallback": False, "parallel": False,
              "candidates": proposed, "gates": ["license and pinned artifact review", "local/offline or authorized quota verification", "host and tool compatibility", "explicit execution approval", "independent verification"],
              "scope": "Advisory only; does not enforce sandbox, role access, quota, network, or licensing."}
    result["sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result

def doctor():
    commands = {"conductor": "conductor", "git": "git", "uv": "uv", "ollama": "ollama", **{h: v[1] for h, v in HOSTS.items()}}
    return {"status": "presence-only", "tools": {k: bool(shutil.which(v)) for k, v in commands.items()}, "scope": "No process, authentication, installation, or network check; no approval inferred."}

def register(sub):
    p = sub.add_parser("mastermind", help="Read-only Mastermind catalog and integration planner")
    actions = p.add_subparsers(dest="mastermind_action", required=True)
    c = actions.add_parser("catalog")
    c.add_argument("--domain")
    actions.add_parser("doctor")
    plan = actions.add_parser("plan")
    plan.add_argument("config", type=Path)

def command(args):
    if args.mastermind_action == "doctor":
        return doctor()
    if args.mastermind_action == "plan":
        return resolve(read_config(args.config))
    data = catalog()
    if args.domain:
        _require(args.domain in {e["domain"] for e in data["entries"]}, "Unknown catalog domain")
        data["entries"] = [e for e in data["entries"] if e["domain"] == args.domain]
    return data
