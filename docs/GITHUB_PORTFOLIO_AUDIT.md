# GitHub portfolio maintenance — handoff and roadmap

## Status

Phase 1 candidate, not deployed. The native NAVI inventory module is read-only.
It verifies the authenticated owner, filters forks and archives, paginates
repositories/issues/comments/PRs, records exact PR head/base SHAs and flags
possible unanswered issues. An owner comment is only a signal; its substance
is not evaluated. Every PR remains blocked pending full review. No scheduler,
reply, rebase, merge, approval or remote mutation is implemented.

## Local execution (after code review and tests)

Use a reviewed NAVI installation, Python 3.11+, the official open-source GitHub
CLI and a trusted private output directory outside any Git worktree or sync
folder. Confirm the selected account and access, using read-only permissions
for this phase. Never put credentials in command lines, source or reports.

```sh
gh auth status --hostname github.com
python -m unittest discover -s tests -p test_github_audit.py -v
python -m navi_core.github_audit --owner EXPECTED_LOGIN --output PRIVATE_NEW_REPORT.json --execute
```

The owner and output are placeholders. Use a fresh timestamped output path for
each run. Restrict directory access (Windows ACLs as appropriate); the JSON
contains private repository metadata and must not be published. No credential
is stored by NAVI. An incomplete inventory exits nonzero; do not use it as an
approval. Accessible inventory is not proof of total account access, and
pagination is not a transactional snapshot.

## Roadmap and acceptance

1. **Inventory:** execute offline regression tests and authenticated read-only
   pilot on the owner's trusted host. Compare scope and item counts with GitHub.
   Verify output privacy, timeout handling, pagination and rate-limit behavior.
2. **Evidence and planning:** collect PR diffs, exact required checks/jobs,
   review decisions and threads, branch protection, project-specific instructions,
   security/license and runtime acceptance; fetch fresh base/head before each
   proposal. Integrate with NAVI evidence contracts, Control Center and
   operation-bound governance. Missing, stale, skipped required or failing
   evidence must block. No automatic execution of untrusted PR code.
3. **Agent-assisted triage:** optional single explicitly configured host
   (Codex, Claude, Gemini or Copilot) for semantic issue and PR review. Treat
   repository content as untrusted data, never as privileged instructions.
   Use a structured plan, evidence and idempotency key; do not infer a fix or
   repeat an existing response. Keep no-AI inventory independent of hosts.
4. **Controlled operations:** separate least-privilege writer from read-only
   collector. Verify current permissions, allowed repo, exact action and
   SHA-bound acceptance in a deterministic gate; respect development branches,
   branch protection and required approvals. Use no force push, direct main
   commits, visibility changes, paid service activation or release publishing.
   Test duplicate/replay, concurrent pushes, interrupted and ambiguous
   operations, denied approvals and revocation. Start in dry-run, then an
   explicitly approved pilot. Rebase requests only when needed; merge only
   non-draft fully qualified PRs with expected head SHA and supported method.
   Observe post-merge checks and report failures. Never use CI alone to
   substitute for required local or manual acceptance.
5. **Weekly native execution:** after acceptance, register one owner-controlled
   OS scheduler (Windows Task Scheduler or systemd timer) on a trusted machine
   with reviewed installation, explicit credentials and private report storage.
   Use a single-run lock, bounded retries for read-only work, no automatic
   replay of uncertain writes, and status/exit-code logging. Avoid running
   privileged portfolio audits in public GitHub Actions; no paid service or
   always-on host is assumed. Confirm a live scheduled run before retiring
   any external audit. ChatGPT may read or summarize authorized evidence but
   must not impersonate an executing NAVI instance.
6. **Reporting:** English Markdown handoff and roadmap with per-repository
   observations, issue/PR links, exact merge SHAs, test evidence, blockers,
   unreviewed items and next actions. Preserve private history; Portuguese
   notification summary optional. Maintain no public portfolio audit logs.

## Handoff

The first candidate is additive and isolated from existing CLI entry points.
Use the module entry point until reviewed integration into the main CLI.
Offline test fixtures are provided; live account access, scheduler execution,
write gates and full regression/CI acceptance are outstanding. Do not merge
or deploy merely because this document exists.
