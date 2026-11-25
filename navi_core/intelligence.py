"""Bounded read-only Python dependency analysis. No source imports or execution."""
import ast
from collections import defaultdict
import os
from pathlib import Path
import re
from .cli import NaviError,validate
from .agent_bridge import safe_target
from . import nef

MAX_FILES=1500
MAX_BYTES=512*1024
MAX_SCAN_BYTES=32*1024*1024
IGNORE={".git",".navi",".venv","venv","node_modules","__pycache__","build","dist",".godot","vendor"}
MODULE=re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")

def _source_root(root,rel):
    if rel==".":return root
    if not isinstance(rel,str) or not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*",rel) or any(x in (".","..") for x in rel.split("/")):
        raise NaviError("Source root must be a safe relative path")
    p=safe_target(root,rel)
    if not p.is_dir():raise NaviError("Source root must be an existing directory")
    return p

def _files(root,base):
    result=[];visited=0
    for directory,dirs,files in os.walk(base,followlinks=False):
        visited+=len(dirs)+len(files)
        if visited>20000:raise NaviError("Directory scan limit exceeded")
        d=Path(directory)
        dirs[:]=sorted(x for x in dirs if x not in IGNORE and not x.startswith(".") and not (d/x).is_symlink() and not (hasattr(d/x,"is_junction") and (d/x).is_junction()))
        for name in sorted(files):
            if not name.endswith(".py") or name.startswith("."):continue
            p=d/name
            if p.is_symlink():continue
            p=safe_target(root,p.relative_to(root).as_posix())
            if not p.is_file():continue
            result.append(p)
            if len(result)>MAX_FILES:raise NaviError("Python file count exceeds analysis limit")
    return result

def _name(base,path):
    parts=list(path.relative_to(base).with_suffix("").parts)
    if parts[-1]=="__init__":parts.pop()
    ident=".".join(parts)
    return ident if MODULE.fullmatch(ident) else None

def _target(name,modules):
    # Resolve only known module names; never import a module or execute a loader.
    while name:
        if name in modules:return name
        name=name.rpartition(".")[0]
    return None

def _edges(module,path,tree,modules):
    package=module if path.name=="__init__.py" else module.rpartition(".")[0]
    found=set();unresolved=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            names=[a.name for a in node.names]
        elif isinstance(node,ast.ImportFrom):
            prefix=node.module or ""
            if node.level:
                parts=package.split(".") if package else []
                up=node.level-1
                if not parts or up>=len(parts):
                    unresolved+=1;continue
                prefix=".".join(parts[:len(parts)-up]+([prefix] if prefix else []))
            names=[prefix+"."+a.name if prefix else a.name for a in node.names if a.name!="*"]
            if not names and prefix:names=[prefix]
        else:continue
        for name in names:
            target=_target(name,modules)
            if target is None:unresolved+=1
            elif target!=module:found.add((module,target,node.lineno))
    return sorted(found),unresolved

def _cycles(nodes,edges):
    # Iterative Kosaraju SCC avoids recursion depth on long dependency chains.
    forward={n:set() for n in nodes};back={n:set() for n in nodes}
    for a,b,_ in edges:forward[a].add(b);back[b].add(a)
    seen=set();order=[]
    for n in sorted(nodes):
        if n in seen:continue
        stack=[(n,False)]
        while stack:
            cur,done=stack.pop()
            if done:order.append(cur);continue
            if cur in seen:continue
            seen.add(cur);stack.append((cur,True))
            stack.extend((x,False) for x in sorted(forward[cur],reverse=True) if x not in seen)
    seen.clear();groups=[]
    for n in reversed(order):
        if n in seen:continue
        group=[];stack=[n];seen.add(n)
        while stack:
            cur=stack.pop();group.append(cur)
            for x in sorted(back[cur]):
                if x not in seen:seen.add(x);stack.append(x)
        if len(group)>1:groups.append(sorted(group))
    return sorted(groups)

def _matches(name,prefix):
    return name==prefix or name.startswith(prefix+".")

def analyze(root,policy=None,source_root="."):
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise NaviError("Invalid project root")
    if policy is not None:
        validate("architecture-policy",policy)
        source_root=policy["source_root"]
    base=_source_root(root,source_root)
    modules={};errors=[];total=0
    for path in _files(root,base):
        name=_name(base,path)
        if name is None:
            errors.append({"path":path.relative_to(root).as_posix(),"reason":"unresolved-module-name"});continue
        if name in modules:raise NaviError("Ambiguous module name; select narrower source root")
        with path.open("rb") as f:raw=f.read(MAX_BYTES+1)
        total+=len(raw)
        if total>MAX_SCAN_BYTES:raise NaviError("Source byte limit exceeded")
        if len(raw)>MAX_BYTES:
            errors.append({"path":path.relative_to(root).as_posix(),"reason":"file-too-large"});continue
        try:tree=ast.parse(raw,filename="<source>")
        except (SyntaxError,ValueError,UnicodeError,RecursionError):
            errors.append({"path":path.relative_to(root).as_posix(),"reason":"parse-failed"});continue
        modules[name]=(path,tree)
    edges=[];unresolved=0
    for name,(path,tree) in sorted(modules.items()):
        found,missed=_edges(name,path,tree,modules);edges.extend(found);unresolved+=missed
    cycles=_cycles(modules,edges)
    violations=[];rule_results=[]
    if policy is not None:
        for rule in policy["forbidden_imports"]:
            a,b=rule["from"],rule["to"]
            a_count=sum(_matches(n,a) for n in modules);b_count=sum(_matches(n,b) for n in modules)
            matches=[{"from":x,"to":y,"line":line,"source":modules[x][0].relative_to(root).as_posix()} for x,y,line in edges if _matches(x,a) and _matches(y,b)]
            violations.extend(matches)
            rule_results.append({"from":a,"to":b,"status":"violation" if matches else ("unverified" if not a_count or not b_count else "no-observed-violation"),"source_modules":a_count,"target_modules":b_count})
    incoming=defaultdict(set);outgoing=defaultdict(set)
    for a,b,_ in edges:outgoing[a].add(b);incoming[b].add(a)
    coupling=[{"module":n,"incoming":len(incoming[n]),"outgoing":len(outgoing[n])} for n in modules]
    coupling.sort(key=lambda x:(-x["outgoing"]-x["incoming"],x["module"]))
    result={"status":"inspected","language":"python","source_root":source_root,"modules":len(modules),"edges":len(edges),
            "unresolved_import_references":unresolved,"parse_or_scope_issues":errors,"cycles":cycles,
            "coupling":coupling[:30],"violations":violations,"rule_results":rule_results,
            "recommendations":[{"kind":"review-cycle","modules":g} for g in cycles],
            "scope":"Static local Python import approximation only. Dynamic imports, conditional execution, namespace packaging, type-only imports and non-Python code are not fully resolved. No edits or execution."}
    if not modules or errors or any(r["status"]=="unverified" for r in rule_results):result["status"]="review-required"
    if violations or (policy is not None and policy["forbid_cycles"] and cycles):result["status"]="violations"
    return result
