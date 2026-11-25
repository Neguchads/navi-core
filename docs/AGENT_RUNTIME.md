# Agent Runtime Integration (phase 4, preview)

The runtime supports one selected host or no AI, without installing or invoking
any agent. It is a local managed workflow and optional advisory context hooks,
not an agent supervisor with universal write interception.

## Discover and choose

    navi hosts
    navi capabilities --host codex

PATH checks do not prove version, authentication, permissions or availability.
Manus and generic hosts use portable context; Copilot command-hook prompt
output is not a reliable context injection mechanism. Do not require multiple
providers. Existing host preferences are respected when no explicit host is supplied.

## Private session lifecycle

Create a canonical, trusted private directory outside Git worktrees, with
owner-only access (on Windows configure ACLs separately). Do not place the
database in a synced/public directory. Example commands (replace STORE):

    navi session start --root . --store STORE --id task-1 --host codex
    navi session event --root . --store STORE --id task-1 --revision 0 --event UserPrompt --brief brief.json
    navi session event --root . --store STORE --id task-1 --revision 1 --event BeforeExecution
    navi session event --root . --store STORE --id task-1 --revision 2 --event AfterExecution
    navi session event --root . --store STORE --id task-1 --revision 3 --event Checkpoint --handoff handoff.json --reviewed
    navi session resume --root . --store STORE --id task-1
    navi session history --root . --store STORE --id task-1

Use the returned current revision at every mutation, not blindly the example
numbers. SQLite transactions prevent stale concurrent updates. A missing or
ambiguous brief blocks the execution stage. A failed intake still records a
clarify state; resolve the user questions, submit a new brief and use its
returned revision. No raw prompts, transcripts, tool output or brief text are
stored: the session records state, events and hashes of the accepted objective
and criteria. Hashes are not encryption. The agent supplies brief classification;
the state machine does not detect semantic ambiguity itself.

BeforeCompletion needs review state and a complete valid handoff whose objective
and acceptance criteria match the last ready brief exactly after trimming.
For simple tasks with no criteria, provide observable criteria in a revised
brief before completion. Evidence is self-reported and must still be verified.
SessionEnd with reviewed in-progress/blocked handoff pauses the session; a new
UserPrompt may reopen it. Checkpoint and resume preserve explicit decisions,
blockers and next steps; oversized context is rejected rather than truncated.
Use --reviewed only for sanitized user-reviewed data. This does not establish
identity or authorize high-risk actions. The agent may still bypass this CLI.

## Candidate native context hooks

    navi connect --root . --store STORE --host codex
    navi connect --root . --store STORE --host codex --apply
    navi connect --root . --store STORE --host codex --check
    navi disconnect --root . --store STORE --host codex
    navi disconnect --root . --store STORE --host codex --apply

The default command is a preview. Apply only creates a missing project-local
file and a private exact-content receipt. Existing settings are never merged
or overwritten; review the fragment and integrate manually if required.
Disconnect removes only the matching generated file with its receipt; modified
files require manual review. Other NAVI-owned host connections must be removed
first. The operation is not transactional across files; interrupted writes
require manual recovery. Run on a trusted local tree without concurrent edits.
Never commit local environment settings or the private receipt.

| Host | Candidate path | Events |
|---|---|---|
| Codex | .codex/hooks.json | SessionStart, UserPromptSubmit |
| Claude Code | .claude/settings.local.json | SessionStart, UserPromptSubmit |
| Gemini CLI | .gemini/settings.json | SessionStart, BeforeAgent |

These are documented protocol candidates. They inject short fixed NEF policy
context; they do not store prompts or automatically bind the host session to
the managed database. No host permission decision or tool blocking is emitted.
The command uses navi on the selected host's PATH; review the resolved executable,
hook settings and host trust prompts before activating. Do not enable in untrusted
repos. Host configuration, version, shell and actual authenticated execution must
be tested separately. Manual portable instructions remain the fallback.

Official references:
- https://learn.chatgpt.com/docs/hooks
- https://code.claude.com/docs/en/hooks
- https://geminicli.com/docs/hooks/reference/
- https://docs.github.com/en/copilot/reference/hooks-reference

## Remaining scope

Automatic installer/update/uninstall, host event-to-session mapping, automatic
context retrieval, semantic prompt classification and write interception are not
implemented. Runtime hooks do not prove host enforcement. No new dependency
beyond the existing Core; SQLite is part of Python's standard library.
