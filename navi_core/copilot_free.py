"""Advisory, fail-closed Copilot Free routing; no inference, billing API or credentials."""
import datetime
from .cli import NaviError

SMALL=("docs","unit-test","small-fix","explain")
KINDS=(*SMALL,"format","lint","complex","architecture","security","release")
RISKS=("low","medium","high","critical")
VISIBILITY=("public","private","internal","unknown")
INSTRUCTIONS = "# NAVI — Copilot Free micro-tasks\n\nUse Copilot only for small, low-risk, public-code tasks: concise explanations,\ndocumentation, small isolated fixes and simple unit tests. Prefer deterministic\ntools for formatting, linting and known checks. Keep the task within two files\nand 80 changed lines; if it expands, stop and ask the user to route elsewhere.\nRead only relevant excerpts. Return a short proposed patch and one verification\ncommand. No unrelated refactoring, new dependencies, parallel agents, retries,\nwhole-repo analysis, secrets, private context, authentication changes, releases,\nremote writes, merges or deployments. Never claim tests passed without evidence.\nUse automatic model selection. Confirm the current monthly credit allowance\nand disable paid additional usage in GitHub billing before requesting inference.\nNAVI reserves 30% of the included allowance; use the manual copilot-plan gate\nbefore starting a task. This instruction file is advisory, not a spending cap.\n"

def plan(kind,risk,visibility,files,lines,used=None,estimate=None,checked_on=None,paid_usage_blocked=False):
    if kind not in KINDS or risk not in RISKS or visibility not in VISIBILITY:
        raise NaviError("Invalid Copilot task classification")
    if type(files) is not int or type(lines) is not int or not 0<=files<=100000 or not 0<=lines<=1000000:
        raise NaviError("Invalid task size")
    for value in (used,estimate):
        if value is not None and (type(value) is not int or not 0<=value<=100):
            raise NaviError("Use integer percentages of included monthly credits")
    if type(paid_usage_blocked) is not bool:
        raise NaviError("Invalid billing confirmation")
    out={"status":"planned","provider":None,"mode":"manual-routing-only",
         "kind":kind,"risk":risk,"visibility":visibility,"max_files":2,"max_changed_lines":80,
         "monthly_target_percent":70,"reserve_percent":30,"max_estimated_task_percent":5,
         "additional_paid_usage_allowed":False,
         "scope":"User-reported rounded-up credits and task estimate; advisory only. No actual quota lookup, reservation, provider call or billing change."}
    def choose(provider,reason):
        return {**out,"provider":provider,"reason":reason}
    if risk!="low" or kind in ("security","release"):
        return choose("human-review","Risk or operation requires separate approval")
    if kind in ("format","lint"):
        return choose("deterministic","No LLM required")
    if visibility!="public":
        return choose("local-review","Private or unknown context is not eligible")
    if kind=="architecture":
        return choose("claude-review","Architecture requires separate review")
    if kind not in SMALL or files>2 or lines>80:
        return choose("codex-review","Task exceeds micro-task scope")
    today=datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if not paid_usage_blocked or used is None or estimate is None or checked_on!=today:
        return choose("local-review","Current UTC-day usage, estimate and zero-overage confirmation required")
    if not 1<=estimate<=5 or used+estimate>70:
        return choose("local-review","Conservative included-credit target or task allowance exceeded")
    return {**choose("copilot-free","Eligible for a manually approved small task"),
            "reported_used_percent":used,"estimated_task_percent":estimate,
            "checked_on_utc":checked_on,"projected_percent":used+estimate,
            "recommended_mode":"Auto selection; one short request; check actual usage after completion"}
