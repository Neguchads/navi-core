"""Offline versioned environment installer; never installs or changes an AI host."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import venv
from .cli import NaviError

RECEIPT=".navi-install.json"
WHEEL=re.compile(r"[A-Za-z0-9_.+-]+\.whl")
CORE=re.compile(r"navi_engineering_core-([0-9][A-Za-z0-9.]*)-py3-none-any\.whl")

def _sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
    return h.hexdigest()

def _safe(path):
    path=Path(path).absolute()
    for p in (path,*path.parents):
        if p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()):raise NaviError("Use canonical unlinked installer paths")
    return path

def _destination(path):
    p=_safe(path)
    if not p.parent.is_dir() or any((x/".git").exists() for x in (p,*p.parents)):
        raise NaviError("Use an existing private parent outside Git")
    return p

def _manifest(path,expected):
    path=_safe(path)
    if not path.is_file() or path.stat().st_size>65536:raise NaviError("Invalid wheel manifest")
    if not isinstance(expected,str) or not re.fullmatch(r"[a-f0-9]{64}",expected) or _sha(path)!=expected:
        raise NaviError("Manifest digest mismatch; review expected SHA-256")
    rows={}
    for line in path.read_text(encoding="utf-8").splitlines():
        m=re.fullmatch(r"([0-9a-f]{64}) [ *](?:\./)?([A-Za-z0-9_.+-]+\.whl)",line)
        if not m or m[2] in rows:raise NaviError("Invalid or duplicate wheel manifest entry")
        rows[m[2]]=m[1]
    if not 1<=len(rows)<=40:raise NaviError("Wheel bundle count limit exceeded")
    core=[CORE.fullmatch(n) for n in rows if CORE.fullmatch(n)]
    if len(core)!=1:raise NaviError("Bundle requires exactly one NAVI universal wheel")
    total=0
    for n,digest in rows.items():
        p=_safe(path.parent/n)
        if not p.is_file():raise NaviError("Missing reviewed wheel")
        total+=p.stat().st_size
        if total>1024*1024*1024 or _sha(p)!=digest:raise NaviError("Wheel digest mismatch or bundle too large")
    return rows,core[0][1]

def _python(path):
    return path/("Scripts/python.exe" if os.name=="nt" else "bin/python")

def _inventory(root):
    h=hashlib.sha256();count=0;total=0
    for directory,dirs,files in os.walk(root,followlinks=False):
        d=Path(directory)
        for name in sorted(dirs+files):
            p=d/name;rel=p.relative_to(root).as_posix()
            if rel==RECEIPT:continue
            count+=1
            if count>30000:raise NaviError("Environment inventory exceeds limit")
            if p.is_symlink():kind="symlink";digest=os.readlink(p)
            elif hasattr(p,"is_junction") and p.is_junction():raise NaviError("Refusing environment junction")
            elif p.is_dir():kind="dir";digest=""
            elif p.is_file():
                kind="file";total+=p.stat().st_size
                if total>1024*1024*1024:raise NaviError("Environment inventory exceeds byte limit")
                digest=_sha(p)
            else:raise NaviError("Unsupported environment entry")
            h.update(json.dumps([rel,kind,digest],ensure_ascii=False,separators=(",",":")).encode()+b"\n")
        dirs.sort()
    return h.hexdigest(),count

def _run(args):
    # Explicit trusted wheel installation only; no shell or package index.
    env={k:v for k,v in os.environ.items() if not k.upper().startswith(("PIP_","PYTHON"))}
    env["PIP_NO_INDEX"]="1";env["PIP_DISABLE_PIP_VERSION_CHECK"]="1"
    return subprocess.run([str(x) for x in args],env=env,check=True,timeout=180,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def provision(manifest,expected,destination,apply=False):
    manifest=_safe(manifest);destination=_destination(destination)
    rows,version=_manifest(manifest,expected)
    if destination.exists():raise NaviError("Destination already exists; use a new versioned environment")
    if manifest.is_relative_to(destination) or destination.is_relative_to(manifest.parent):
        raise NaviError("Keep wheel bundle and installed environment separate")
    report={"status":"planned","version":version,"wheels":sorted(rows),"manifest_sha256":expected,
            "scope":"Explicit offline bundle; no agent installation, global PATH, index or existing environment changes. Digest verification is not publisher attestation."}
    if not apply:return report
    # Create exclusively; keep partial state if installation fails, never erase user data.
    destination.mkdir(mode=0o700,exist_ok=False)
    venv.EnvBuilder(with_pip=True,symlinks=False).create(destination)
    py=_python(destination)
    # Recheck exact input after environment creation.
    _manifest(manifest,expected)
    _run([py,"-I","-m","pip","--isolated","install","--no-index","--no-deps","--no-compile",*[manifest.parent/n for n in sorted(rows)]])
    _run([py,"-I","-m","pip","--isolated","check"])
    actual=_run([py,"-I","-B","-m","navi_core","--version"]).stdout.strip()
    if actual!=version:raise NaviError("Installed version differs from reviewed wheel")
    inventory,count=_inventory(destination)
    receipt={"schema_version":1,"version":version,"manifest_sha256":expected,
             "inventory_sha256":inventory,"entries":count,"destination_sha256":hashlib.sha256(os.fsencode(str(destination))).hexdigest()}
    with (destination/RECEIPT).open("x",encoding="utf-8") as f:json.dump(receipt,f,sort_keys=True)
    return {**report,"status":"installed","entries":count}

def uninstall(destination,apply=False):
    destination=_destination(destination)
    if not destination.is_dir():raise NaviError("Unknown environment")
    receipt=_safe(destination/RECEIPT)
    if not receipt.is_file() or receipt.stat().st_size>4096:raise NaviError("No managed installation receipt")
    data=json.loads(receipt.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data)!={"schema_version","version","manifest_sha256","inventory_sha256","entries","destination_sha256"} or data["schema_version"]!=1 or data["destination_sha256"]!=hashlib.sha256(os.fsencode(str(destination))).hexdigest():
        raise NaviError("Invalid installation receipt")
    digest,count=_inventory(destination)
    same=digest==data["inventory_sha256"] and count==data["entries"]
    result={"status":"planned" if same else "review-required","version":data["version"],"unchanged":same,
            "scope":"Only exact unchanged managed environment may be removed. Modified environments require manual owner review; no project data is targeted."}
    if not apply or not same:return result
    if _inventory(destination)!=(digest,count):raise NaviError("Environment changed before removal")
    shutil.rmtree(destination)
    return {**result,"status":"removed"}
