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
    if (root/"pyproject.toml").is_file(): matches.append("python-tooling")
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

def plan(root):
    data=load_manifest(root); profile=data["project"]["profile"]; p=REGISTRY[profile]
    if p["status"] != "supported": raise NaviError("Profile planned, not executable")
    missing=[name for name in p["required"] if not (root/name).is_file()]
    if missing: raise NaviError("Missing required files: "+", ".join(missing))
    commands=p["commands"]
    if profile == "typescript-backend":
        pkg=json.loads((root/"package.json").read_text(encoding="utf-8"))
        if not pkg.get("scripts",{}).get("verify"): raise NaviError("npm verify script missing")
    if profile == "python-tooling" and not any((root/"tests").glob("test*.py")):
        raise NaviError("No top-level unittest test files found")
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
    p=sub.add_parser("validate");p.add_argument("kind",choices=CONTRACTS);p.add_argument("file",type=pathlib.Path)
    args=parser.parse_args(argv)
    try:
        if args.command=="doctor": out=doctor()
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
