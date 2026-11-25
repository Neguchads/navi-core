# NAVI Core 0.3.0rc1 — functional preview

This version is a release candidate, not stable production certification.
The main CI builds and attests the wheel, then tests the exact downloaded
artifact in clean virtual environments on Linux, Windows and macOS. A separate
main-only job publishes the fixed preview version to GitHub Releases,
without overwriting an existing release. No private data is included.
The install resolves dependencies from PyPI, so this is not a fully
hash-locked offline installation.

After publication download the wheel and manifest from the release, verify
the wheel with gh attestation verify --repo Neguchads/navi-core, install
in a new Python virtual environment and run navi doctor and navi bench
--mode reference. Nexus remains optional and unapproved for production.
Do not infer stable rollout, real host acceptance or durable recovery from
the preview. A stable version needs the separate acceptance issue gates.

## Changes since 0.2.0rc3

- NEF with 19 advisory reference profiles, adaptable documentation, roadmap/handoff, additive migration and structure inspection.
- Optional architecture_profile independent of the executable verification profile.
- Structured prompt clarification and reviewed local learning, including opt-in lexical retrieval.
- Exact-wheel NEF smoke added; actual host adherence and semantic checks remain separate.

## Earlier changes since rc2

- Provider-independent instructions for Codex, Claude Code, Gemini CLI and Copilot.
- Optional single preferred host in new or existing project manifests; one logical worker by default. No AI required by the Core.
- macOS CI and separate installed-wheel host fixtures added; verify actual CI before asserting publication or compatibility.

## Earlier preview changes

- Local operation-bound, single-use approvals and atomic reservation ledger.
- Manual single-host acceptance lab for Codex, Claude, Gemini or Copilot (optional comparison).
- Explicit Ollama fixture calls reserve before transport and settle reported usage. Live run 45546679286 passed: reservation 4352, settlement 142 tokens, 4210 unused. Not a hard account billing cap.
- All acceptance criteria for production remain tracked separately in issue #15. No general stable production claim. The optional Nexus code remains private.
