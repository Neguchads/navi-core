# NAVI Core 0.2.0rc1 — functional preview

This version is a release candidate, not stable production certification.
The main CI builds and attests the wheel, then tests the exact downloaded
artifact in clean virtual environments on Linux and Windows. A separate
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
