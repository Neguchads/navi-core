# NAVI Engineering Core v0.1.0

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
