"""Build a reviewed synthetic wheel bundle and exercise actual offline provision."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from navi_core import installer

def main():
    source=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp).resolve();bundle=base/"bundle";bundle.mkdir()
        subprocess.run([sys.executable,"-m","pip","download","--only-binary=:all:","-r",str(source/"requirements-ci.txt"),"-d",str(bundle)],check=True,timeout=180)
        subprocess.run([sys.executable,"-m","pip","wheel","--no-deps","--no-build-isolation",str(source),"-w",str(bundle)],check=True,timeout=180)
        manifest=bundle/"WHEELS.sha256"
        manifest.write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.name+"\n" for p in sorted(bundle.glob("*.whl"))),encoding="utf-8")
        digest=hashlib.sha256(manifest.read_bytes()).hexdigest()
        target=base/"env"
        assert installer.provision(manifest,digest,target)["status"]=="planned"
        assert not target.exists()
        result=installer.provision(manifest,digest,target,True)
        assert result["status"]=="installed",result
        assert installer.uninstall(target,True)["status"]=="removed"
        assert not target.exists()
        print("Offline wheel bundle provision, version check and exact-inventory removal passed")

if __name__=="__main__":main()
