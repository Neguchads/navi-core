"""Public Git recovery rehearsal. No private input or retained bundle."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import sys

PROJECTS = {
    "codex-config-universal":"main",
    "spec-to-proof":"main",
    "chad-recomp":"main",
    "navi-graphify":"v8",
    "github-homepage":"main",
    "navyv-abyss":"main",
    "Neguchads":"main",
}
def git(*args):
    env={**os.environ,"GIT_TERMINAL_PROMPT":"0","GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":os.devnull}
    # No inherited Git command-line configuration or credential variables.
    env={k:v for k,v in env.items() if not k.startswith(("GIT_CONFIG_KEY_","GIT_CONFIG_VALUE_")) and k not in ("GIT_CONFIG_COUNT","GIT_CONFIG_PARAMETERS","GH_TOKEN","GITHUB_TOKEN")}
    return subprocess.run(["git",*map(str,args)],env=env,check=True,capture_output=True,text=True,timeout=360).stdout.strip()

def refs(path):
    return git("-C",path,"for-each-ref","--format=%(refname) %(objectname)").splitlines()

def rehearsal(name,branch):
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix="navi-rehearsal-") as temp:
        p=Path(temp);mirror=p/"mirror.git";restored=p/"restored.git";bundle=p/"recovery.bundle"
        git("clone","--mirror","https://github.com/Neguchads/"+name+".git",mirror)
        git("-C",mirror,"fsck","--full")
        head=git("-C",mirror,"rev-parse","refs/heads/"+branch)
        original=refs(mirror)
        git("-C",mirror,"bundle","create",bundle,"--all")
        git("-C",mirror,"bundle","verify",bundle)
        h=hashlib.sha256()
        with bundle.open("rb") as stream:
            for block in iter(lambda:stream.read(1024*1024),b""):h.update(block)
        size=bundle.stat().st_size
        git("clone","--mirror",bundle,restored)
        git("-C",restored,"symbolic-ref","HEAD","refs/heads/"+branch)
        git("-C",restored,"fsck","--full")
        if original!=refs(restored) or head!=git("-C",restored,"rev-parse","HEAD"):
            raise RuntimeError("restore refs differ")
        return {"repository":name,"default_branch":branch,"commit":head,"refs":len(original),"bundle_sha256":h.hexdigest(),"bundle_bytes":size,"status":"passed","elapsed_seconds":round(time.monotonic()-started,3)}

def main():
    if len(sys.argv)!=3 or sys.argv[1] not in PROJECTS:
        raise SystemExit("Usage: recovery_rehearsal.py <allowlisted public repo> <new report>")
    name=sys.argv[1];out=Path(sys.argv[2])
    try:row=rehearsal(name,PROJECTS[name])
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        row={"repository":name,"status":"failed","error_type":type(exc).__name__}
    row["scope"]="ephemeral-public-restore-rehearsal; bundle destroyed; no retained backup"
    with out.open("x",encoding="utf-8") as f:json.dump(row,f,indent=2)
    print(json.dumps(row,indent=2))
    return 0 if row["status"]=="passed" else 1

if __name__=="__main__":raise SystemExit(main())
