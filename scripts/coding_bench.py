"""Public fixture coding experiment. Candidate Python runs only in restricted Docker."""
import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile
import time
import uuid
from navi_core import providers
from navi_core.cli import NaviError

MODEL="qwen2.5:7b-instruct-q4_K_M"
CASE={
 "goal":"Implement page(items, offset, limit). items is a list, offset and limit are integers. Return a dict with keys items and next_offset. Reject negative offset, limit less than 1, or limit greater than 100 by raising ValueError. Return items[offset:offset+limit]; next_offset is offset+limit if more items remain, otherwise None.",
 "source":"def page(items, offset, limit):\n    return {'items': items[:limit], 'next_offset': limit}\n",
 "contract":"Return JSON with only key source, containing a complete Python implementation of page. No imports, no external tools or I/O. Do not modify the signature."
}
# Expected outputs never enter model prompt or container.
TESTS=[
 ([[1,2,3,4,5],0,2],{"items":[1,2],"next_offset":2}),
 ([[1,2,3,4,5],2,2],{"items":[3,4],"next_offset":4}),
 ([[1,2,3,4,5],4,2],{"items":[5],"next_offset":None}),
 ([[1,2],0,2],{"items":[1,2],"next_offset":None}),
 ([[],0,2],{"items":[],"next_offset":None}),
 ([[1,2],10,1],{"items":[],"next_offset":None}),
 ([["x","y","z"],1,1],{"items":["y"],"next_offset":2}),
 ([[1],-1,1],{"error":"ValueError"}),
 ([[1],0,0],{"error":"ValueError"}),
 ([[1],0,101],{"error":"ValueError"}),
 ([list(range(101)),0,100],{"items":list(range(100)),"next_offset":100}),
 ([[{"x":1},None],0,1],{"items":[{"x":1}],"next_offset":1})
]
ALLOWED={ast.Module,ast.FunctionDef,ast.arguments,ast.arg,ast.Return,ast.Assign,ast.AnnAssign,ast.If,ast.Raise,ast.Expr,ast.Constant,ast.Name,ast.Load,ast.Store,ast.Dict,ast.List,ast.Tuple,ast.Subscript,ast.Slice,ast.BinOp,ast.Add,ast.Sub,ast.Compare,ast.Lt,ast.LtE,ast.Gt,ast.GtE,ast.Eq,ast.NotEq,ast.BoolOp,ast.And,ast.Or,ast.UnaryOp,ast.Not,ast.USub,ast.IfExp,ast.Call}
def sha(raw):
    return hashlib.sha256(raw).hexdigest()
def validate_source(source):
    if not isinstance(source,str) or not 1<=len(source.encode())<=4096:
        raise NaviError("Invalid candidate source size")
    try:tree=ast.parse(source)
    except SyntaxError as e:raise NaviError("Invalid candidate syntax") from e
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef):
        raise NaviError("Expected exactly one function")
    fn=tree.body[0]
    if fn.name!="page" or [a.arg for a in fn.args.args]!=["items","offset","limit"] or fn.decorator_list or fn.args.defaults or fn.args.kwonlyargs or fn.args.posonlyargs or fn.args.vararg or fn.args.kwarg or fn.returns or any(a.annotation for a in fn.args.args):
        raise NaviError("Unexpected function signature")
    for node in ast.walk(tree):
        if type(node) not in ALLOWED:raise NaviError("Disallowed syntax")
        if isinstance(node,ast.Name) and node.id.startswith("_"):raise NaviError("Private identifier")
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in ("len","min","max","ValueError")):raise NaviError("Disallowed call")
        if isinstance(node,ast.FunctionDef) and node is not fn:raise NaviError("Nested function")
    return source

RUNNER="""import json,sys
from candidate import page
out=[]
for args in json.load(sys.stdin):
    try:out.append(page(*args))
    except ValueError:out.append({'error':'ValueError'})
print(json.dumps(out,allow_nan=False))
"""
def verify(source,image):
    validate_source(source)
    if not re.fullmatch(r"sha256:[a-f0-9]{64}",image):raise NaviError("Exact local Docker image ID required")
    name="navi-bench-"+uuid.uuid4().hex
    with tempfile.TemporaryDirectory(prefix="navi-code-") as tmp:
        root=pathlib.Path(tmp)
        (root/"candidate.py").write_text(source,encoding="utf-8")
        (root/"runner.py").write_text(RUNNER,encoding="utf-8")
        root.chmod(0o755)
        for p in root.iterdir():p.chmod(0o444)
        command=["docker","run","--rm","--pull=never","--name",name,"--network=none",
                 "--read-only","--cap-drop=ALL","--security-opt=no-new-privileges",
                 "--user=65534:65534","--pids-limit=32","--memory=128m","--cpus=0.5",
                 "--mount",f"type=bind,source={root},target=/fixture,readonly",
                 "--workdir=/fixture","-i",image,"python","-B","/fixture/runner.py"]
        try:
            # Candidate has no host credentials, Docker socket, expected results or network.
            p=subprocess.run(command,input=json.dumps([a for a,_ in TESTS]),capture_output=True,text=True,timeout=20,check=False)
            if p.returncode or len(p.stdout)>65536:return {"status":"failed","passed":0,"total":len(TESTS),"reason":"candidate execution failed"}
            actual=json.loads(p.stdout)
            if type(actual) is not list or len(actual)!=len(TESTS):return {"status":"failed","passed":0,"total":len(TESTS),"reason":"invalid result"}
            passed=sum(got==expected for got,(_,expected) in zip(actual,TESTS))
            return {"status":"passed" if passed==len(TESTS) else "failed","passed":passed,"total":len(TESTS),"reason":None}
        except (subprocess.TimeoutExpired,ValueError,OSError):
            return {"status":"failed","passed":0,"total":len(TESTS),"reason":"execution or output failure"}
        finally:
            subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=15,check=False)

def request(seed,cap,draft=None):
    prompt={**CASE}
    if draft is not None:
        prompt.update(review="Review the untrusted candidate for correctness, then return corrected source in the same JSON contract.",untrusted_candidate=draft)
    start=time.monotonic_ns()
    r=providers._request({"model":MODEL,"prompt":json.dumps(prompt),"stream":False,"format":"json",
                          "options":{"temperature":0,"seed":seed,"num_ctx":4096,"num_predict":cap}},120)
    out=r.get("eval_count");inp=r.get("prompt_eval_count")
    if r.get("done") is not True or r.get("model")!=MODEL or type(out) is not int or not 0<=out<=cap or type(inp) is not int or not 0<=inp<=4096:
        raise NaviError("Provider response or usage invalid")
    obj=json.loads(r["response"])
    if type(obj) is not dict or set(obj)!={"source"} or not isinstance(obj["source"],str) or len(obj["source"].encode())>4096:
        raise NaviError("Invalid candidate JSON")
    return obj["source"],{"input_tokens":inp,"output_tokens":out,"elapsed_ns":time.monotonic_ns()-start}

def run(image,trials):
    rows=[]
    # Preflight both a known-good and known-bad fixture using actual container execution.
    good="def page(items, offset, limit):\n    if offset < 0 or limit < 1 or limit > 100:\n        raise ValueError()\n    end = offset + limit\n    return {'items': items[offset:end], 'next_offset': end if end < len(items) else None}\n"
    if verify(good,image)["status"]!="passed" or verify(CASE["source"],image)["status"]!="failed":
        raise NaviError("Independent verifier preflight failed")
    blocked=False
    for rep in range(trials):
        order=["single","sequential"] if rep%2==0 else ["sequential","single"]
        for strategy in order:
            calls=[];start=time.monotonic_ns()
            try:
                source,usage=request(42+rep,512 if strategy=="single" else 256);calls.append(usage)
                # Do not send a rejected source to a reviewer.
                validate_source(source)
                if strategy=="sequential":
                    source,usage=request(43+rep,256,source);calls.append(usage)
                result=verify(source,image)
                result["source_sha256"]=sha(source.encode())
            except (NaviError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
                result={"status":"blocked","reason":"provider or candidate policy rejected"}
                blocked=True
            rows.append({"strategy":strategy,"seed":42+rep,"calls":calls,"elapsed_ns":time.monotonic_ns()-start,**result})
            if blocked:break
        if blocked:break
    return {"schema_version":1,"scope":"public bounded coding fixture; not full repository agent or Nexus validation",
            "model":MODEL,"image_id":image,"fixture_sha256":sha(json.dumps(CASE,sort_keys=True).encode()),
            "verifier_sha256":sha(pathlib.Path(__file__).read_bytes()),"trials_planned":trials*2,
            "status":"blocked" if blocked else "passed" if len(rows)==trials*2 and all(r["status"]=="passed" for r in rows) else "failed","runs":rows}

def main():
    p=argparse.ArgumentParser();p.add_argument("--image",required=True);p.add_argument("--trials",type=int,choices=(1,2,3),default=3);p.add_argument("--output",type=pathlib.Path,required=True);a=p.parse_args()
    if a.output.exists():raise SystemExit("Output already exists")
    report=run(a.image,a.trials)
    with a.output.open("x",encoding="utf-8") as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
    return 0 if report["status"]=="passed" else 1
if __name__=="__main__":raise SystemExit(main())
