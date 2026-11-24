"""Read-only foundation for proof, sentinel, rollout and public status."""
import hashlib
import re
import shutil
from pathlib import Path
from . import agent_bench, __version__
from .cli import NaviError, load_manifest, REGISTRY

def proof(case,answer,budget):
    report=agent_bench.evaluate(case,answer,budget)
    return {"schema_version":1,"status":report["status"],"kind":"recomputed-synthetic-evidence",
            "evidence":report,"evidence_sha256":agent_bench.sha(report),
            "limitations":"Hash establishes content integrity, not authorship, execution provenance or signature. No production evidence."}

def preflight(root):
    root=Path(root).resolve(strict=True)
    data=load_manifest(root)
    profile=data["project"]["profile"]
    checks={"manifest":"passed","public_export_disabled":"passed" if data["knowledge"]["public_export"] is False else "failed",
            "real_tests_required":"passed" if data["verification"]["require_real_tests"] is True else "failed",
            "profile_supported":"passed" if REGISTRY[profile]["status"]=="supported" else "failed"}
    tools={name:bool(shutil.which(name)) for name in ("git","gitleaks","osv-scanner","trivy")}
    return {"schema_version":1,"status":"failed" if "failed" in checks.values() else "preflight-only",
            "checks":checks,"tools_present":tools,
            "unverified":["secret scan","dependency scan","branch protection","workflow permissions","backup restore","license review","sandbox"],
            "scope":"Manifest preflight and tool presence only; not security certification."}

def rollout(root,core_sha):
    if not re.fullmatch(r"[a-f0-9]{40}",core_sha): raise NaviError("A full reviewed Core SHA is required")
    root=Path(root).resolve(strict=True)
    manifest=load_manifest(root)
    pre=preflight(root)
    return {"schema_version":1,"status":"blocked" if pre["status"]=="failed" else "planned",
            "core_sha":core_sha,"profile":manifest["project"]["profile"],"visibility":manifest["project"]["visibility"],
            "proposed_workflow":{"uses":"Neguchads/navi-core/.github/workflows/reusable-ci.yml@"+core_sha,"with":{"core_sha":core_sha},"permissions":{"contents":"read"}},
            "required_before_merge":["review exact SHA and workflow","restore-tested backup","original and NAVI CI success","license and secret review","human approval"],
            "rollback":"Revert reviewed integration commit; preserve original CI.",
            "scope":"No repository writes, no credential access, no SHA existence or approval attestation."}

def public_status():
    # No user-provided report or project data can enter this export.
    reference=agent_bench.run_reference()
    return {"schema_version":1,"scope":"public-core-synthetic-only","core_version":__version__,
            "benchmark_suite":reference["suite_version"],"synthetic_reference":{"passed":reference["summary"]["passed"],"total":reference["summary"]["total"]},
            "real_agent_comparison":None,"nexus_adoption":"not-homologated",
            "security_certification":None,"production_rollout":None}
