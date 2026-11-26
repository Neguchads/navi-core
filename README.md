# NAVI Engineering Core

**Universal · Local-first · Evidence-driven**

Engineering contracts and reusable GitHub automation for the [NAVI Engineering Universe](https://neguchads.github.io/Neguchads/). Development preview, not production certification.

[English](#setup) · [Português brasileiro](README.pt-BR.md) · [Roadmap](docs/ROADMAP.md) · [Decisions](docs/DECISIONS.md)

## Setup

Requires Python 3.11+. Use an isolated virtual environment.

```sh
python -m venv .venv
# Activate the virtual environment for your shell.
python -m pip install .
python -m unittest discover -s tests -v
navi doctor
```

## CLI

```sh
navi detect --root path/to/project
navi init --root path/to/project --profile documentation --visibility private
navi verify --root path/to/project
navi verify --root path/to/project --execute
```

Init exclusively creates the manifest; it never overwrites. Verify defaults to planning. Explicit execution runs trusted project code, NOT a sandbox. Install reviewed project dependencies first. No automatic publication.

## Profiles

Supported: typescript-backend (Node 24 and npm verify), python-tooling (unittest, including standalone stdlib repositories; rejects empty/all-skipped suites), cpp-native (CMake/CTest), documentation (README local links), static-website (tracked standalone JS syntax). Six other profiles are registered as planned, not executable. Gates are scoped, not production certification.

## Contracts

Project, task, skill, evidence and event schemas live in `navi_core/contracts/`. Run `navi validate project .navi/project.toml`. Approval and privacy flags are declarative; no approval service or public export implemented.

## Provider independence

NAVI Core requires no AI provider, AI SDK, API key or subscription. Choose **one** host: Codex, Claude Code, Gemini CLI or GitHub Copilot. Logical engineering roles can be sequential in that host. No automatic cross-provider fallback. Quota or capability failures pause for review or deterministic tools. Optional multi-host comparison is not an installation requirement. See [provider independence](docs/PROVIDER_INDEPENDENCE.md).

## Agent Bridge (preview)

Generate or check repository-scoped instructions with `navi agents`; list original candidate metadata with `navi skills`. No automatic overwrites or host configuration. See [Agent Bridge](docs/AGENT_BRIDGE.md).

## Private skill registry

`navi skill-scan` inventories local ZIPs; `navi context` selects explicitly reviewed variants under a byte budget. No automatic approval or execution. [Guide](docs/SKILL_REGISTRY.md).

## Agent Bench (offline)

`navi bench --mode reference` runs four synthetic engineering fixtures. External JSON answers may be evaluated without executing code. No real agent or Nexus performance claims. [Guide](docs/AGENT_BENCH.md).

## Governed foundation (experimental)

`navi providers`, `navi proof`, `navi sentinel`, `navi rollout` and `navi public-status` provide synthetic provider evaluation, recomputed proof, manifest preflight, adoption planning and public synthetic status. [Scope and limitations](docs/GOVERNED_FOUNDATION.md).

## GitHub Actions

The reusable workflow checks out the consumer and a reviewed Core SHA, installs dependencies, validates its manifest and executes its gate with a read-only token. Pin both the reusable workflow and core_sha to the same reviewed commit. Do not use with secrets or pull_request_target on untrusted code. See [integration guide](docs/GITHUB.md).

No private configuration, sessions, repositories, audit records or third-party skill content included. Recovery, full security review and license gates precede broad adoption.

MIT License.

### Paired synthetic comparison

`navi compare --model MODEL:TAG` plans a direct versus sequential-review experiment. [Protocol and limitations](docs/PAIRED_BENCH.md).

### Current preview acceptance

See [host acceptance](docs/HOST_ACCEPTANCE.md), [operation reservation](docs/EXECUTION_GATE.md) and [preview release](docs/PREVIEW_RELEASE.md). The ledger and host challenge tools are not production agent authorization or verified authenticated host execution.

For new projects, `navi init --root . --profile documentation --host gemini` saves an optional preferred host. Use `--host none` for a no-AI project. The Core remains independent of any subscription.

## NAVI Engineering Framework (NEF)

Provider-independent engineering references, 19 architecture profiles, adaptable documentation, roadmap and handoff templates, additive scaffolding/migration, structural inspection, structured clarification and explicitly reviewed local lessons. See [NEF guide](docs/NEF.md). Reference profiles do not imply executable project test gates.

## Universal Agent Interface

Use `navi assist --profile game-recomp --format markdown` for portable context with any compatible agent. `navi handoff-check` validates structured session transfer. Optional `navi mcp` exposes public reference tools through stdio. No additional AI provider is required. [Guide](docs/UNIVERSAL_AGENT_INTERFACE.md).

## Agent Runtime Integration

`navi hosts`, `navi capabilities`, private SQLite `navi session` lifecycle, and explicit reversible project-local context hook candidates via `navi connect`/`disconnect`. See [runtime guide](docs/AGENT_RUNTIME.md). Actual host enforcement remains separate.

## Adaptive Knowledge Engine

Reviewed local excerpts and Graphify node-link metadata, project-scoped FTS5/BM25 retrieval, bounded one-hop graph expansion and checkpoint-preserving context packing. No AI dependency. [Guide](docs/ADAPTIVE_KNOWLEDGE.md).

## Engineering Intelligence and Control Center

Read-only static Python import/cycle and reviewed boundary analysis via `navi architecture`; private offline multi-project metadata dashboard via `navi control-center`. [Intelligence](docs/ENGINEERING_INTELLIGENCE.md) · [Control Center](docs/CONTROL_CENTER.md).

[Offline versioned installation and update](docs/INSTALLATION.md): reviewed wheel bundles, isolated environments and non-destructive rollback.

[NAVI canonical repositories](docs/REPOSITORY_NAMES.md).

[Open-source credits, provenance and distribution review](docs/OPEN_SOURCE_COMPLIANCE.md).
