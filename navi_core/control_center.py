"""Read-only local portfolio dashboard. No server, network, project mutation or raw memory."""
import html
import json
from pathlib import Path
from . import __version__,nef,runtime
from .cli import NaviError,load_manifest
from .skill_registry import write_private
import os

def portfolio(config):
    if type(config) is not dict or set(config)!={"schema_version","projects"} or config["schema_version"]!=1 or type(config["projects"]) is not list or not 1<=len(config["projects"])<=30:
        raise NaviError("Expected 1..30 explicit project entries")
    rows=[];seen=set()
    for entry in config["projects"]:
        if type(entry) is not dict or set(entry)!={"root","profile","store"} or not isinstance(entry["root"],str) or not isinstance(entry["profile"],str) or (entry["store"] is not None and not isinstance(entry["store"],str)):
            raise NaviError("Invalid portfolio entry")
        root=Path(entry["root"])
        if not root.is_absolute():raise NaviError("Use explicit absolute local project paths")
        root=root.resolve(strict=True)
        if root in seen:raise NaviError("Duplicate portfolio project")
        seen.add(root)
        audit=nef.inspect(root,entry["profile"])
        counts={s:sum(x["state"]==s for x in audit["references"]) for s in ("present","not-found","review-required")}
        row={"project":root.name,"profile":audit["profile"],"references":counts,"audit":audit["status"],"sessions":None}
        if entry["store"] is not None:
            store=Path(entry["store"])
            directory,_=nef._outside(root,store)
            if (directory/"runtime.sqlite3").exists():
                result=runtime.sessions(root,store)["sessions"]
                row["sessions"]={state:sum(x["state"]==state for x in result) for state in ("awaiting-brief","clarify","ready","executing","review","paused","closed")}
                row["session_count_scope"]="latest 100"
        rows.append(row)
    return {"status":"inspected","core_version":__version__,"projects":rows,
            "scope":"Private local metadata only; no absolute paths, session text, credentials or graph/source content. Not production certification."}

def render(data):
    e=lambda value:html.escape(str(value),quote=True)
    cards=[]
    for row in data["projects"]:
        refs=row["references"];sessions=row["sessions"]
        session_text="Not configured" if sessions is None else ", ".join(e(k)+": "+e(v) for k,v in sessions.items())
        cards.append("<article><h2>"+e(row["project"])+"</h2><p>"+e(row["profile"])+" · "+e(row["audit"])+"</p><dl><dt>References present</dt><dd>"+e(refs["present"])+"</dd><dt>Not found (advisory)</dt><dd>"+e(refs["not-found"])+"</dd><dt>Review required</dt><dd>"+e(refs["review-required"])+"</dd></dl><p>Sessions: "+session_text+"</p></article>")
    integration_html=""
    if "integrations" in data:
        report=data["integrations"]
        integration_html="<section><h2>Integration audit: "+e(report["status"])+"</h2><ul>"+ "".join("<li>"+e(r["repository"])+": "+e(r["state"])+"</li>" for r in report["repositories"])+"</ul><p>Universe: "+e(report["universe"]["state"])+"</p><small>"+e(report["scope"])+"</small></section>"
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>NAVI Control Center</title><style>body{background:#07131d;color:#dce9ef;font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px}h1{color:#65cbd5}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}article{background:#102331;border:1px solid #285062;border-radius:12px;padding:20px}h2{overflow-wrap:anywhere}dt{color:#a5becd}dd{margin:3px 0 12px;font-size:1.3rem}small{color:#a5becd}</style>
<h1>NAVI Control Center</h1><p>Local engineering overview · """+e(data["core_version"])+"""</p><main>"""+ "".join(cards)+"""</main>"""+integration_html+"""<p><small>"""+e(data["scope"])+"""</small></p></html>"""

def save_html(path,data):
    path=Path(path).absolute()
    if path.is_symlink() or any(p.is_symlink() or (hasattr(p,"is_junction") and p.is_junction()) for p in path.parents):
        raise NaviError("Refusing linked output")
    if any((p/".git").exists() for p in path.parents):
        raise NaviError("Dashboard output must be outside Git worktrees")
    raw=render(data).encode("utf-8")
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f:f.write(raw)
