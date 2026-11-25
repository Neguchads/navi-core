"""Local bounded retrieval over reviewed lessons, source excerpts and Graphify metadata."""
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from . import nef, runtime
from .cli import NaviError, validate
from .agent_bridge import safe_target
from .skill_registry import read_json,write_private,encoded

ID=re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
MAX_DOCS=500
MAX_NODES=2000
MAX_LINKS=5000
SCOPE="Private local advisory data; no provider calls, source execution or policy authority."

def _store(root,store):
    directory,scope=nef._outside(root,store)
    if not directory.is_dir():raise NaviError("Create private store outside Git first")
    return directory,scope

def _id(value):
    if not isinstance(value,str) or not ID.fullmatch(value):raise NaviError("Invalid knowledge id")
    return value

def _digest(data):
    return hashlib.sha256(encoded(data)).hexdigest()

def _size(data):
    return len(json.dumps(data,ensure_ascii=False,indent=2).encode("utf-8"))+1

def _path(directory,ident,kind):
    return safe_target(directory,"knowledge-"+_id(ident)+"."+kind+".json")

def _text(value,limit):
    if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 and c not in "\n\r\t" for c in value):
        raise NaviError("Invalid knowledge text")
    return value

def _source(value):
    # Only relative paths inside the selected project are cited; never read these paths.
    value=_text(value,240)
    if not re.fullmatch(r"[A-Za-z0-9_. -]+(?:/[A-Za-z0-9_. -]+)*",value) or any(p.strip() in ("",".","..") for p in value.split("/")):
        raise NaviError("Source must be a safe relative reference")
    return value

def _document(record):
    validate("knowledge",record)
    _id(record["id"])
    _source(record["source"])
    _text(record["text"],4000)
    _text(record["title"],200)
    return record

def graphify(data):
    """Normalize actual NetworkX node-link format, retaining only allowlisted fields."""
    if type(data) is not dict or type(data.get("nodes")) is not list or type(data.get("links")) is not list:
        raise NaviError("Expected Graphify node-link JSON")
    if len(data["nodes"])>MAX_NODES or len(data["links"])>MAX_LINKS:
        raise NaviError("Graph exceeds bounded preview limits")
    nodes={};links=set()
    for n in data["nodes"]:
        if type(n) is not dict:raise NaviError("Invalid graph node")
        ident=_text(n.get("id"),200)
        if ident in nodes:raise NaviError("Duplicate graph node")
        nodes[ident]={"id":ident,"label":_text(n.get("label"),200),
                      "source":_source(n.get("source_file")),"location":_text(n.get("source_location") or "unknown",80)}
    for e in data["links"]:
        if type(e) is not dict:raise NaviError("Invalid graph edge")
        a=_text(e.get("source"),200);b=_text(e.get("target"),200)
        if a not in nodes or b not in nodes:raise NaviError("Unknown graph endpoint")
        relation=_text(e.get("relation") or "related",100)
        confidence=_text(e.get("confidence") or "UNKNOWN",40)
        links.add((a,b,relation,confidence))
    return {"nodes":[nodes[k] for k in sorted(nodes)],"links":[dict(zip(("source","target","relation","confidence"),e)) for e in sorted(links)]}

def _vector(values,dimension):
    if type(values) is not list or len(values)!=dimension or not 1<=dimension<=4096:
        raise NaviError("Invalid vector dimension")
    if any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e6 for x in values):
        raise NaviError("Invalid vector component")
    norm=math.sqrt(sum(x*x for x in values))
    if norm<=0:raise NaviError("Zero embedding vector")
    return [x/norm for x in values]

def _vectors(data):
    validate("embeddings",data)
    dimension=data["dimension"]
    seen=set()
    for entry in data["entries"]:
        if entry["id"] in seen:raise NaviError("Duplicate embedded evidence")
        seen.add(entry["id"]);_vector(entry["vector"],dimension)
    return data

def ingest(root,store,ident,data,kind,approve_digest=None):
    directory,scope=_store(root,store);_id(ident)
    if kind=="document":
        content=_document(data)
        if content["id"]!=ident:raise NaviError("Document id mismatch")
    elif kind=="graph":content=graphify(data)
    elif kind=="embeddings":content=_vectors(data)
    else:raise NaviError("Unknown knowledge kind")
    digest=_digest(content)
    out={"status":"review-required","id":ident,"kind":kind,"sha256":digest,"scope":SCOPE,
         "review":content}
    if approve_digest is None:return out
    if approve_digest!=digest:raise NaviError("Reviewed digest mismatch")
    record={"schema_version":1,"project_scope":scope,"kind":kind,"sha256":digest,"content":content}
    write_private(_path(directory,ident,kind),record)
    return {"status":"saved","id":ident,"kind":kind,"sha256":digest,"scope":SCOPE}

def _load(directory,scope,ident,kind):
    data=read_json(_path(directory,ident,kind))
    if type(data) is not dict or set(data)!={"schema_version","project_scope","kind","sha256","content"} or data["schema_version"]!=1 or data["project_scope"]!=scope or data["kind"]!=kind:
        raise NaviError("Knowledge record outside selected project or invalid")
    if _digest(data["content"])!=data["sha256"]:raise NaviError("Knowledge record digest mismatch")
    if kind=="document":
        _document(data["content"])
        if data["content"]["id"]!=ident:raise NaviError("Document identity mismatch")
    return data

def _revoked(directory,scope,ident,kind):
    path=_path(directory,ident,kind+"-revoked")
    if not path.exists():return False
    data=read_json(path)
    if data!={"schema_version":1,"project_scope":scope,"id":ident,"kind":kind,"state":"revoked"}:
        raise NaviError("Invalid knowledge revocation")
    return True

def revoke(root,store,ident,kind,apply=False):
    directory,scope=_store(root,store)
    if kind not in ("document","graph","embeddings"):raise NaviError("Invalid knowledge kind")
    _load(directory,scope,ident,kind)
    if _revoked(directory,scope,ident,kind):return {"status":"revoked","id":ident}
    if not apply:return {"status":"planned","id":ident,"kind":kind}
    write_private(_path(directory,ident,kind+"-revoked"),{"schema_version":1,"project_scope":scope,"id":ident,"kind":kind,"state":"revoked"})
    return {"status":"revoked","id":ident,"scope":"Excluded from retrieval, original remains on disk."}

def _records(root,store):
    directory,scope=_store(root,store);docs=[];graphs=[];vectors=[]
    for i,path in enumerate(sorted(directory.iterdir())):
        if i>=1500:raise NaviError("Private directory scan limit exceeded")
        m=re.fullmatch(r"knowledge-([a-z0-9][a-z0-9_-]{0,63})\.(document|graph|embeddings)\.json",path.name)
        if m:
            ident,kind=m.groups()
            meta=read_json(safe_target(directory,path.name))
            if type(meta) is not dict or meta.get("project_scope")!=scope:continue
            record=_load(directory,scope,ident,kind)
            if _revoked(directory,scope,ident,kind):continue
            if kind=="document":
                d=record["content"]
                docs.append({"id":"document:"+ident,"kind":"document","title":d["title"],"text":d["text"],
                             "source":d["source"],"revision":d["revision"],"sha256":record["sha256"]})
            elif kind=="graph":graphs.append((ident,record))
            else:vectors.append((ident,record))
        elif ID.fullmatch(path.stem) and path.suffix==".json" and not path.name.startswith("hook-"):
            data=read_json(safe_target(directory,path.name))
            if type(data) is not dict or data.get("project_scope")!=scope:continue
            _,lesson=nef._record(directory,scope,path.stem)
            if nef._revoked(directory,scope,path.stem):continue
            docs.append({"id":"lesson:"+lesson["id"],"kind":"lesson","title":lesson["kind"],
                         "text":lesson["summary"],"source":lesson["source_reference"],
                         "validation":lesson["validation"],"sha256":_digest(lesson)})
    if len(docs)>MAX_DOCS or len(graphs)>8 or len(vectors)>8:raise NaviError("Knowledge corpus limit exceeded")
    return docs,graphs,vectors

def _terms(text):
    return list(dict.fromkeys(w.casefold() for w in re.findall(r"[^\W_]+",text,re.UNICODE) if len(w)>=2))[:64]

def _query(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise NaviError("Invalid local query file")
    with path.open("rb") as f:raw=f.read(16385)
    if len(raw)>16384:raise NaviError("Query exceeds size limit")
    return raw.decode("utf-8")

def _rank(items,query,limit):
    tokens=_terms(query)
    if not tokens or not items:return [],"empty"
    # FTS5 is an in-memory derived index; revoked entries never survive a new request.
    with sqlite3.connect(":memory:") as con:
        try:con.execute("CREATE VIRTUAL TABLE corpus USING fts5(id UNINDEXED,title,body,tokenize='unicode61 remove_diacritics 2')")
        except sqlite3.OperationalError:
            terms=set(tokens)
            ranked=[(len(terms&set(_terms(item["title"]+" "+item["text"]))),i) for i,item in enumerate(items)]
            return [items[i] for score,i in sorted(ranked,key=lambda x:(-x[0],items[x[1]]["id"])) if score][:limit],"lexical-fallback"
        con.executemany("INSERT INTO corpus VALUES(?,?,?)",[(str(i),item["title"],item["text"]) for i,item in enumerate(items)])
        match=" OR ".join('"'+t+'"' for t in tokens)
        rows=con.execute("SELECT id FROM corpus WHERE corpus MATCH ? ORDER BY bm25(corpus,0,3,1), id LIMIT ?",(match,limit)).fetchall()
        return [items[int(row[0])] for row in rows],"fts5-bm25"

def _graph_context(graphs,query):
    items=[];links=[]
    for ident,record in graphs:
        for n in record["content"]["nodes"]:
            items.append({"id":ident+":"+n["id"],"kind":"graph-node","title":n["label"],"text":n["source"],
                          "source":n["source"],"location":n["location"],"sha256":record["sha256"]})
        for e in record["content"]["links"]:
            links.append({**e,"source":ident+":"+e["source"],"target":ident+":"+e["target"],"graph":ident})
    ranked,engine=_rank(items,query,12)
    seeds={n["id"] for n in ranked};lookup={n["id"]:n for n in items}
    neighbors=[];edges=[];seen=set(seeds)
    for edge in links:
        if len(edges)>=24:break
        if edge["source"] not in seeds and edge["target"] not in seeds:continue
        edges.append(edge)
        for node in (edge["source"],edge["target"]):
            if node not in seen and len(neighbors)<12:
                seen.add(node);neighbors.append(lookup[node])
    selected=ranked+neighbors
    ids={n["id"] for n in selected}
    return selected,[e for e in edges if e["source"] in ids and e["target"] in ids],engine

def _semantic(docs,vectors,query_data):
    validate("embedding-query",query_data)
    if not vectors:raise NaviError("No approved embedding snapshot")
    snapshot=[r for ident,r in vectors if ident==query_data["snapshot"]]
    if len(snapshot)!=1:raise NaviError("Selected embedding snapshot missing or revoked")
    data=_vectors(snapshot[0]["content"])
    if data["model"]!=query_data["model"] or data["dimension"]!=query_data["dimension"]:
        raise NaviError("Embedding model or dimension mismatch")
    q=_vector(query_data["vector"],data["dimension"])
    current={d["id"]:d for d in docs}
    scores=[]
    for entry in data["entries"]:
        d=current.get(entry["id"])
        if d is None or d["sha256"]!=entry["sha256"]:continue
        v=_vector(entry["vector"],data["dimension"])
        score=sum(a*b for a,b in zip(q,v))
        if score>0:scores.append((score,d))
    return [d for _,d in sorted(scores,key=lambda x:(-x[0],x[1]["id"]))[:40]]

def _fusion(a,b):
    # Reciprocal rank fusion avoids assuming BM25 and cosine are comparable.
    scores={};lookup={}
    for ranked in (a,b):
        for i,item in enumerate(ranked,1):
            k=item["id"];lookup[k]=item;scores[k]=scores.get(k,0)+1/(60+i)
    return [lookup[k] for k in sorted(scores,key=lambda k:(-scores[k],k))][:40]

def retrieve(root,store,query_file,budget=8192,session_id=None,embedding_query=None):
    if type(budget) is not int or not 1024<=budget<=32768:raise NaviError("Budget must be 1024..32768 bytes")
    query=_query(query_file);docs,graphs,vectors=_records(root,store)
    ranked,engine=_rank(docs,query,40)
    if embedding_query is not None:ranked=_fusion(ranked,_semantic(docs,vectors,embedding_query))
    nodes,edges,graph_engine=_graph_context(graphs,query)
    out={"status":"selected","scope":SCOPE,"retrieval":{"text":engine,"graph":graph_engine,"semantic_embeddings":embedding_query is not None},
         "checkpoint":None,"evidence":[],"graph":{"nodes":[],"links":[]},"omitted":0}
    if session_id is not None:out["checkpoint"]=runtime.context(root,store,session_id,32768)
    if _size(out)>budget:raise NaviError("Required checkpoint exceeds context budget; review a smaller handoff")
    seen=set()
    # Keep full evidence units and provenance. Never silently truncate an excerpt.
    for doc in ranked:
        key=hashlib.sha256(" ".join(doc["text"].casefold().split()).encode()).hexdigest()
        if key in seen:out["omitted"]+=1;continue
        seen.add(key);out["evidence"].append(doc)
        if _size(out)>budget-64:out["evidence"].pop();out["omitted"]+=1
    for node in nodes:
        out["graph"]["nodes"].append(node)
        if _size(out)>budget-64:out["graph"]["nodes"].pop();out["omitted"]+=1
    ids={n["id"] for n in out["graph"]["nodes"]}
    for edge in edges:
        if edge["source"] not in ids or edge["target"] not in ids:out["omitted"]+=1;continue
        out["graph"]["links"].append(edge)
        if _size(out)>budget-64:out["graph"]["links"].pop();out["omitted"]+=1
    if _size(out)>budget:raise NaviError("Context budget exceeded")
    return out
