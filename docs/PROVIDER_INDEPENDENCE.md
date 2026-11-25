# NAVI provider independence

Normative architecture: Core must run with zero AI providers installed. Assisted work selects one host. Codex, Claude Code, Gemini CLI and GitHub Copilot are alternatives, not cumulative dependencies. Ollama's synthetic loopback adapter is opt-in; Nexus is unapproved. No hidden cloud credentials or fallback.

| Host | Repository instruction | Current integration |
|---|---|---|
| Codex | AGENTS.md | Advisory adapter |
| Claude Code | CLAUDE.md | Advisory adapter |
| Gemini CLI | GEMINI.md | Advisory adapter; other Google products require separate acceptance |
| GitHub Copilot | .github/copilot-instructions.md | Advisory adapter; optional Free budget policy |

Gemini CLI context reference: https://geminicli.com/docs/cli/gemini-md/ .

## One-host workflow

Run `navi agents --root .` to list choices if no host is saved. Choose exactly one host (replace gemini as needed). New projects may persist their preference with `navi init --root . --profile documentation --host gemini`. Existing manifests may add `host = "gemini"` under `[agents]` after review. Without a preference, apply/check require an explicit host. `host = "none"` leaves AI optional; explicit command-line selection remains possible. New manifests default to one logical worker; old manifests remain valid.

```sh
navi agents --root . --host gemini --mode plan
navi agents --root . --host gemini --mode apply
navi agents --root . --host gemini --mode check
navi skills --host gemini
navi verify --root .
```

Apply creates missing instructions only. Existing differing instructions must be reviewed and manually merged. Do not overwrite private settings. The explicit `all` operation is only for maintainers who want compatibility files, not required for use. No CLI installation or invocation of any host takes place.

## Logical roles

Planning, implementation, testing, review, security and documentation are logical stages in the same selected host. Independent human review and deterministic checks remain required when risk or project policy demands them. Native subagents are optional capabilities, not external provider dependencies. An unavailable capability or exhausted quota stops or degrades to authorized deterministic tooling; never automatically reroute inference.

## Acceptance

Core verification and GitHub Actions must not require AI credentials. Each host must be tested alone, with no other host installed or authenticated. Synthetic adapter tests cover instruction creation, check, skill metadata and host-lab fixtures. Actual authenticated instruction ingestion, project task execution, tool permissions, quota behavior and OS compatibility require separate evidence for each host. Candidate metadata does not install or approve skills. Passing a synthetic lab is not production certification. A host can be adopted independently after its own acceptance; comparison is optional.

RC3 targets Linux, Windows and macOS through CI, exact wheel checks, separate host-lab preparation and a no-AI project fixture. Check the actual run before claiming a platform passed.

On macOS, temporary paths may include the system `/var` symlink. For new proof/lab output, use an explicitly canonical parent (for example `cd "$TMPDIR" && pwd -P`). The output symlink rejection is intentional and is not relaxed for macOS.
