# NAVI ecosystem integration and acceptance

## Integration Manager (local preview)

Clone the five canonical repositories into one trusted directory, using their
repository names. Graphify uses v8; other default branches are main.
Choose a separately reviewed full Core SHA (not an arbitrary floating branch).

    navi integrations --workspace WORKSPACE --core-sha REVIEWED_SHA
    navi control-center --config PRIVATE_CONFIG --workspace WORKSPACE --core-sha REVIEWED_SHA --html PRIVATE_DASHBOARD

The audit reads committed Git objects, not uncommitted files. It validates
both canonical Core pins and the three Universe source pins. Divergence
requires review; it is not automatically a defect because old pins may be
intentional. Unavailable checkouts are not counted as success. No Git write,
network access, provider invocation or automatic update occurs. Exit 1 means
review is required. Local checkout identity, signatures and remote CI are
not certified. The workflow text recognizer deliberately accepts only the
existing canonical syntax, not arbitrary YAML. No Nexus dependency.

## Environment inventory

    navi sbom > installed.cdx.json

Run from a clean reviewed environment for a useful CycloneDX 1.6 inventory.
This lists installed Python distributions, not the dependency closure of a
wheel or OS components. License expressions are declared metadata, not
license clearance. Keep the inventory local until reviewed. Use the existing
pip-audit, Gitleaks, workflow scan and artifact provenance gates separately.

## Acceptance matrix

| Phase | Existing implementation / verification | Remaining external gate |
| --- | --- | --- |
| Integration | Local committed pin audit, reusable CI, pinned Universe publication | Review cross-repo upgrades and live CI |
| Control Center | Local project/session summary plus integration audit | Authenticated GitHub task/release/security metadata |
| Agent Runtime | Single-host managed sessions, reversible candidate hooks, host lab | Actual selected authenticated host and native event acceptance |
| Knowledge | SQLite/BM25, approved Graphify imports, optional vector snapshots | Measured retrieval quality with real embeddings |
| Security & Recovery | CI audit, history scan, provenance, recovery rehearsal, environment inventory | License review, durable encrypted restore and production threat review |
| Distribution | Reviewed offline wheels, isolated venv, update/uninstall, multi-OS smoke | Stable release approval and independently reviewed wheel bundles |
| Acceptance | Real Git fixture, existing unit tests and isolated coding benchmark | Selected-host real engineering outcomes, measured baselines and explicit production decision |

No production certification is inferred from tests or from the inventory.
Passing a single selected host suffices for that host's adoption; other
providers are optional and never prerequisites. Nexus remains separate.
