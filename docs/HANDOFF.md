# NAVI Core handoff

## Current scope
NEF reference tooling, provider-independent engineering assistance. The RC3 release predates NEF; consult the current reviewed revision and CI before adoption.

## Completed evidence before NEF
- PR #24: independent agent adapters and neutral quota handling.
- PR #25: optional host preference and cross-platform tests. RC3 published after main CI.
- PR #26: NEF implementation submitted; check its current CI and merge state before claiming validation.

## Open work
- Verify NEF from the installed artifact; real agent hook/contract ingestion remains separate.
- Review project documentation mappings before adoption; no forced path migration.
- Private reviewed learning: evaluate actual host retrieval and user-approved records.
- Optional Nexus and real host acceptance are not prerequisites for deterministic NEF.

## Next steps
1. Check current commit, dirty tree and CI.
2. Run unit tests, standard, audit and scaffold plan.
3. Review recommendations before apply; preserve existing layout and original CI.
4. Update roadmap and handoff with actual evidence and unresolved questions.

## Rollback
Revert only the reviewed NEF commit if needed. Do not erase user documentation, private records, or existing repository changes.

## UAI follow-up
NEF #26 passed all five pre-merge gates and was integrated. UAI adds portable public context and optional SDK-backed MCP. Review current CI, actual published artifact and host capability before adoption.

RC1 main artifact installation (run 45601823906) found a CLI KeyError after zero-AI verification, before NEF smoke. Publication was correctly blocked. PR #27 fixes status-free reference output handling, adds CLI-level regression tests and pre-merge installed CLI smoke. RC2 replaces the unpublished RC1 only after actual evidence; do not overwrite release tags.

Runtime phase 4: inspect `docs/AGENT_RUNTIME.md`, current PR/CI and exact release artifact. Native context hook candidates must be tested in the selected host; no actual host session is claimed by synthetic protocol tests.

AKE follow-up: read docs/ADAPTIVE_KNOWLEDGE.md and check exact CI. Do not call lexical graph expansion semantic vector RAG; do not expose private queries, graphs or checkpoints.

Intelligence and Control Center follow-up: review docs/ENGINEERING_INTELLIGENCE.md and docs/CONTROL_CENTER.md, confirm exact CI, do not imply semantic multi-language or administrative enforcement.
