"""Provider-neutral local session lifecycle. No host launch, transcript or prompt capture."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from . import nef, assist
from .cli import NaviError, load_manifest
from .agent_bridge import safe_target

HOSTS=("codex","claude","gemini","copilot","manus","generic","none")
EXECUTABLES={"codex":"codex","claude":"claude","gemini":"gemini","copilot":"copilot"}
HOOKS={"codex":(".codex/hooks.json","SessionStart","UserPromptSubmit"),
       "claude":(".claude/settings.local.json","SessionStart","UserPromptSubmit"),
       "gemini":(".gemini/settings.json","SessionStart","BeforeAgent")}
ID=re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
SCOPE="Local managed session only; not host authentication, a sandbox or permission authority."

def discover():
    return {"status":"inspected","hosts":[{"host":h,"cli_on_path":bool(shutil.which(EXECUTABLES[h])) if h in EXECUTABLES else None,
        "native_context_hook_candidate":h in HOOKS,"portable_context":h!="none",
        "authenticated":None,"host_acceptance":"not-verified"} for h in HOSTS],
        "scope":"PATH presence only; no command invocation, account discovery, installation or provider selection."}

def capabilities(host):
    if host not in HOSTS:raise NaviError("Select a known host or generic")
    return {"status":"described","host":host,"portable_context":host!="none",
            "managed_sessions":True,"managed_intake":True,"native_context_hooks":list(HOOKS[host][1:]) if host in HOOKS else [],
            "native_hook_acceptance":"pending" if host in HOOKS else "not-implemented",
            "native_write_interception":False,"automatic_learning":False,
            "scope":"Declared adapter capabilities, not observed authenticated host behavior."}

def _project(root):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise NaviError("Project root must be a directory")
    return root

def _host(root,host):
    if host is None:
        try:host=load_manifest(root)["agents"].get("host")
        except (NaviError,OSError):host=None
    if host not in HOSTS:raise NaviError("Choose one host explicitly or set a preferred host")
    return host

def _ident(ident):
    if not isinstance(ident,str) or not ID.fullmatch(ident):raise NaviError("Invalid local session id")
    return ident

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()

def _now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def _db(root,store,create=False):
    directory,scope=nef._outside(root,store)
    if not directory.is_dir():raise NaviError("Create a private store outside Git first")
    path=safe_target(directory,"runtime.sqlite3")
    if not path.exists():
        if not create:raise NaviError("Runtime store not initialized")
        try:
            fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            os.close(fd)
        except FileExistsError:pass
    if not path.is_file():raise NaviError("Invalid runtime store")
    for name in ("runtime.sqlite3-journal","runtime.sqlite3-wal","runtime.sqlite3-shm"):
        p=safe_target(directory,name)
        if p.exists() and not p.is_file():raise NaviError("Invalid SQLite sidecar")
    con=sqlite3.connect(path,timeout=5,isolation_level=None)
    con.row_factory=sqlite3.Row
    try:
        con.execute("PRAGMA trusted_schema=OFF")
        con.execute("BEGIN IMMEDIATE")
        version=con.execute("PRAGMA user_version").fetchone()[0]
        if version==0 and create:
            if con.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]:
                raise NaviError("Unrecognized runtime database")
            con.execute("CREATE TABLE sessions(scope TEXT NOT NULL,id TEXT NOT NULL,host TEXT NOT NULL,state TEXT NOT NULL,revision INTEGER NOT NULL,updated TEXT NOT NULL,goal_hash TEXT,criteria TEXT,handoff TEXT,PRIMARY KEY(scope,id))")
            con.execute("CREATE TABLE events(scope TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,event TEXT NOT NULL,state TEXT NOT NULL,at TEXT NOT NULL,PRIMARY KEY(scope,id,revision))")
            con.execute("PRAGMA user_version=1")
        elif version!=1:raise NaviError("Unsupported runtime database version")
        yield con,scope
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:con.close()

def _row(con,scope,ident):
    row=con.execute("SELECT * FROM sessions WHERE scope=? AND id=?",(scope,_ident(ident))).fetchone()
    if row is None:raise NaviError("Unknown session for this project")
    return row

def _report(row,include_handoff=False):
    result={"status":"session","id":row["id"],"host":row["host"],"state":row["state"],
            "revision":row["revision"],"updated":row["updated"],"scope":SCOPE}
    if include_handoff:result["handoff"]=json.loads(row["handoff"]) if row["handoff"] else None
    return result

def _event(con,scope,ident,revision,event,state):
    con.execute("INSERT INTO events VALUES(?,?,?,?,?,?)",(scope,ident,revision,event,state,_now()))

def start(root,store,ident,host=None):
    root=_project(root);ident=_ident(ident);host=_host(root,host)
    with _db(root,store,create=True) as (con,scope):
        if con.execute("SELECT 1 FROM sessions WHERE scope=? AND id=?",(scope,ident)).fetchone():
            raise NaviError("Session exists; resume instead")
        con.execute("INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",(scope,ident,host,"awaiting-brief",0,_now(),None,None,None))
        _event(con,scope,ident,0,"SessionStart","awaiting-brief")
        return _report(_row(con,scope,ident))

def status(root,store,ident,include_handoff=False):
    with _db(_project(root),store) as (con,scope):
        return _report(_row(con,scope,ident),include_handoff)

def sessions(root,store):
    with _db(_project(root),store) as (con,scope):
        rows=con.execute("SELECT * FROM sessions WHERE scope=? ORDER BY updated DESC,id LIMIT 100",(scope,)).fetchall()
        return {"status":"listed","sessions":[_report(r) for r in rows],"scope":SCOPE}

def advance(root,store,ident,expected,event,brief=None,handoff=None,reviewed=False):
    if type(expected) is not int or expected<0:raise NaviError("Supply the current session revision")
    with _db(_project(root),store) as (con,scope):
        row=_row(con,scope,ident);old=row["state"]
        if row["revision"]!=expected:raise NaviError("Stale revision; resume session before updating")
        if old=="closed":raise NaviError("Session closed; start a new session")
        goal=row["goal_hash"];criteria=row["criteria"];saved=row["handoff"];gate=None
        if event=="UserPrompt":
            if old not in ("awaiting-brief","clarify","ready","review","paused"):
                raise NaviError("Finish or pause the active execution stage first")
            if brief is None or handoff is not None:raise NaviError("UserPrompt requires brief only")
            gate=nef.intake(brief)
            state="ready" if gate["status"]=="ready" else "clarify"
            goal=_digest(brief["goal"].strip()) if state=="ready" else None
            criteria=json.dumps(sorted(_digest(x.strip()) for x in brief["acceptance"] if x.strip())) if state=="ready" else None
            # Old checkpoint remains useful for resume, not as completion evidence for the new brief.
        elif event=="BeforeExecution":
            if old!="ready":raise NaviError("Execution stage blocked until a ready brief is recorded")
            state="executing"
        elif event=="AfterExecution":
            if old!="executing":raise NaviError("No active execution stage")
            state="review"
        elif event in ("Checkpoint","BeforeCompletion","SessionEnd"):
            if handoff is None or not reviewed:raise NaviError("Supply a reviewed, sanitized handoff explicitly")
            checked=assist.check_handoff(handoff)
            if checked["status"]!="valid":return {"status":"review-required","issues":checked["issues"],"revision":expected}
            if event=="BeforeCompletion":
                if old!="review" or handoff["state"]!="complete" or goal is None:
                    raise NaviError("Completion needs a ready brief, execution review and complete handoff")
                if _digest(handoff["objective"].strip())!=goal:
                    raise NaviError("Handoff objective differs from approved brief")
                actual=sorted(_digest(x["criterion"].strip()) for x in handoff["acceptance"])
                if actual!=json.loads(criteria):raise NaviError("Handoff criteria differ from brief; revise brief explicitly")
                state="closed"
            elif event=="SessionEnd":
                if handoff["state"]=="complete":raise NaviError("Use BeforeCompletion to close a completed task")
                state="paused"
            else:
                if handoff["state"]=="complete":raise NaviError("Checkpoint cannot assert completion")
                state=old
            saved=json.dumps(handoff,ensure_ascii=False,separators=(",",":"))
            if len(saved.encode("utf-8"))>32768:raise NaviError("Handoff exceeds private checkpoint budget")
        else:raise NaviError("Unsupported managed lifecycle event")
        if event!="UserPrompt" and brief is not None:raise NaviError("Unexpected brief")
        if event not in ("Checkpoint","BeforeCompletion","SessionEnd") and handoff is not None:
            raise NaviError("Unexpected handoff")
        revision=expected+1
        con.execute("UPDATE sessions SET state=?,revision=?,updated=?,goal_hash=?,criteria=?,handoff=? WHERE scope=? AND id=?",
                    (state,revision,_now(),goal,criteria,saved,scope,ident))
        _event(con,scope,ident,revision,event,state)
        result=_report(_row(con,scope,ident))
        if gate is not None:
            result["gate"]=gate
            if state=="clarify":result["status"]="clarify"
        return result

def history(root,store,ident):
    with _db(_project(root),store) as (con,scope):
        _row(con,scope,ident)
        rows=con.execute("SELECT revision,event,state,at FROM events WHERE scope=? AND id=? ORDER BY revision DESC LIMIT 100",(scope,ident)).fetchall()
        return {"status":"listed","events":[dict(r) for r in reversed(rows)],"scope":"Metadata only; latest 100 events."}

def context(root,store,ident,budget=8192):
    if type(budget) is not int or not 1024<=budget<=32768:raise NaviError("Context budget must be 1024..32768 bytes")
    result=status(root,store,ident,True)
    result["scope"]="Private reviewed checkpoint; not automatic provider upload. Preserve decisions and blockers; no truncation."
    if len(json.dumps(result,ensure_ascii=False,indent=2).encode())+1>budget:
        raise NaviError("Checkpoint exceeds budget; review a smaller handoff instead of silently truncating")
    return result
