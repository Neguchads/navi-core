# Local skill quarantine and context planning — Phase 2B

The scanner reads direct SKILL.md entries in ZIP archives without extraction,
execution, network access, or publication. It groups by directory-based
case-folded ID and exact SHA-256; it does not infer versions from filenames
or license from a nearby file. Nested archives are not scanned.

```sh
navi skill-scan codex.zip claude-config.zip Skills.zip Nexus.zip --output inventory.json
navi context --inventory inventory.json --approvals approvals.json --host codex --query "architecture plan" --budget-bytes 24000
```

An empty review file is {"schema_version":1,"scope":"private-local","approvals":[]}.
Each manually reviewed approval has id, sha256, decision ("approved"), license,
reviewed_by, review_reference, risk (low/medium/high/critical), hosts (array),
and tags (array). Review license and source, choose ONE exact variant per ID.
A review assertion is not independent verification. No implicit approval.
The default risk ceiling is low.

Optional --output context.json --archives <ZIP paths> creates a private,
exclusive local packet with exact verified skill text, rechecking archive
and content hashes. The budget is UTF-8 bytes, not tokens; serialized packet
size is checked independently. The planning operation returns metadata only.
Keyword overlap is deterministic, not semantic search. No skill is executed.

Keep inventory, approvals and context outside any Git working tree; they can
contain private paths, identifiers and instructions. POSIX output is created
with mode 0600; Windows uses the directory ACL. Use a restricted directory.
The scanner is a metadata/integrity tool, not a secrets or malware scanner.
Review contents for prompt injection, credentials and licenses before use.
No private archives or inventory are included in this public repository.

Future: independent Codex/Claude/Gemini/Copilot acceptance tests, host-specific tool
availability checks, tokenization benchmarks, graph retrieval, and governed
execution. Do not enable automatic ingestion or publish private context.
