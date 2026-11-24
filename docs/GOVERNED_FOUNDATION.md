# Governed foundation — phases 3D through 8 (initial implementation)

## Providers and agentic evaluation

```sh
navi providers
navi providers --model qwen3.5:9b --case BENCH-DAG-001 --execute
```

The second command makes an explicit local HTTP request to 127.0.0.1:11434.
Only built-in public synthetic cases are sent. No shell, tools, private
context or credential access. The adapter requests an output limit and rejects
missing or excessive server-reported usage; this is not a hard billing limit.
Socket timeout is not an overall execution deadline. Loopback does not
guarantee the server itself is offline. Inspect local model/server configuration.
Codex and Claude remain external JSON submission workflows; Nexus stays
disabled. No comparative agent results are claimed.

## Proof, Sentinel, Operations and Universe

```sh
navi proof --case BENCH-DAG-001 --submission answer.json
navi sentinel --root .
navi rollout --root . --core-sha REVIEWED_40_HEX_SHA
navi public-status
```

Proof recomputes synthetic gates and hashes the result; it is not a signed
attestation and does not prove real code execution. Sentinel is a read-only
manifest preflight and tool-presence report, not a secret or vulnerability scan.
Rollout is an explicit non-mutating plan; it does not verify the remote SHA or
authorize a merge. Public status derives only from built-in synthetic cases
and can be collected by a public dashboard without private data. No actual
dashboard publication or production rollout is implied.

## Hard gates still open

Restore-tested real backups, license review, real provider access, full
sandbox/network isolation, independent coding tasks, model cost limits,
adversarial/paired repeated trials, signed provenance, actual security scans,
GitHub administrative governance and pilot approval. Do not adopt Nexus as a
mandatory dependency until these gates and comparative evidence pass.

## Local verification receipt and security CI

```sh
navi proof-run --root . --output-dir /path/outside/repo/new-receipt --execute
navi proof-check /path/outside/repo/new-receipt
```

An explicitly trusted clean Git workspace is required. The installed CLI
is invoked in isolated Python import mode. The receipt binds the gate to the
observed Git revision, exit code, elapsed time and SHA-256 of its local log.
Dirty or changed worktrees fail. The check recomputes log integrity but cannot
authenticate an unsigned receipt. Logs may contain secrets: keep them private.
Timeout is not process-tree isolation; log creation is not bounded by the
later hash limit. This follows the evidence discipline of
[spec-to-proof](https://github.com/Neguchads/spec-to-proof), without claiming
that a generic profile gate covers every acceptance criterion.

CI adds pinned zizmor, pip-audit and Gitleaks (verified release binary hash)
for the public Core. Findings must be reviewed. Version pins are not full hash
locking and known-vulnerability scans are not certification. After all gates
pass on main, a wheel, public synthetic status and hash manifest are uploaded
as Actions artifacts, not a package release or Pages deployment.
