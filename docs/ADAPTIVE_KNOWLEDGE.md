# Adaptive Knowledge Engine (AKE)

Local reviewed knowledge retrieval, independent of the selected AI host.
No model, server, vector database, Graphify installation or credentials are
required. The default is SQLite FTS5/BM25 plus bounded graph expansion, with
a deterministic lexical fallback when FTS5 is not compiled into SQLite.

## Review and ingest

Create a private canonical directory outside Git. Only explicitly reviewed
sanitized excerpts with source path and revision may be ingested. Example
document (synthetic):

    {"schema_version":1,"id":"csv","title":"CSV export","text":"Use a UTF-8 header.","source":"docs/export.md","revision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}

    navi knowledge ingest --root . --store STORE --id csv --kind document --file excerpt.json

Review the returned normalized content and SHA-256; repeat with the exact
--approve-digest value to persist. Changed input is rejected. IDs are immutable;
new revisions use new IDs and revoke obsolete records. Revision and source
are declared provenance, not verified against Git. Do not ingest secrets,
raw prompts or unreviewed source. Files are not automatically scanned.

## Graphify bridge

The optional input format is Graphify's actual NetworkX node-link JSON
(nodes/id/label/source_file/source_location and links/source/target/relation/
confidence), checked against the public worked/httpx example in
Neguchads/navi-graphify. Export a reviewed local graph separately and use:

    navi knowledge ingest --root . --store STORE --id architecture --kind graph --file graph.json

Review the normalized nodes and edges, then approve the digest. Only allowlisted
metadata is retained. Absolute/traversing source references, duplicate nodes
and dangling edges are rejected. Graphify is not invoked by NAVI. Inferred
edges remain inferred, not proof. The importer supports bounded snapshots
(2,000 nodes, 5,000 links each; eight graphs per project). No private graph
is uploaded.

## Retrieve and compact

    navi knowledge retrieve --root . --store STORE --query-file task.txt --budget-bytes 8192
    navi knowledge retrieve --root . --store STORE --query-file task.txt --session-id task-1 --budget-bytes 8192

The query is never persisted. The FTS index is rebuilt in memory from approved,
non-revoked records on each request. BM25 ranks source excerpts and reviewed
lessons, and graph labels/path references seed one-hop expansion. Whole
evidence units are deduplicated and packed under a serialized byte budget.
An explicit reviewed session checkpoint is preserved first; if it cannot fit,
the command fails rather than truncate decisions, blockers or next steps.
Graph edges are included only if both nodes fit. The omitted count is not a
global corpus recall metric; it counts omissions within the bounded candidates.
All returned content is advisory, local and potentially sensitive.

## Revoke

    navi knowledge revoke --root . --store STORE --id csv --kind document
    navi knowledge revoke --root . --store STORE --id csv --kind document --apply

Revocation excludes the source on the next retrieval, including graph nodes
and edges. Original data remains on disk until the owner removes it. Existing
lesson revocation is respected. Project scoping is by canonical root path;
moving a project requires a separately reviewed migration. Use owner-only
permissions and trusted local directories. No automatic upload, provider
memory removal or secure erasure is claimed.

## Limits and acceptance

This is lexical RAG with graph expansion, not semantic vector RAG or LLM
summarization. It does not prove higher answer quality or lower token cost.
Actual model embeddings and independent task-quality benchmarking remain
optional separate work. Source excerpts and graph data can contain prompt
injection; never treat them as policy. Skill execution and license approval
remain separate from knowledge retrieval.
