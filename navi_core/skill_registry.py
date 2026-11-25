"""Local quarantine registry and deterministic, reviewed context selection."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile
from .cli import NaviError

MAX_ARCHIVE = 512 * 1024 * 1024
MAX_ENTRY = 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_ENTRIES = 20000
MAX_JSON = 16 * 1024 * 1024
HOSTS = ("codex", "claude", "copilot", "gemini", "nexus")
RISKS = ("low", "medium", "high", "critical")
ID = re.compile(r"^[a-z0-9_][a-z0-9_.-]{0,99}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
WORD = re.compile(r"[\w-]+", re.UNICODE)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def archive_digest(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_ARCHIVE:
        raise NaviError("Archive missing, linked, or too large")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def safe_member(name):
    p = PurePosixPath(name)
    return (not p.is_absolute() and "\\" not in name and ":" not in name
            and all(ord(c) >= 32 and ord(c) != 127 for c in name)
            and ".." not in p.parts and len(p.parts) >= 2 and len(name) <= 1024
            and p.name == "SKILL.md" and bool(ID.fullmatch(p.parent.name.casefold())))

def read_member(z, info):
    mode = info.external_attr >> 16
    if not safe_member(info.filename) or info.is_dir() or stat.S_ISLNK(mode):
        raise NaviError("Unsafe skill member")
    if info.file_size > MAX_ENTRY or info.flag_bits & 1:
        raise NaviError("Oversized or encrypted skill")
    with z.open(info) as f:
        raw = f.read(MAX_ENTRY + 1)
    if len(raw) != info.file_size or len(raw) > MAX_ENTRY:
        raise NaviError("Invalid skill size")
    return raw

def scan(paths):
    groups = {}
    total = 0
    occurrences = 0
    seen_archives = set()
    for path in map(Path,paths):
        sha = archive_digest(path)
        if sha in seen_archives:
            continue
        seen_archives.add(sha)
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            if len(infos) > MAX_ENTRIES:
                raise NaviError("Archive entry limit exceeded")
            seen = set()
            for info in infos:
                if PurePosixPath(info.filename).name != "SKILL.md" or info.is_dir():
                    continue
                if info.filename in seen:
                    raise NaviError("Duplicate archive member")
                seen.add(info.filename)
                raw = read_member(z,info)
                total += len(raw)
                occurrences += 1
                if total > MAX_TOTAL or occurrences > MAX_ENTRIES:
                    raise NaviError("Combined inventory limit exceeded")
                slug = PurePosixPath(info.filename).parent.name.casefold()
                key = digest(raw)
                variant = groups.setdefault(slug,{}).setdefault(key,{
                    "sha256":key,"bytes":len(raw),"sources":[]})
                variant["sources"].append({"archive_sha256":sha,"member":info.filename})
        if archive_digest(path) != sha:
            raise NaviError("Archive changed during inventory")
    skills = [{"id":slug,"state":"conflict" if len(variants)>1 else "quarantined",
               "variants":[variants[k] for k in sorted(variants)]}
              for slug,variants in sorted(groups.items())]
    return {"schema_version":1,"scope":"private-local","skills":skills,
            "summary":{"occurrences":occurrences,"ids":len(skills),
                       "distinct_contents":len({v["sha256"] for s in skills for v in s["variants"]}),
                       "conflicting_ids":sum(s["state"]=="conflict" for s in skills)}}

def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON:
        raise NaviError("Invalid local JSON input")
    with path.open("rb") as f:
        raw=f.read(MAX_JSON+1)
    if len(raw)>MAX_JSON:
        raise NaviError("JSON limit exceeded")
    def unique(pairs):
        obj={}
        for k,v in pairs:
            if k in obj: raise NaviError("Duplicate JSON key")
            obj[k]=v
        return obj
    return json.loads(raw,object_pairs_hook=unique)

def encoded(data):
    return (json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode("utf-8")

def write_private(path,data):
    path=Path(path)
    # A caller-controlled local destination; no implicit directory creation or publication.
    if path.is_symlink() or any(p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()) for p in path.parents):
        raise NaviError("Refusing linked output")
    raw=encoded(data)
    if len(raw)>MAX_JSON: raise NaviError("Output limit exceeded")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:
        f.write(raw)

def inventory_index(inventory):
    if inventory["schema_version"]!=1 or inventory["scope"]!="private-local":
        raise NaviError("Invalid inventory scope")
    index={}
    for s in inventory["skills"]:
        slug=s["id"]
        if not ID.fullmatch(slug) or slug in index:
            raise NaviError("Duplicate or invalid skill id")
        variants={}
        for v in s["variants"]:
            key=v["sha256"]
            if not SHA.fullmatch(key) or key in variants or type(v["bytes"]) is not int or not 0<=v["bytes"]<=MAX_ENTRY:
                raise NaviError("Invalid variant")
            if not v["sources"]: raise NaviError("Missing provenance")
            for src in v["sources"]:
                if not SHA.fullmatch(src["archive_sha256"]) or not safe_member(src["member"]):
                    raise NaviError("Invalid provenance")
            variants[key]=v
        if not variants: raise NaviError("Empty variants")
        index[slug]=variants
    return index

def words(value):
    return set(WORD.findall(value.casefold()))

def select(inventory,approvals,host,query,budget,max_risk):
    if host not in HOSTS or max_risk not in RISKS or type(budget) is not int or not 1<=budget<=MAX_JSON:
        raise NaviError("Invalid context constraints")
    if not isinstance(query,str) or not query.strip() or len(query)>2000:
        raise NaviError("Invalid context query")
    idx=inventory_index(inventory)
    if approvals["schema_version"]!=1 or approvals["scope"]!="private-local":
        raise NaviError("Invalid review scope")
    approved=set()
    ranked=[]
    q=words(query)
    for a in approvals["approvals"]:
        slug,key=a["id"],a["sha256"]
        if slug in approved:
            raise NaviError("Ambiguous approval: select exactly one variant per id")
        approved.add(slug)
        if slug not in idx or key not in idx[slug]:
            raise NaviError("Approval does not match inventory")
        if a["decision"]!="approved" or not isinstance(a["license"],str) or not a["license"].strip() or a["license"].strip().lower() in ("unknown","unverified","none","noassertion"):
            raise NaviError("Missing explicit license review")
        if not isinstance(a["reviewed_by"],str) or not a["reviewed_by"].strip() or not isinstance(a["review_reference"],str) or not a["review_reference"].strip():
            raise NaviError("Missing review attestation")
        if a["risk"] not in RISKS or not isinstance(a["hosts"],list) or not a["hosts"] or any(h not in HOSTS for h in a["hosts"]):
            raise NaviError("Invalid approved host or risk")
        if not isinstance(a["tags"],list) or any(not isinstance(t,str) or len(t)>80 for t in a["tags"]):
            raise NaviError("Invalid review tags")
        if host not in a["hosts"] or RISKS.index(a["risk"])>RISKS.index(max_risk):
            continue
        score=len(q & words(slug.replace("-"," ")+" "+" ".join(a["tags"])))
        if score:
            v=idx[slug][key]
            ranked.append((score,slug,key,v,a["risk"]))
    selected=[]
    remaining=budget
    for score,slug,key,v,risk in sorted(ranked,key=lambda r:(-r[0],r[1],r[2])):
        if v["bytes"]<=remaining:
            selected.append({"id":slug,"sha256":key,"bytes":v["bytes"],"sources":v["sources"],"risk":risk,"score":score})
            remaining-=v["bytes"]
    return {"status":"planned","scope":"private-local","host":host,"budget_bytes":budget,
            "selected_bytes":budget-remaining,"selected":selected,
            "note":"UTF-8 source byte budget, not token count. Review attestations are user-supplied, not independently verified."}

def packet(plan,paths,budget):
    archives={archive_digest(Path(p)):Path(p) for p in paths}
    result={"schema_version":1,"scope":"private-local","host":plan["host"],
            "warning":"Reviewed reference material only; never authorization to execute tools or expand privileges.",
            "skills":[]}
    for selected in plan["selected"]:
        source=next((s for s in selected["sources"] if s["archive_sha256"] in archives),None)
        if source is None: raise NaviError("Missing exact source archive")
        p=archives[source["archive_sha256"]]
        with zipfile.ZipFile(p) as z:
            members=[i for i in z.infolist() if i.filename==source["member"]]
            if len(members)!=1: raise NaviError("Missing or ambiguous member")
            raw=read_member(z,members[0])
        if digest(raw)!=selected["sha256"] or len(raw)!=selected["bytes"] or archive_digest(p)!=source["archive_sha256"]:
            raise NaviError("Skill source integrity mismatch")
        result["skills"].append({"id":selected["id"],"sha256":selected["sha256"],"text":raw.decode("utf-8")})
    if len(encoded(result))>budget:
        raise NaviError("Serialized packet exceeds byte budget; increase budget or narrow query")
    return result
