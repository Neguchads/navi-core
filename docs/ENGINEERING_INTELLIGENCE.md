# Engineering Intelligence (preview)

The initial engine is a bounded static Python import approximation using the
standard library AST. It never imports project modules, executes project code,
rewrites files or guesses an architectural standard. The current project
structure remains authoritative.

    navi architecture --root . --source-root src
    navi architecture --root . --policy architecture-policy.json

Select the actual Python import root (often . or src). An explicit reviewed
policy example:

    {"schema_version":1,"source_root":"src","forbid_cycles":true,"forbidden_imports":[{"from":"app.domain","to":"app.infrastructure"}]}

Reports contain module counts, observed import edges, unresolved import
references, parse/scope issues, strongly connected components, top coupling
counts and explicit boundary violations with line references. A missing
policy endpoint, empty module set or parse failure requires review. A rule
with no observed violation is not full conformance proof. Dynamic imports,
conditional and type-only imports, complex packaging and non-Python code
are outside the precise analysis scope. Unresolved references may be external
dependencies or unresolved local imports. No automated refactoring. Review
actual source and tests before any proposed architectural change.

The engine ignores common generated/dependency directories and linked files,
caps file count/bytes and rejects traversal. Use trusted local trees only.
Other languages can be inspected with reviewed Graphify metadata; native
semantic analyzers for TypeScript, C++, Godot and other languages are not
implemented by this module.
