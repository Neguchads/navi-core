# Agent Bridge (Phase 2A)

Canonical original policy is packaged in navi_core/agents/policy.json. The
policy is advisory: host settings, sandboxes, approvals and hooks are not
implemented by these files. No personal configuration is imported.

```sh
navi agents --root path/to/project
navi agents --root path/to/project --host codex --mode apply
navi agents --root path/to/project --mode check
navi skills --host claude --category verification
```

The repository must have a valid NAVI manifest. The default operation plans
without writing. Apply exclusively creates missing files; any pre-existing
different file blocks all planned writes. Check returns a nonzero exit code
for missing or conflicting files. A policy hash identifies the expected bytes.
Existing instructions must be merged manually after review. No host-level
configuration, MCP setup, model choice, or credential handling is performed.
No automatic overwrites or network calls. On concurrent I/O failure, inspect
the listed created files; writes across several files are not transactional.

Targets: AGENTS.md (Codex), CLAUDE.md (Claude Code),
.github/copilot-instructions.md (Copilot). Actual host loading behavior and
integration require separate acceptance tests. The registry contains six
original candidate metadata records; no third-party skills or handlers are
installed. Phase 2B will add provenance/license review, private registry
import, version conflict handling and context selection after review.
