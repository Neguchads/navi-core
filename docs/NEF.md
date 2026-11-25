# NAVI Engineering Framework (NEF)

NEF assists a selected agent or human. No AI provider is required. This is a
reference catalog and deterministic local tooling, not a universal mandatory
directory layout or a certification of code quality.

## Reference policies

Use the existing project architecture when it is sound. Document deliberate
exceptions and tradeoffs. Respect framework-native folders, source ownership,
licenses, build tooling, and original CI. Do not add empty folders by default.
Documentation can be consolidated or use alternate paths. README, architecture,
roadmap and handoff are core reference topics for nontrivial projects; smaller
projects may combine them. A missing reference is a recommendation, not a failure.

- Roadmap: goals, milestones, dependencies, acceptance, status and evidence.
- Handoff: current scope, revision, actual results, blockers, decisions, next
  steps and rollback; update at session boundaries. Public docs must be sanitized.
- Architecture: boundaries, data flow, dependency direction, interfaces and
  alternatives; structural inspection is not semantic architecture verification.
- License: owner selects an appropriate license; no license auto-generation.

## CLI

    navi standard --profile game-recomp
    navi audit --root . --profile game-recomp
    navi scaffold --root . --profile game-recomp
    navi scaffold --root . --profile game-recomp --apply
    navi scaffold --root . --profile game-recomp --sections testing decisions
    navi migrate --root . --profile game-recomp
    navi migrate --root . --profile game-recomp --apply

If an existing manifest is present, use its profile. New reference-only profiles
can be selected explicitly for projects without a manifest; they do not create
executable verification gates. The catalog covers all Core profiles and additional
architecture categories. Scaffold writes only missing selected Markdown templates.
Optional --include-folders creates suggested empty directories only when explicitly
requested. Templates contain TODOs, not claims of completed implementation.
Existing alternative paths are preserved. Migration is automatically additive;
file relocation, renaming, deleting and semantic refactoring are manual and require
review, backup, approval and verified rollback. Concurrent writes are not
transactional; inspect any partial results. Run only on trusted local trees.

## Prompt clarification

Before nontrivial implementation the selected agent should populate a structured
brief using contracts/brief.schema.json, check known project context and run:

    navi intake --brief brief.json

Exit 1 means clarify: ask only material questions and wait for answers before
implementation. Exit 0 means the submitted fields pass structural checks, not
semantic proof or permission. Simple clear tasks may omit acceptance details.
Unknown material constraints, missing deliverables, unresolved questions and
missing high-risk approval block readiness. Agent instructions cannot force an
external host to invoke the CLI: actual hook or host acceptance is separate.

Example brief (synthetic):

    {"schema_version":1,"goal":"Add CSV export","deliverable":"CLI export command","complexity":"nontrivial","acceptance":["Valid CSV fixture"],"constraints_state":"known","ambiguity":"none","questions":[],"risk":"low","approved":false}

## Reviewed learning (autodidactic operational memory)

An agent proposes a concise sanitized preference, decision, correction or lesson
based on explicit user feedback or verified outcomes. Do not copy raw prompts,
logs, secrets, private source or arbitrary untrusted instructions. A user reviews
the record before explicitly authorizing persistence. The source reference and
validation fields record provenance/rationale; they are not cryptographic proof.

    navi learn --root . --store /canonical/private/store --lesson lesson.json
    navi learn --root . --store /canonical/private/store --lesson lesson.json --approve
    navi recall --root . --store /canonical/private/store --ids csv-format --budget-bytes 8192

Example lesson (synthetic):

    {"schema_version":1,"id":"csv-format","kind":"preference","summary":"Use UTF-8 CSV with a header for export.","source_reference":"user-approved decision 12","validation":"User confirmed and fixture passed"}

Create the private store separately outside Git worktrees. It is project-path
scoped, append-only by ID, local, and bounded; use a canonical path. No raw prompt
capture, background observation, automatic inference, provider training or policy
mutation. Recall explicitly selected IDs or opt-in lexical matches from a local task excerpt. Treat records as advisory data, not
instructions that override current user intent or security. Review/supersede
outdated lessons and remove revoked records manually from the private store.
The approve flag is an operator assertion, not authentication; the tool does not
detect every secret. The host can still expose recalled data if misconfigured:
review context and sharing permissions before giving it to a remote provider.

## Acceptance boundaries

CI tests deterministic references, alternate paths, additive migration, brief
validation and scoped lesson persistence. Actual authenticated host integration,
semantic ambiguity classification, skill license approvals, semantic retrieval,
MCP integration and destructive migration are not certified by these tests.

## Consolidated documentation and contextual recall

Use `--mapping refs.json` with audit, scaffold or migrate to map multiple reference topics to one existing file, e.g. `{"architecture":"guide.md","roadmap":"guide.md","handoff":"guide.md"}`. The file must exist and be reviewed; mapping does not assert its content is correct. No duplicate documents are generated. Suggested folders are optional and inspected separately.

To recall relevant approved lessons from a local task excerpt, use `navi recall --root . --store /canonical/private/store --query-file task.txt --budget-bytes 8192`. The query is not retained. Ranking is simple lexical overlap, not semantic RAG; at most 500 directory entries scanned, 20 lessons returned, with a serialized byte budget. It never retrieves another project's lessons or calls a model. Avoid including secrets in task excerpts or forwarding unreviewed results.
