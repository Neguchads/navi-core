"""Offline benchmark harness. No model calls, network, shell or Nexus import."""
import copy
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from .cli import NaviError
from . import bench_cases, bench_verify

def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode("utf-8")

def sha(value):
    return hashlib.sha256(encoded(value)).hexdigest()

def catalog():
    return {"schema_version":1,"suite_version":bench_cases.VERSION,"scope":"synthetic-public",
            "strategies":copy.deepcopy(list(bench_cases.STRATEGIES)),
            "cases":[{"id":k,"fixture_sha256":sha(v),**copy.deepcopy(v)} for k,v in sorted(bench_cases.CASES.items())],
            "limitations":"No real agent runs, code execution, token measurements, or Nexus comparison."}

def check_options(mode,case,submission,budget):
    if type(budget) is not int or not 1<=budget<=1024*1024:
        raise NaviError("Invalid byte budget")
    if case is not None and case not in bench_cases.CASES:
        raise NaviError("Unknown case")
    if mode=="evaluate" and (case is None or submission is None):
        raise NaviError("Evaluate requires --case and --submission")
    if mode!="evaluate" and submission is not None:
        raise NaviError("Submission only supported in evaluate mode")
    if mode=="catalog" and case is not None:
        raise NaviError("Catalog lists all cases")

def solve(case,data):
    # Trusted, non-agent reference implementation. Never loaded from a submission.
    if case=="BENCH-DAG-001":
        remaining=set(data["dependencies"]); order=[]
        while remaining:
            ready=sorted(n for n in remaining if set(data["dependencies"][n])<=set(order))
            if not ready: raise NaviError("Reference DAG has cycle")
            order.extend(ready);remaining.difference_update(ready)
        return {"order":order}
    if case=="BENCH-ARTIFACT-001":
        accepted=[];rejected=[]
        for name,value in sorted(data["payloads"].items()):
            bucket=accepted if hashlib.sha256(value.encode()).hexdigest()==data["manifest"].get(name) else rejected
            bucket.append(name)
        return {"accepted":accepted,"rejected":rejected}
    if case=="BENCH-BUDGET-001":
        remaining=data["budget"];admitted=[]
        for job in data["jobs"]:
            if job["reserve"]<=remaining:
                remaining-=job["reserve"];admitted.append(job["id"])
        return {"admitted":admitted,"remaining":remaining}
    if case=="BENCH-GOVERNANCE-001":
        allowed=[];denied=[]
        for req in data["requests"]:
            ok=req["action"] in data["allowed_actions"] and req["risk"] in data["allowed_risk"] and req["approved"] is True
            (allowed if ok else denied).append(req["id"])
        return {"allowed":allowed,"denied":denied}
    raise NaviError("Unknown case")

def provenance(case):
    return {"case":case,"suite_version":bench_cases.VERSION,"fixture_sha256":sha(bench_cases.CASES[case]),
            "verifier_sha256":hashlib.sha256(Path(bench_verify.__file__).read_bytes()).hexdigest(),
            "harness_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python":platform.python_version(),"platform":sys.platform}

def evaluate(case,answer,budget):
    check_options("evaluate",case,True,budget)
    started=time.perf_counter_ns()
    data=bench_cases.CASES[case]["input"]
    try:
        raw=encoded(answer)
        fits=len(raw)<=budget
        correct,safe=bench_verify.verify(case,data,answer) if fits else (False,False)
        answer_sha=hashlib.sha256(raw).hexdigest()
        size=len(raw)
    except (ValueError,TypeError,RecursionError):
        correct=safe=fits=False;answer_sha=None;size=None
    return {"schema_version":1,"status":"passed" if correct and safe and fits else "failed",
            "mode":"offline-submission","provenance":provenance(case),"gates":{"correctness":correct,"security":safe,"byte_budget":fits},
            "metrics":{"answer_sha256":answer_sha,"answer_bytes":size,"budget_bytes":budget,
                       "verification_ns":time.perf_counter_ns()-started,"generation_ns":None,"input_tokens":None,"output_tokens":None,"cost":None},
            "scope":"Independent checks of synthetic JSON only. No provider execution or attested model usage."}

def run_reference(case=None,budget=4096):
    check_options("reference",case,None,budget)
    runs=[]
    for name in ([case] if case else sorted(bench_cases.CASES)):
        started=time.perf_counter_ns()
        answer=solve(name,copy.deepcopy(bench_cases.CASES[name]["input"]))
        elapsed=time.perf_counter_ns()-started
        report=evaluate(name,answer,budget)
        report["mode"]="offline-reference"
        report["metrics"]["generation_ns"]=elapsed
        runs.append(report)
    return {"schema_version":1,"status":"passed" if all(r["status"]=="passed" for r in runs) else "failed",
            "strategy":"offline-reference","suite_version":bench_cases.VERSION,"runs":runs,
            "summary":{"passed":sum(r["status"]=="passed" for r in runs),"total":len(runs)},
            "scope":"Harness smoke only; timings are local reference Python timings, not agent performance."}
