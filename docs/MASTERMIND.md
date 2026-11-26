# NAVI Core — Mastermind foundation

ADR: one product and repository; external specialists remain upstream. Original AAF Core and Nexus Engine are preserved, not mandatory dependencies. Existing Core commands are unchanged. This additive preview does not certify any integration.

## Try the offline planner

```sh
navi mastermind catalog
navi mastermind catalog --domain orchestration
navi mastermind doctor
navi mastermind plan examples/mastermind/local.json
navi mastermind plan examples/mastermind/multi.json
```

The 167-reference catalog is research metadata only. No package, model, skill or service is approved or installed. A proposed capability is not a selected executable. The plan digest identifies canonical content, not authorization. The planner is deliberately read-only; it cannot enforce role permissions, network denial, model licenses or actual quota.

## Microsoft Conductor gate

Primary candidate: https://github.com/microsoft/conductor (MIT upstream; exact revision and dependencies still require review). Not Conductor OSS. Use a separate reviewed environment. Follow the upstream [CLI reference](https://github.com/microsoft/conductor/blob/main/docs/cli-reference.md) and pin a revision before installing. First validate and test a deterministic-only workflow without agents or network; check actual dependency licenses and offline installation, checkpoints and ambiguous effects. Never use --skip-gates for production. No automatic remote plugin fetch or paid provider. Then validate MCP stdio and ACP or native CLI handoff independently. A Codex subscription is not API access. Claude/Codex multi-agent coordination is explicitly planned, not executed.

## Acceptance and migration

1. Catalog review (license at revision, dependencies, artifact digest, model terms, offline behavior).
2. Conductor isolated deterministic smoke, then MCP tool allowlist and exact result.
3. Single-host acceptance using explicit local/free or already authorized quota; no billing or automatic fallback. Multi uses named sequential roles, one writer; actual permission enforcement requires isolated worktrees and reviewed adapters.
4. Compare agent direct, optimized direct, Conductor only and NAVI on the same tasks, independent verifier and cost. Adopt only on demonstrated benefit; keep existing AAF/Nexus until equivalence.
5. Integrate Graphify/Serena, planning skills, security and memory one capability at a time; no forced installation, no private data export.

Zero additional spending; no remote API calls, installation, secret handling, or publication by this command. Local model weights and external services require separate review. Existing project-specific verification remains available through navi verify.

## Local Conductor qualification recipe

The upstream release candidate examined is [v0.1.47](https://github.com/microsoft/conductor/releases/tag/v0.1.47). Its root license is MIT, its Python requirement is 3.12+, and its package metadata includes Microsoft Copilot SDK, Anthropic/OpenAI SDKs and other dependencies. SDK code licensing does not imply that associated runtimes or services are OSS or free. Review the complete resolved dependency tree, package contents, license notices and artifact hashes before approval; do not install this candidate as a mandatory dependency.

With a manually reviewed installation in an isolated environment and network denied, run from the Core checkout:

```sh
conductor validate examples/mastermind/conductor-smoke.yaml
conductor run examples/mastermind/conductor-smoke.yaml --no-interactive
```

Expected output result: `NAVI_CONDUCTOR_OK` and successful exit. This original local script recipe has not yet been executed with the real Conductor runtime. No provider or remote MCP is configured. Check the actual workflow trace, no credentials and no outbound connections; the recipe alone is not proof of isolation. Do not run the command if the runtime or dependency license is unapproved. The no-agent, direct path remains available through existing Core verification.

Multi-agent examples: the `roles.review` value may be a host name or an ordered array of selected host names. Planning and implementation each have exactly one host; review can have several. The sequence is advisory and does not grant write access or invoke the hosts.
