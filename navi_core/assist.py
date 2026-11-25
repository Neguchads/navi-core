"""Portable public reference packet and structured handoff validation."""
import json
import re
from . import __version__, nef
from .agent_bridge import policy
from .cli import NaviError, RES, validate

def contract(name):
    if name not in ("brief","handoff","lesson"):
        raise NaviError("Unknown assistant contract")
    return json.loads(RES.joinpath("contracts/"+name+".schema.json").read_text(encoding="utf-8"))

def packet(profile):
    p,digest=policy()
    standard=nef.standard(profile)
    if profile is None:raise NaviError("Select one architecture profile")
    return {"schema_version":1,"framework":"NAVI Engineering Framework","core_version":__version__,
            "scope":"Public reference data only; selected host remains responsible for execution.",
            "profile":profile,"reference":standard["profiles"][profile],
            "documentation":[{k:x[k] for k in ("id","preferred","alternatives","priority")} for x in standard["common"]],
            "policy_sha256":digest,"rules":p["rules"],
            "workflow":["recover relevant context","clarify material ambiguity","define acceptance",
                        "plan roadmap and architecture","implement authorized scope","verify actual results",
                        "record handoff","propose reviewed lessons"],
            "contracts":{"brief":contract("brief"),"handoff":contract("handoff"),"lesson":contract("lesson")},
            "commands":["navi standard","navi audit","navi intake","navi scaffold","navi migrate",
                        "navi verify","navi handoff-check","navi learn","navi recall"],
            "capabilities":{"portable_context":True,"host_autoload":False,"host_enforcement":False,
                            "private_context_included":False,"inference":False}}

def render(profile):
    data=packet(profile)
    lines=["# NAVI Engineering Framework — portable agent context","",
           "Use only your selected agent; no other AI provider is required.",
           "Public reference only. These instructions do not grant permissions or prove execution.",
           "",f"Architecture profile: {profile}",data["reference"]["architecture"],"",
           "## Engineering policies"]
    lines.extend("- **"+r["id"]+" "+r["title"]+":** "+r["text"] for r in data["rules"])
    lines+=["","## Lifecycle"]
    lines.extend(str(i)+". "+s for i,s in enumerate(data["workflow"],1))
    lines+=["","## Reference folders (optional)",", ".join(data["reference"]["folders"]),
            "","## Reference documents (alternate paths or consolidated documents are valid)"]
    lines.extend("- "+x["id"]+": "+", ".join(x["alternatives"]) for x in data["documentation"])
    lines+=["","## Local tools when available",", ".join(data["commands"]),
            "If local tools are unavailable, use the included contract and report unverified checks; never claim execution.",
            "","## Structured contracts"]
    for name,schema in data["contracts"].items():
        lines+=["","### "+name,"",chr(96)*3+"json",json.dumps(schema,ensure_ascii=False,indent=2),chr(96)*3]
    return "\n".join(lines)+"\n"

def check_handoff(data):
    validate("handoff",data)
    errors=[]
    if not data["objective"].strip():errors.append("objective")
    if data["state"]!="complete" and not any(x.strip() for x in data["next_steps"]):
        errors.append("next_steps")
    if data["state"]=="blocked" and not any(x.strip() for x in data["blockers"]):
        errors.append("blockers")
    if data["state"]=="complete":
        if data["blockers"]:errors.append("unresolved_blockers")
        if not data["acceptance"]:errors.append("acceptance")
        if any(x["status"]!="passed" or not x["evidence"].strip() for x in data["acceptance"]):
            errors.append("unverified_acceptance")
    if any(x["status"]=="passed" and (not x["evidence"].strip() or x["exit_code"]!=0) for x in data["verification"]):
        errors.append("unverified_test")
    if any(x["status"]=="passed" and not x["evidence"].strip() for x in data["acceptance"]):
        errors.append("missing_acceptance_evidence")
    return {"status":"review-required" if errors else "valid","issues":errors,
            "scope":"Structural self-reported handoff validation; evidence must be independently checked. No permission or production certification."}
