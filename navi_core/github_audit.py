"""Explicit, read-only GitHub portfolio inventory. No agent or write operations."""
import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess


class AuditError(RuntimeError):
    """A missing or incomplete observation must never be treated as approval."""


def gh_get(endpoint):
    executable = shutil.which("gh")
    if not executable:
        raise AuditError("GitHub CLI is unavailable")
    if os.name == "nt" and pathlib.Path(executable).suffix.lower() != ".exe":
        raise AuditError("A native GitHub CLI executable is required")
    env = dict(os.environ, GH_PROMPT_DISABLED="1")
    try:
        result = subprocess.run(
            [executable, "api", "--hostname", "github.com", "--method", "GET", endpoint],
            capture_output=True, text=True, encoding="utf-8", timeout=60, env=env,
            check=True,
        )
        return json.loads(result.stdout)
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        # Do not surface private URLs, raw stderr, credentials or response bodies.
        raise AuditError("GitHub GET failed; verify authentication, access and quota") from exc


def pages(get, endpoint):
    """Bounded complete pagination; never silently accept a truncated inventory."""
    seen = set()
    for page in range(1, 1001):
        separator = "&" if "?" in endpoint else "?"
        rows = get(f"{endpoint}{separator}per_page=100&page={page}")
        if not isinstance(rows, list) or len(rows) > 100:
            raise AuditError("Unexpected pagination response")
        for row in rows:
            if not isinstance(row, dict) or type(row.get("id")) is not int:
                raise AuditError("Missing record identity")
            if row["id"] in seen:
                raise AuditError("Pagination changed during inventory; rerun")
            seen.add(row["id"])
            yield row
        if len(rows) < 100:
            return
    raise AuditError("Pagination bound reached; inventory incomplete")


def inventory(get=gh_get, *, owner):
    """Discover owned non-fork active repositories and open items; no mutations."""
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", owner):
        raise AuditError("Invalid expected owner")
    identity = get("user")
    if not isinstance(identity, dict) or str(identity.get("login", "")).casefold() != owner.casefold():
        raise AuditError("Authenticated identity does not match expected owner")
    repos = list(pages(get, "user/repos?affiliation=owner&visibility=all&sort=full_name&direction=asc"))
    report = {
        "schema_version": 1,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "owner": owner,
        "scope": "Accessible owned non-fork non-archived repositories",
        "mode": "read_only_inventory",
        "repositories": [],
        "excluded": 0,
        "complete": True,
        "writes_performed": 0,
    }
    for repo in repos:
        actual_owner = repo.get("owner", {}).get("login")
        if not isinstance(actual_owner, str):
            raise AuditError("Repository owner missing")
        if actual_owner.casefold() != owner.casefold():
            report["excluded"] += 1
            continue
        if type(repo.get("fork")) is not bool or type(repo.get("archived")) is not bool:
            raise AuditError("Repository scope metadata missing")
        if repo["fork"] or repo["archived"]:
            report["excluded"] += 1
            continue
        name = repo.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in (".", ".."):
            raise AuditError("Invalid repository name")
        full_name = f"{actual_owner}/{name}"
        entry = {"repository": full_name, "issues": [], "pull_requests": [], "status": "observed"}
        report["repositories"].append(entry)
        try:
            for item in pages(get, f"repos/{full_name}/issues?state=open&sort=created&direction=asc"):
                if "pull_request" in item:
                    continue
                number = item.get("number")
                if type(number) is not int or number < 1:
                    raise AuditError("Invalid issue number")
                comments = list(pages(get, f"repos/{full_name}/issues/{number}/comments"))
                replied = any(
                    isinstance(comment.get("user"), dict)
                    and str(comment["user"].get("login", "")).casefold() == owner.casefold()
                    and isinstance(comment.get("body"), str)
                    and bool(comment["body"].strip())
                    for comment in comments
                )
                entry["issues"].append({
                    "number": number, "owner_comment_observed": replied,
                    "disposition": "review_reply_quality" if replied else "review_response_candidate",
                })
            for item in pages(get, f"repos/{full_name}/pulls?state=open&sort=created&direction=asc"):
                number = item.get("number")
                if type(number) is not int or number < 1:
                    raise AuditError("Invalid pull request number")
                pr = get(f"repos/{full_name}/pulls/{number}")
                if not isinstance(pr, dict) or pr.get("number") != number:
                    raise AuditError("Pull request identity mismatch")
                head = pr.get("head", {}).get("sha")
                base = pr.get("base", {}).get("sha")
                if any(not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha) for sha in (head, base)):
                    raise AuditError("Missing exact revision")
                entry["pull_requests"].append({
                    "number": number, "head_sha": head, "base_sha": base,
                    "draft": pr.get("draft"), "mergeable": pr.get("mergeable"),
                    "disposition": "blocked_pending_full_review",
                })
        except AuditError:
            entry["status"] = "incomplete"
            report["complete"] = False
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True, help="Expected authenticated login")
    parser.add_argument("--output", required=True, type=pathlib.Path, help="New JSON file in a private trusted directory")
    parser.add_argument("--execute", action="store_true", help="Explicitly allow read-only GitHub requests")
    args = parser.parse_args(argv)
    if not args.execute:
        parser.error("Explicit --execute required; no requests made")
    try:
        if args.output.exists() or args.output.is_symlink():
            raise AuditError("Output exists; no overwrite")
        report = inventory(owner=args.owner)
        # Caller must use a trusted private directory with appropriate ACLs.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
            handle.write("\n")
        return 0 if report["complete"] else 2
    except (AuditError, OSError) as exc:
        parser.exit(2, f"Audit blocked: {type(exc).__name__}; no remote writes performed\n")


if __name__ == "__main__":
    raise SystemExit(main())
