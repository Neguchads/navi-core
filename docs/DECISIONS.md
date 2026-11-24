# Decisions — v0.1.0

- Python 3.11+ with jsonschema as the single direct runtime dependency; transitive versions pinned for CI, hash verification still pending.
- JSON Schema Draft 2020-12 contracts, TOML project manifest, fixed argv arrays; no arbitrary command strings in manifests.
- Verify defaults to plan; explicit execution of trusted code is not a sandbox.
- Init exclusively creates a manifest, rejects preexisting files and symlinks.
- Public export disabled; approval flags declarative, not an enforcement or identity system.
- Reusable workflow uses pinned Core source and read-only GitHub token. No secrets, no pull_request_target, no automatic publication.
- No copied private configuration or third-party skill content.
