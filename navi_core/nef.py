"""NEF advisory references, additive scaffolding, and explicit intake/learning gates."""
import hashlib
import json
import os
from pathlib import Path
import re
from .cli import NaviError, RES, REGISTRY, load_manifest, validate
from .agent_bridge import safe_target
from .skill_registry import read_json, write_private

def catalog():
    return json.loads(RES.joinpath("profiles/nef.json").read_text(encoding="utf-8"))

def standard(profile=None):
    data=catalog()
    if profile is not None and profile not in data["profiles"]:
        raise NaviError("Unknown NEF profile")
    def details(name):
        return {**data["profiles"][name],"verification_gate":REGISTRY.get(name,{}).get("status","not-registered")}
    return {"version":data["version"],"name":"NAVI Engineering Framework (NEF)",
            "scope":"Advisory references; paths are alternatives, not mandatory layout.",
            "common":data["common"],"profiles":{n:details(n) for n in ([profile] if profile else data["profiles"])}}

def project(root,profile):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():
        raise NaviError("Project root must be a directory")
    if (root/".navi/project.toml").exists() or (root/".navi/project.toml").is_symlink():
        declared=load_manifest(root)["project"]["profile"]
        if profile is not None and profile!=declared:
            raise NaviError("Explicit profile conflicts with project manifest")
        profile=declared
    if profile not in catalog()["profiles"]:
        raise NaviError("Select a NEF profile or initialize a project manifest")
    return root,profile

def inspect(root,profile=None):
    root,profile=project(root,profile)
    data=catalog()
    rows=[]
    for item in data["common"]:
        found=[]; blocked=[]
        for rel in item["alternatives"]:
            try:
                p=safe_target(root,rel)
            except NaviError:
                blocked.append(rel);continue
            if p.is_file() and item["kind"] in ("file","either") and p.stat().st_size>0:
                found.append(rel)
            elif p.is_dir() and item["kind"]=="either":
                found.append(rel)
            elif p.exists():
                blocked.append(rel)
        state="present" if found else ("review-required" if blocked else "not-found")
        rows.append({"id":item["id"],"priority":item["priority"],"state":state,
                     "matches":found,"blocked":blocked,"suggested_path":item["preferred"]})
    return {"status":"review-required" if any(x["blocked"] for x in rows) else "inspected",
            "profile":profile,"references":rows,"architecture":standard(profile)["profiles"][profile],
            "scope":"Presence only; content, architectural boundaries, license and behavior require review. Missing references are not conformance failures."}

def scaffold(root,profile=None,sections=None,apply=False,include_folders=False):
    root,profile=project(root,profile)
    data=catalog(); audit=inspect(root,profile)
    selected=set(sections or ("overview","architecture","roadmap","handoff"))
    known={x["id"] for x in data["common"] if x["preferred"] in data["templates"]}
    if not selected<=known:
        raise NaviError("Unknown or non-generatable section (license must be selected by owner)")
    operations=[]; review=[]
    for row in audit["references"]:
        if row["id"] not in selected:continue
        if row["blocked"]:
            review.append(row["id"]);continue
        if row["state"]=="not-found":
            rel=row["suggested_path"]
            operations.append({"path":rel,"kind":"file","action":"create","template":data["templates"][rel]})
    if include_folders:
        for rel in data["profiles"][profile]["folders"]:
            try:
                p=safe_target(root,rel)
                if p.exists() and not p.is_dir():review.append(rel)
                elif not p.exists():operations.append({"path":rel,"kind":"directory","action":"create"})
            except NaviError:review.append(rel)
    if review:
        return {"status":"blocked","profile":profile,"review":review,"operations":[]}
    # Preflight every destination including parent file collisions before writes.
    for op in operations:
        p=safe_target(root,op["path"])
        if p.exists() or any(q.exists() and not q.is_dir() for q in p.parents if q!=root):
            raise NaviError("Destination or parent conflict")
    report={"status":"planned","profile":profile,"operations":operations,
            "scope":"Additive only; no overwrite, move, delete, code generation or automatic license. Folder creation is opt-in."}
    if not apply:return report
    created=[]
    try:
        for op in operations:
            p=safe_target(root,op["path"])
            if op["kind"]=="directory":
                p.mkdir(parents=True,exist_ok=False)
            else:
                p.parent.mkdir(parents=True,exist_ok=True)
                with safe_target(root,op["path"]).open("xb") as f:
                    f.write(op["template"].encode("utf-8"))
            created.append(op["path"])
    except OSError as exc:
        raise NaviError("Scaffold interrupted; inspect created paths: "+", ".join(created)) from exc
    return {**report,"status":"applied","created":created}

def migration(root,profile=None,apply=False):
    # Safe automation: create missing core documentation only; preserve all existing layout.
    root,profile=project(root,profile)
    report=scaffold(root,profile,apply=apply)
    return {**report,"migration":"additive-documentation","manual_review":["Map existing module boundaries and documentation aliases.",
        "Review actual import graph and tests before any relocation.",
        "For breaking moves, require owner approval, clean backup, tests and rollback plan."],
        "scope":"No rename, delete, overwrite or automatic code refactor."}

def intake(brief):
    validate("brief",brief)
    missing=[]
    for key in ("goal","deliverable"):
        if not brief[key].strip():missing.append(key)
    if brief["complexity"]!="simple" and not any(x.strip() for x in brief["acceptance"]):
        missing.append("acceptance")
    if brief["complexity"]!="simple" and brief["constraints_state"]=="unknown":
        missing.append("constraints")
    unresolved=[x for x in brief["questions"] if x.strip()]
    if brief["ambiguity"]=="material" and not unresolved:
        missing.append("clarifying-question")
    if brief["risk"] in ("high","critical") and not brief["approved"]:
        missing.append("approval")
    return {"status":"clarify" if missing or unresolved or brief["ambiguity"]=="material" else "ready",
            "missing_fields":missing,"questions":unresolved,
            "scope":"Checks agent-supplied structured brief, not semantic understanding or host enforcement. Ready is not execution authorization."}

def _outside(root,path):
    root=Path(root).resolve(strict=True)
    path=Path(path).absolute()
    if path.is_symlink() or any(p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()) for p in path.parents):
        raise NaviError("Use an unlinked canonical private store path")
    resolved=path.resolve()
    if resolved.is_relative_to(root) or any((p/".git").exists() for p in (resolved,*resolved.parents)):
        raise NaviError("Private lesson store must be outside project and Git worktrees")
    return resolved,hashlib.sha256(os.fsencode(str(root))).hexdigest()

def learn(root,store,lesson,approve=False):
    validate("lesson",lesson)
    store,scope=_outside(root,store)
    # Approval is a local operator assertion, not attested identity. Do not save raw prompts.
    if not approve:
        return {"status":"review-required","id":lesson["id"],"scope":"Review sanitized summary and source reference; no write."}
    if not store.is_dir():
        raise NaviError("Create a private store directory explicitly")
    record={"schema_version":1,"scope":"private-local","project_scope":scope,"lesson":lesson}
    path=store/(lesson["id"]+".json")
    write_private(path,record)
    return {"status":"saved","id":lesson["id"],"scope":"Private local reviewed lesson; no model training, network or policy mutation."}

def recall(root,store,ids,budget=8192):
    store,scope=_outside(root,store)
    if not store.is_dir() or type(budget) is not int or not 1<=budget<=32768 or not 1<=len(ids)<=20 or len(set(ids))!=len(ids):
        raise NaviError("Invalid lesson selection or budget")
    records=[]
    for ident in ids:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}",ident):raise NaviError("Invalid lesson id")
        data=read_json(store/(ident+".json"))
        if set(data)!={"schema_version","scope","project_scope","lesson"} or data["schema_version"]!=1 or data["scope"]!="private-local" or data["project_scope"]!=scope:
            raise NaviError("Lesson belongs to another project or is invalid")
        lesson=validate("lesson",data["lesson"])
        if lesson["id"]!=ident:raise NaviError("Lesson identity mismatch")
        records.append(lesson)
    out={"status":"selected","scope":"private-local; advisory data, never authorization","lessons":records}
    if len(json.dumps(out,ensure_ascii=False,indent=2).encode("utf-8"))+1>budget:
        raise NaviError("Lesson context exceeds budget")
    return out
