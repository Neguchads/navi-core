"""Manual authenticated host challenge; no inference or credential access."""
import hashlib
import json
from pathlib import Path
import re
import secrets
from . import agent_bridge
from .cli import NaviError
from .skill_registry import read_json,write_private

HOSTS=tuple(agent_bridge.TARGETS)
CASE={"dependencies":{"compile":["lint"],"lint":[],"test":["compile"]}}
PROMPT="""This is a public synthetic NAVI host acceptance test. Read the repository
instructions applicable to this host and TASK.json. Return only a JSON object
with the keys challenge and order. Copy the challenge from the repository
instructions and list every task once in a valid dependency order.
Do not edit files, execute commands, use the network, or read any other path.
"""
def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def create(directory,host=None):
    if host is not None and host not in HOSTS:
        raise NaviError("Unknown lab host")
    selected=(host,) if host is not None else HOSTS
    root=Path(directory).absolute()
    if root.exists() or root.is_symlink() or any(p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()) for p in root.parents):
        raise NaviError("Lab directory must be new and unlinked")
    root.mkdir(mode=0o700)
    rows={}
    for host in selected:
        workspace=root/host
        workspace.mkdir(mode=0o700)
        target=workspace/agent_bridge.TARGETS[host]
        target.parent.mkdir(parents=True,exist_ok=True)
        nonce=secrets.token_hex(16)
        raw=agent_bridge.render(host,"documentation")+("\n## Synthetic acceptance challenge\nChallenge: "+nonce+"\n").encode()
        target.write_bytes(raw)
        task=(json.dumps(CASE,sort_keys=True)+"\n").encode()
        (workspace/"TASK.json").write_bytes(task)
        rows[host]={"challenge":nonce,"instruction_sha256":sha(raw),"task_sha256":sha(task)}
    write_private(root/"expected.json",{"schema_version":1,"scope":"private-local-host-lab","hosts":rows})
    (root/"PROMPT.txt").write_text(PROMPT,encoding="utf-8")
    return {"status":"prepared","hosts":list(selected),"scope":"Manual challenge only; no authenticated host invoked. Open only each individual workspace; keep expected.json outside host context."}

def check(directory,host,answer,reported_version):
    if host not in HOSTS or not isinstance(reported_version,str) or not 1<=len(reported_version)<=120 or any(ord(c)<32 for c in reported_version):
        raise NaviError("Explicit host and reported version required")
    root=Path(directory).resolve(strict=True)
    expected=read_json(root/"expected.json")
    if expected.get("schema_version")!=1 or expected.get("scope")!="private-local-host-lab":
        raise NaviError("Invalid lab")
    if host not in expected["hosts"]:
        raise NaviError("Host was not prepared in this lab")
    e=expected["hosts"][host]
    workspace=agent_bridge.safe_target(root,host)
    paths=(agent_bridge.TARGETS[host],"TASK.json")
    digests=[]
    for p in paths:
        target=agent_bridge.safe_target(workspace,p)
        if not target.is_file() or target.stat().st_size>32768:raise NaviError("Invalid challenge file")
        digests.append(sha(target.read_bytes()))
    integrity=digests==[e["instruction_sha256"],e["task_sha256"]]
    nonce=type(answer) is dict and set(answer)=={"challenge","order"} and answer["challenge"]==e["challenge"]
    order=answer.get("order") if type(answer) is dict else None
    correct=type(order) is list and order==["lint","compile","test"]
    return {"status":"passed" if integrity and nonce and correct else "failed","host":host,"reported_version":reported_version,
            "gates":{"workspace_integrity":integrity,"challenge_response":nonce,"dependency_order":correct},
            "scope":"Manually submitted host response. Not cryptographic proof of host identity, automatic instruction ingestion, or sandbox compliance."}
