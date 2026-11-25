"""Local-only, explicit-execution CLI. No credentials, network API or publishing."""
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tomllib
from urllib.parse import unquote, urlsplit
from importlib.resources import files
from jsonschema import Draft202012Validator, FormatChecker
from . import __version__

RES = files("navi_core")
REGISTRY = json.loads(RES.joinpath("profiles/registry.json").read_text(encoding="utf-8"))
CONTRACTS = ("project", "task", "skill", "evidence", "event")

class NaviError(Exception):
    pass

def validate(kind, data):
    if kind not in CONTRACTS:
        raise NaviError("Unknown contract")
    schema = json.loads(RES.joinpath(f"contracts/{kind}.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data), key=lambda e: str(e.path))
    if errors:
        # Do not include manifest values in diagnostics (they may be private).
        raise NaviError("Invalid " + kind + ": " + "; ".join(f"{'.'.join(map(str,e.path)) or '<root>'}: {e.validator}" for e in errors))
    if kind == "task" and data["risk"] in ("high", "critical") and not data["approval_required"]:
        raise NaviError("High-risk tasks require approval")
    if kind == "evidence" and data["status"] == "passed" and data["exit_code"] != 0:
        raise NaviError("Passed evidence requires exit code 0")
    return data

def detect(root):
    matches = []
    if (root/"package.json").is_file() and (root/"tsconfig.json").is_file():
        try:
            p = json.loads((root/"package.json").read_text(encoding="utf-8"))
            if "hono" in p.get("dependencies", {}) and "verify" in p.get("scripts", {}):
                matches.append("typescript-backend")
            else:
                matches.append("typescript-frontend")
        except (ValueError, TypeError, AttributeError):
            raise NaviError("Invalid package.json")
    if (root/"pyproject.toml").is_file() or any((root/"tests").glob("test*.py")): matches.append("python-tooling")
    if (root/"CMakeLists.txt").is_file(): matches.append("cpp-native")
    if (root/"project.godot").is_file(): matches.append("godot-game")
    if (root/"index.html").is_file(): matches.append("static-website")
    if not matches and (root/"README.md").is_file(): matches.append("documentation")
    return matches

def init(root, profile, visibility):
    if not root.is_dir(): raise NaviError("Project root must exist")
    if profile is None:
        candidates = detect(root)
        if len(candidates) != 1: raise NaviError("No unique profile; supply --profile")
        profile = candidates[0]
    name = root.name
    data = {"schema_version":1,"project":{"name":name,"visibility":visibility,"maturity":"experimental","profile":profile},"verification":{"require_real_tests":True,"timeout_seconds":900},"knowledge":{"public_export":False},"agents":{"approval_for_production":True,"parallel_workers":2}}
    validate("project", data)
    directory = root/".navi"
    if directory.is_symlink(): raise NaviError("Refusing symlink .navi")
    directory.mkdir(exist_ok=True)
    path = directory/"project.toml"
    if path.is_symlink(): raise NaviError("Refusing symlink manifest")
    content = "schema_version = 1\n"
    for key, section in data.items():
        if key == "schema_version": continue
        content += f"\n[{key}]\n"
        for k,value in section.items(): content += f"{k} = {json.dumps(value,ensure_ascii=False)}\n"
    try:
        with path.open("x",encoding="utf-8") as f: f.write(content)
    except FileExistsError: raise NaviError("Manifest exists; no overwrite")
    return {"created":".navi/project.toml","profile":profile}

def load_manifest(root):
    p=root/".navi/project.toml"
    if p.is_symlink() or p.parent.is_symlink(): raise NaviError("Refusing symlink manifest")
    return validate("project",tomllib.loads(p.read_text(encoding="utf-8")))

def scoped_tests(root, directory, suffixes):
    # Only normalized relative paths. Reject links/junctions along every component.
    parts=directory.split("/")
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*(/[A-Za-z0-9_][A-Za-z0-9_.-]*)*",directory):
        raise NaviError("Invalid test directory")
    path=root
    for part in parts:
        path=path/part
        if path.is_symlink() or (hasattr(path,"is_junction") and path.is_junction()):
            raise NaviError("Linked test directory")
    if not path.is_dir() or not path.resolve().is_relative_to(root):
        raise NaviError("Test directory missing or outside project")
    found=[]
    for child in sorted(path.iterdir()):
        if child.suffix in suffixes and (suffixes!={".py"} or child.name.startswith("test")):
            if child.is_symlink() or not child.is_file() or not child.resolve().is_relative_to(root):
                raise NaviError("Invalid test file")
            found.append(child.relative_to(root).as_posix())
    if not found: raise NaviError("No scoped test files found")
    return found

def plan(root):
    root = root.resolve(strict=True)
    data=load_manifest(root); profile=data["project"]["profile"]; p=REGISTRY[profile]
    if p["status"] != "supported": raise NaviError("Profile planned, not executable")
    missing=[name for name in p["required"] if not (root/name).is_file()]
    if missing: raise NaviError("Missing required files: "+", ".join(missing))
    commands=p["commands"]
    if profile == "typescript-backend":
        pkg=json.loads((root/"package.json").read_text(encoding="utf-8"))
        if not pkg.get("scripts",{}).get("verify"): raise NaviError("npm verify script missing")
    directory=data["verification"].get("test_dir","tests")
    if "test_dir" in data["verification"] and profile not in ("python-tooling","javascript-tooling"):
        raise NaviError("test_dir is only supported by scoped test profiles")
    if profile == "python-tooling":
        scoped_tests(root,directory,{".py"})
        commands=[["python","-c","import sys, unittest; suite = unittest.defaultTestLoader.discover(sys.argv[1]); count = suite.countTestCases(); result = unittest.TextTestRunner(verbosity=2).run(suite); print('Discovered tests:', count, 'Executed non-skipped:', result.testsRun-len(result.skipped)); sys.exit(0 if count > 0 and result.testsRun > len(result.skipped) and result.wasSuccessful() else 1)",directory]]
    if profile == "javascript-tooling":
        paths=scoped_tests(root,directory,{".mjs",".cjs",".js"})
        commands=[["python","-I","-m","navi_core.test_gates","node",*paths]]
    if profile == "static-website":
        # Check tracked JS only; never traverse dependencies or arbitrary symlinks.
        tracked=subprocess.run(["git","-C",str(root),"ls-files","-z"],check=True,capture_output=True).stdout.decode("utf-8").split("\0")
        commands=[]
        for f in tracked:
            path=root/f
            if f and path.suffix in (".js",".mjs",".cjs") and not path.is_symlink() and path.resolve().is_relative_to(root) and path.is_file(): commands.append(["node","--check",str(path)])
        if not commands: raise NaviError("No tracked standalone JavaScript to verify")
    return {"profile":profile,"commands":commands,"install":p["install"],"timeout_seconds":data["verification"]["timeout_seconds"],"tools":p["tools"],"builtin":"markdown-links" if profile=="documentation" else None}

LINK = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)")
def check_docs(root):
    root = root.resolve(strict=True)
    # Scoped lightweight checker, not a Markdown parser. README inline links only.
    content=(root/"README.md").read_text(encoding="utf-8")
    checked=0; errors=[]
    content=re.sub(r"```[^\n]*\n.*?```","",content,flags=re.S)
    for target in LINK.findall(content):
        parts=urlsplit(target)
        if parts.scheme or parts.netloc or not parts.path or target.startswith("/"): continue
        p=(root/unquote(parts.path)).resolve();checked+=1
        if not p.is_relative_to(root) or not p.exists(): errors.append(target)
    if errors: raise NaviError(f"README has {len(errors)} invalid local link(s)")
    return {"checked_links":checked,"utf8":True,"scope":"README inline local links; excludes anchors, remote links, code fences"}

def executable(name):
    if name=="python": return sys.executable
    resolved=shutil.which(name)
    if resolved is None: raise NaviError("Missing executable: "+name)
    # Windows .cmd launchers need a shell; refuse instead of silently enabling one.
    if os.name=="nt" and pathlib.Path(resolved).suffix.lower() in (".cmd",".bat"):
        if name=="npm":
            node=shutil.which("node"); npm_cli=pathlib.Path(resolved).parent/"node_modules/npm/bin/npm-cli.js"
            if node and npm_cli.is_file(): return [node,str(npm_cli)]
        raise NaviError("No shell-free executable for "+name)
    return resolved

def verify(root, execute=False):
    root = root.resolve(strict=True)
    p=plan(root)
    if not execute: return {"status":"planned",**p}
    # Project scripts are trusted code, not a sandbox. No arbitrary commands in manifests.
    results=[]
    if p["profile"] == "typescript-backend":
        node = executable("node")
        node_args = [node] if isinstance(node,str) else node
        version = subprocess.run(node_args+["--version"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if not re.fullmatch(r"v24\.\d+\.\d+(?:[-+].*)?",version):
            raise NaviError("Node 24 is required by the backend profile")
    if p["builtin"]: results.append(check_docs(root))
    for command in p["commands"]:
        exe=executable(command[0]); args=([exe] if isinstance(exe,str) else exe)+command[1:]
        result=subprocess.run(args,cwd=root,timeout=p["timeout_seconds"],check=False)
        results.append({"command":command,"exit_code":result.returncode})
        if result.returncode: raise NaviError(f"Verification failed ({result.returncode}): {command[0]}")
    return {"status":"passed","profile":p["profile"],"results":results,"scope":"profile gate only; not production certification"}

def doctor():
    return {"version":__version__,"python":sys.version.split()[0],"tools":{name:bool(shutil.which(name)) for name in ("git","node","npm","cmake","ctest","gh","gitleaks")},"scope":"tool presence only; versions and permissions not verified"}

def main(argv=None):
    parser=argparse.ArgumentParser(prog="navi")
    parser.add_argument("--version",action="version",version=__version__)
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor")
    for name in ("detect","init","verify"):
        p=sub.add_parser(name);p.add_argument("--root",type=pathlib.Path,default=pathlib.Path.cwd())
        if name=="init":
            p.add_argument("--profile",choices=REGISTRY);p.add_argument("--visibility",choices=("public","private","internal","unknown"),default="unknown")
        if name=="verify":p.add_argument("--execute",action="store_true",help="Run trusted project code; not sandboxed")
    p=sub.add_parser("agents",help="Plan, check or create repository agent adapters")
    p.add_argument("--root",type=pathlib.Path,default=pathlib.Path.cwd())
    p.add_argument("--host",choices=("all","codex","claude","copilot","gemini"))
    p.add_argument("--mode",choices=("plan","check","apply"),default="plan")
    p=sub.add_parser("skills",help="List reviewed metadata candidates; never execute skills")
    p.add_argument("--host",choices=("codex","claude","copilot","gemini","nexus"))
    p.add_argument("--category",choices=("architecture","engineering","verification","knowledge"))
    p=sub.add_parser("skill-scan",help="Inventory local ZIP metadata without extracting or executing")
    p.add_argument("archives",nargs="+",type=pathlib.Path)
    p.add_argument("--output",required=True,type=pathlib.Path)
    p=sub.add_parser("context",help="Select reviewed local skill variants; no execution")
    p.add_argument("--inventory",required=True,type=pathlib.Path)
    p.add_argument("--approvals",required=True,type=pathlib.Path)
    p.add_argument("--host",required=True,choices=("codex","claude","copilot","gemini","nexus"))
    p.add_argument("--query",required=True)
    p.add_argument("--budget-bytes",type=int,default=24000)
    p.add_argument("--max-risk",choices=("low","medium","high","critical"),default="low")
    p.add_argument("--output",type=pathlib.Path,help="Optional private context packet; no overwrite")
    p.add_argument("--archives",nargs="+",type=pathlib.Path,default=[])
    p=sub.add_parser("bench",help="Offline synthetic benchmark; no agent or candidate code execution")
    p.add_argument("--mode",choices=("catalog","reference","evaluate"),default="catalog")
    p.add_argument("--case")
    p.add_argument("--submission",type=pathlib.Path)
    p.add_argument("--output",type=pathlib.Path)
    p.add_argument("--budget-bytes",type=int,default=4096)
    p=sub.add_parser("providers",help="List providers or run a synthetic Ollama case explicitly")
    p.add_argument("--model")
    p.add_argument("--case")
    p.add_argument("--execute",action="store_true")
    p.add_argument("--max-output-tokens",type=int,default=512)
    p.add_argument("--timeout",type=int,default=60)
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("proof",help="Recompute synthetic benchmark evidence")
    p.add_argument("--case",required=True)
    p.add_argument("--submission",required=True,type=pathlib.Path)
    p.add_argument("--budget-bytes",type=int,default=4096)
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("sentinel",help="Read-only local project policy preflight")
    p.add_argument("--root",type=pathlib.Path,default=pathlib.Path.cwd())
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("rollout",help="Generate a non-mutating adoption plan")
    p.add_argument("--root",type=pathlib.Path,default=pathlib.Path.cwd())
    p.add_argument("--core-sha",required=True)
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("public-status",help="Produce allowlisted synthetic Core metrics only")
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("proof-run",help="Run trusted project gate and create private evidence")
    p.add_argument("--root",type=pathlib.Path,default=pathlib.Path.cwd())
    p.add_argument("--output-dir",type=pathlib.Path,required=True)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--timeout",type=int,default=900)
    p=sub.add_parser("proof-check",help="Verify local log integrity; not attestation")
    p.add_argument("directory",type=pathlib.Path)
    p=sub.add_parser("compare",help="Paired synthetic Ollama strategy experiment; plan by default")
    p.add_argument("--model",required=True)
    p.add_argument("--case",choices=("all","BENCH-DAG-001","BENCH-ARTIFACT-001","BENCH-BUDGET-001","BENCH-GOVERNANCE-001"),default="all")
    p.add_argument("--trials",type=int,default=3)
    p.add_argument("--max-output-tokens",type=int,default=512)
    p.add_argument("--max-input-tokens",type=int,default=8192)
    p.add_argument("--timeout",type=int,default=120)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("copilot-plan",help="Plan a small Copilot Free task without inference or billing access")
    p.add_argument("--kind",required=True,choices=("docs","unit-test","small-fix","explain","format","lint","complex","architecture","security","release"))
    p.add_argument("--risk",required=True,choices=("low","medium","high","critical"))
    p.add_argument("--visibility",required=True,choices=("public","private","internal","unknown"))
    p.add_argument("--files",required=True,type=int)
    p.add_argument("--lines",required=True,type=int)
    p.add_argument("--used-percent",type=int)
    p.add_argument("--estimate-percent",type=int)
    p.add_argument("--checked-on",help="UTC date when actual account usage was checked (YYYY-MM-DD)")
    p.add_argument("--paid-usage-blocked",action="store_true",help="Confirm you already disabled additional paid usage in GitHub billing")
    p=sub.add_parser("host-lab",help="Prepare or verify manual synthetic host acceptance")
    p.add_argument("--mode",required=True,choices=("prepare","check"))
    p.add_argument("--directory",required=True,type=pathlib.Path)
    p.add_argument("--host",choices=("codex","claude","copilot","gemini"))
    p.add_argument("--submission",type=pathlib.Path)
    p.add_argument("--reported-version")
    p.add_argument("--output",type=pathlib.Path)
    p=sub.add_parser("validate");p.add_argument("kind",choices=CONTRACTS);p.add_argument("file",type=pathlib.Path)
    args=parser.parse_args(argv)
    try:
        if args.command=="doctor": out=doctor()
        elif args.command=="copilot-plan":
            from .copilot_free import plan as copilot_plan
            out=copilot_plan(args.kind,args.risk,args.visibility,args.files,args.lines,args.used_percent,args.estimate_percent,args.checked_on,args.paid_usage_blocked)
        elif args.command=="host-lab":
            from . import host_lab
            from .skill_registry import read_json,write_private
            if args.mode=="prepare":
                if args.submission or args.reported_version or args.output: raise NaviError("Prepare accepts directory and optional host")
                out=host_lab.create(args.directory,args.host)
            else:
                if not args.host or not args.submission or not args.reported_version: raise NaviError("Check requires host, submission and reported version")
                out=host_lab.check(args.directory,args.host,read_json(args.submission),args.reported_version)
                if args.output is not None:write_private(args.output,out)
                if out["status"]!="passed":
                    print(json.dumps(out,ensure_ascii=False,indent=2));return 1
        elif args.command=="agents":
            from .agent_bridge import adapters
            out=adapters(args.root,args.host,args.mode)
            if out["status"] in ("conflict","drift"):
                print(json.dumps(out,ensure_ascii=False,indent=2));return 1
        elif args.command=="skills":
            from .agent_bridge import list_skills
            out=list_skills(args.host,args.category)
        elif args.command=="skill-scan":
            from .skill_registry import scan, write_private
            inventory=scan(args.archives)
            write_private(args.output,inventory)
            out={"status":"quarantined","summary":inventory["summary"]}
        elif args.command=="context":
            from .skill_registry import read_json, select, packet, write_private
            inventory=read_json(args.inventory)
            approvals=read_json(args.approvals)
            out=select(inventory,approvals,args.host,args.query,args.budget_bytes,args.max_risk)
            if args.output is not None:
                content=packet(out,args.archives,args.budget_bytes)
                write_private(args.output,content)
                out={"status":"packet-created","selected":len(out["selected"]),"scope":"private-local; no execution or upload"}
        elif args.command=="compare":
            from . import paired_bench
            from .skill_registry import write_private
            out=paired_bench.run(args.model,args.case,args.trials,args.max_output_tokens,args.max_input_tokens,args.timeout,execute=args.execute)
            if args.output is not None: write_private(args.output,out)
            if out["status"] in ("blocked","failed"):
                print(json.dumps(out,ensure_ascii=False,indent=2));return 1
        elif args.command=="bench":
            from .agent_bench import catalog, run_reference, evaluate, check_options
            from .skill_registry import read_json, write_private
            check_options(args.mode,args.case,args.submission,args.budget_bytes)
            if args.mode=="catalog": out=catalog()
            elif args.mode=="reference": out=run_reference(args.case,args.budget_bytes)
            else: out=evaluate(args.case,read_json(args.submission),args.budget_bytes)
            if args.output is not None:
                write_private(args.output,out)
            if out.get("status")=="failed":
                print(json.dumps(out,ensure_ascii=False,indent=2));return 1
        elif args.command in ("proof-run","proof-check"):
            from . import engineering_proof
            if args.command=="proof-run":
                if not args.execute: raise NaviError("Trusted code execution requires --execute")
                out=engineering_proof.capture(args.root,args.output_dir,args.timeout)
            else: out=engineering_proof.check(args.directory)
            if out["status"]!="passed":
                print(json.dumps(out,ensure_ascii=False,indent=2));return 1
        elif args.command in ("providers","proof","sentinel","rollout","public-status"):
            from . import providers, governance
            from .skill_registry import read_json, write_private
            if args.command=="providers":
                out=providers.run(args.model,args.case,args.max_output_tokens,args.timeout) if args.execute else providers.plan(args.model,args.case,args.max_output_tokens,args.timeout)
            elif args.command=="proof":
                out=governance.proof(args.case,read_json(args.submission),args.budget_bytes)
            elif args.command=="sentinel":
                out=governance.preflight(args.root)
            elif args.command=="rollout":
                out=governance.rollout(args.root,args.core_sha)
            else: out=governance.public_status()
            if args.output is not None:
                write_private(args.output,out)
            if out.get("status") in ("failed","blocked"):
                print(json.dumps(out,ensure_ascii=False,indent=2));return 1
        elif args.command=="validate":
            s=args.file.read_text(encoding="utf-8");validate(args.kind,tomllib.loads(s) if args.file.suffix==".toml" else json.loads(s));out={"status":"valid","contract":args.kind}
        else:
            root=args.root.resolve(strict=True)
            if not root.is_dir(): raise NaviError("Project root must be a directory")
            if args.command=="detect":out={"candidates":detect(root)}
            elif args.command=="init":out=init(root,args.profile,args.visibility)
            else:out=verify(root,args.execute)
        print(json.dumps(out,ensure_ascii=False,indent=2));return 0
    except (NaviError,OSError,ValueError,TypeError,KeyError,subprocess.SubprocessError) as exc:
        print(f"NAVI: {exc if isinstance(exc,NaviError) else type(exc).__name__}",file=sys.stderr);return 1
