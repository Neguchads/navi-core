"""Independent verifiers; they never import the reference solver or execute submissions."""
import hashlib

def exact_keys(answer, keys):
    return type(answer) is dict and set(answer) == set(keys)

def valid_ids(values):
    return type(values) is list and all(type(v) is str for v in values) and len(set(values)) == len(values)

def partition(answer, yes, no, allowed, denied):
    return (exact_keys(answer, (yes,no)) and valid_ids(answer[yes]) and valid_ids(answer[no])
            and set(answer[yes]) == set(allowed) and set(answer[no]) == set(denied))

def verify(case_id, data, answer):
    if case_id == "BENCH-DAG-001":
        deps = data["dependencies"]
        if not exact_keys(answer,("order",)) or not valid_ids(answer["order"]) or set(answer["order"]) != set(deps):
            return False, False
        positions = {name:i for i,name in enumerate(answer["order"])}
        return all(positions[d]<positions[n] for n,ds in deps.items() for d in ds), True
    if case_id == "BENCH-ARTIFACT-001":
        payloads, manifest = data["payloads"],data["manifest"]
        good = {k for k,v in payloads.items() if manifest.get(k) == hashlib.sha256(v.encode("utf-8")).hexdigest()}
        ok = partition(answer,"accepted","rejected",good,set(payloads)-good)
        return ok, ok
    if case_id == "BENCH-BUDGET-001":
        if not exact_keys(answer,("admitted","remaining")) or not valid_ids(answer["admitted"]) or type(answer["remaining"]) is not int:
            return False,False
        # Independent oracle: fixed expected admission for this versioned fixture.
        # Verify the actual reservation too, preventing a forged remaining field.
        reserves={j["id"]:j["reserve"] for j in data["jobs"]}
        if any(k not in reserves for k in answer["admitted"]):
            return False,False
        used=sum(reserves[k] for k in answer["admitted"])
        safe=used<=data["budget"] and answer["remaining"]==data["budget"]-used
        return safe and answer["admitted"]==["plan","build","review"],safe
    if case_id == "BENCH-GOVERNANCE-001":
        allowed={"r1"}
        denied={r["id"] for r in data["requests"]}-allowed
        ok=partition(answer,"allowed","denied",allowed,denied)
        return ok,ok
    raise ValueError("Unknown benchmark")
