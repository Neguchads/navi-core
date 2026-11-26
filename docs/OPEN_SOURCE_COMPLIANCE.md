# Open-source provenance and distribution policy

This is an initial technical attribution audit, not a legal certification or a complete SBOM. Maintainers must preserve upstream rights and review the exact distributed revision.

## Original authorship and license scope

Copyright (c) 2026 Gustavo (Neguchads) — original NAVI Core / NEF contributions, under the existing MIT License. AAF Core and Nexus Engine are original projects of the same author, as confirmed by the owner. Nexus Engine is separately MIT-licensed; AAF Core's private source and separate license are not covered by NAVI Core's license.

For original contributions, record the actual rights holder, year and applicable SPDX license. In forks preserve upstream notices and add a separate notice limited to original contributions. MIT forks retain MIT; NAVI Graphify retains Apache-2.0 and historical MIT notices. Do not automatically relicense third-party or contributor material, or assume every AI-assisted output has exclusive copyright protection.

## Provenance and references

| Source | Relationship | Terms / status |
| --- | --- | --- |
| [NAVI Core / NEF](https://github.com/Neguchads/navi-core) | Repository-maintained engineering contracts and reference implementation | MIT, see LICENSE; does not relicense imported material |
| [Spec-to-Proof](https://github.com/Neguchads/spec-to-proof) | Related acceptance/evidence methodology | MIT for its own material; see its origin attribution |
| [Abyssal Garden](https://github.com/Noniv/abyssal-garden) — Maksymilian Dendura | Reference behind Spec-to-Proof's documented origin; not an assertion that its code is embedded in Core | MIT |
| [Graphify](https://github.com/Graphify-Labs/graphify) — Safi Shamsi and contributors | External graph tooling and interoperability, through NAVI Graphify | Apache-2.0; historical MIT portions |
| Backend template | Engineering reference; README describes original code; no root LICENSE was located during initial review | Rights unresolved for reuse; do not distribute copied material until authorized |
| [jsonschema](https://github.com/python-jsonschema/jsonschema) | Declared runtime dependency | Verify installed version's metadata and notices |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Optional dependency | Verify installed version's metadata and notices |

Codex, Claude Code, Gemini CLI and GitHub Copilot are independent optional host choices, not NAVI products or required joint dependencies. Naming a host does not license its software, assets, service or trademarks.

## Required review before public release

1. Record source URL, exact commit/version, paths, copyright notices, SPDX expression, relationship (copied, adapted, linked, runtime dependency, inspiration only), and distribution scope.
2. Preserve original license/copyright text and applicable NOTICE files. Mark changes to Apache-2.0 files prominently. Do not replace upstream authorship with NAVI branding.
3. Produce and review a version-specific dependency and asset inventory (including transitive packages, vendored code, fonts, icons, generated code and build inputs). An SBOM is not a substitute for license notices.
4. Verify the actual wheel, archive, standalone HTML or deployed bundle includes applicable notices; test extraction and offline readability. Unknown or incompatible rights block distribution until resolved.
5. Quarantine imported skills/configurations and private archives. Review exact content, permission and license before import or redistribution. Never publish confidential provenance, paths or private source.
6. Distinguish references from copied content. Do not assume public GitHub access grants a redistribution license.
7. Preserve audit evidence at the reviewed commit. Automated checks cannot prove copyright ownership or authorize relicensing.

Suggested inventory: SPDX or CycloneDX plus a human-readable attribution file; tools such as ScanCode Toolkit, REUSE and Syft may assist after review. This policy itself does not implement an automated release gate.

See [Apache-2.0 section 4](https://www.apache.org/licenses/LICENSE-2.0.html), [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) and [SPDX license list](https://spdx.org/licenses/).
