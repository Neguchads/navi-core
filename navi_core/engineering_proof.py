"""Actual trusted profile gate receipt. Not a sandbox or signed attestation."""
import datetime
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from .cli import NaviError, load_manifest
from .skill_registry import read_json, write_private

MAX_LOG=64*1024*1024

def git(root,*args):
    return subprocess.run(["git","-C",str(root),*args],capture_output=True,check=True,timeout=30).stdout.decode("utf-8").strip()

def revision(root):
    if Path(git(root,"rev-parse","--show-toplevel")).resolve(strict=True)!=root:
        raise NaviError("Proof root must be the Git repository root")
    sha=git(root,"rev-parse","HEAD")
    if not re.fullmatch("[a-f0-9]{40}",sha):raise NaviError("Unsupported Git object format")
    return sha,not bool(git(root,"status","--porcelain=v1","--untracked-files=all"))

def log_digest(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size>MAX_LOG:
        raise NaviError("Log missing, linked or exceeds integrity check limit")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def capture(root,output,timeout=900):
    root=Path(root).resolve(strict=True)
    output=Path(output).absolute()
    if type(timeout) is not int or not 1<=timeout<=3600:raise NaviError("Invalid gate timeout")
    if output.exists() or output.is_symlink() or any(p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()) for p in output.parents):
        raise NaviError("Output directory must be new and unlinked")
    if output.resolve().is_relative_to(root):raise NaviError("Keep receipts outside Git working tree")
    manifest=load_manifest(root)
    head,clean=revision(root)
    if not clean:raise NaviError("Proof requires a clean working tree")
    output.mkdir(mode=0o700)
    log=output/"verification.log"
    started=stamp();mono=time.perf_counter_ns()
    command=[sys.executable,"-I","-m","navi_core","verify","--root",str(root),"--execute"]
    code=None;reason=None
    with os.fdopen(os.open(log,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),"wb") as f:
        try:code=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,check=False).returncode
        except subprocess.TimeoutExpired:reason="timeout"
    try:after,after_clean=revision(root)
    except (NaviError,OSError,subprocess.SubprocessError):after=None;after_clean=False
    valid=after==head and after_clean
    if not valid:reason="revision-or-worktree-changed"
    try:digest=log_digest(log)
    except NaviError:digest=None;reason="log-integrity-unavailable"
    status="passed" if code==0 and valid and digest else "failed"
    receipt={"schema_version":1,"kind":"local-profile-gate","scope":"private-local","status":status,
             "commit":head,"commit_after":after,"clean_after":after_clean,"profile":manifest["project"]["profile"],
             "command":["python","-I","-m","navi_core","verify","--execute"],"exit_code":code,"started_at":started,
             "finished_at":stamp(),"elapsed_ns":time.perf_counter_ns()-mono,"log_sha256":digest,"reason":reason,
             "limitations":"Trusted project code; no sandbox or process-tree cancellation. Unsigned receipt. Profile gate only."}
    write_private(output/"receipt.json",receipt)
    return {"status":status,"commit":head,"profile":receipt["profile"],"log_sha256":digest,"reason":reason,
            "scope":"Private receipt created; log not printed or uploaded."}

def check(directory):
    directory=Path(directory)
    if directory.is_symlink() or not directory.is_dir():raise NaviError("Invalid receipt directory")
    r=read_json(directory/"receipt.json")
    if r["schema_version"]!=1 or r["kind"]!="local-profile-gate" or r["scope"]!="private-local":raise NaviError("Invalid receipt")
    matches=r["log_sha256"]==log_digest(directory/"verification.log")
    passed=matches and r["status"]=="passed" and type(r["exit_code"]) is int and r["exit_code"]==0 and r["clean_after"] is True and r["commit"]==r["commit_after"] and bool(re.fullmatch("[a-f0-9]{40}",r["commit"]))
    return {"status":"passed" if passed else "failed","log_integrity":matches,"scope":"Unsigned local consistency only; not authenticated evidence."}
