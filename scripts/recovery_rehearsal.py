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

def rehearsal(name,branch,export_dir=None):
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
        if export_dir is not None:
            export_dir.mkdir(mode=0o700,exist_ok=False)
            # Only the public recipient certificate is checked in. Private key never enters CI.
            cert=Path(__file__).resolve().parents[1]/"docs/recovery-recipient.pem"
            der=subprocess.check_output(["openssl","x509","-in",str(cert),"-outform","DER"])
            if hashlib.sha256(der).hexdigest()!="37dab806e8d5a75fe0fe0b1ac2e27cb4b82116de6aeacd2214c6ea357e8cd7e9":
                raise RuntimeError("Recovery certificate fingerprint mismatch")
            encrypted=export_dir/"recovery.bundle.cms"
            subprocess.run(["openssl","cms","-encrypt","-binary","-aes-256-gcm","-in",str(bundle),"-out",str(encrypted),"-outform","DER",str(cert)],check=True,timeout=120,capture_output=True)
            with encrypted.open("rb") as f:
                cipher_hash=hashlib.file_digest(f,"sha256").hexdigest()
            (export_dir/"receipt.json").write_text(json.dumps({"repository":name,"default_branch":branch,"commit":head,"refs":original,"bundle_sha256":h.hexdigest(),"bundle_bytes":size,"cipher_sha256":cipher_hash,"recipient_sha256":hashlib.sha256(der).hexdigest(),"scope":"encrypted Git bundle; Git objects/advertised refs only"},indent=2),encoding="utf-8")
        return {"repository":name,"default_branch":branch,"commit":head,"refs":len(original),"bundle_sha256":h.hexdigest(),"bundle_bytes":size,"status":"passed","elapsed_seconds":round(time.monotonic()-started,3)}

def main():
    if len(sys.argv) not in (3,4) or sys.argv[1] not in PROJECTS:
        raise SystemExit("Usage: recovery_rehearsal.py <allowlisted public repo> <new report>")
    name=sys.argv[1];out=Path(sys.argv[2])
    try:row=rehearsal(name,PROJECTS[name],Path(sys.argv[3]) if len(sys.argv)==4 else None)
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        row={"repository":name,"status":"failed","error_type":type(exc).__name__}
    row["scope"]="encrypted recovery export" if len(sys.argv)==4 else "ephemeral-public-restore-rehearsal; bundle destroyed; no retained backup"
    with out.open("x",encoding="utf-8") as f:json.dump(row,f,indent=2)
    print(json.dumps(row,indent=2))
    return 0 if row["status"]=="passed" else 1

if __name__=="__main__":raise SystemExit(main())
