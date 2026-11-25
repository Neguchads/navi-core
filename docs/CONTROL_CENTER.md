# NAVI Control Center (local preview)

A static offline dashboard and JSON report aggregate explicitly selected
projects without a running server, external network or AI provider.

Create a private portfolio.json outside Git:

    {"schema_version":1,"projects":[{"root":"/absolute/project","profile":"python-tooling","store":null}]}

Set store to the optional canonical private runtime directory. Windows paths
must use valid escaped JSON strings. Then run:

    navi control-center --config portfolio.json
    navi control-center --config portfolio.json --html /private/dashboard.html

The report shows project basename, selected architecture reference, reference
presence/review counts and optional latest-100 session state counts. It does
not expose absolute project paths, handoff text, prompts, source or graph
contents. The HTML is self-contained, escaped, offline and uses a restrictive
content security policy. Output is exclusive-create outside Git. Project
names and counts may still be private: do not publish the dashboard.

This is a read-only local overview, not a live administrative control plane.
It cannot run tasks, merge pull requests, modify governance, authenticate
agents or certify production readiness. No background processes or network
services.
