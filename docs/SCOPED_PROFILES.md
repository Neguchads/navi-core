# Scoped test profiles

Select a reviewed relative directory in the manifest, for example:

```toml
[verification]
require_real_tests = true
timeout_seconds = 900
test_dir = "integrations/portfolio"
```

Python tooling discovers unittest tests in that directory, defaulting to
tests. JavaScript tooling runs explicit top-level .js/.mjs/.cjs files in
the selected directory with node:test and checks a positive TAP pass count.
These are complementary scoped gates, not comprehensive coverage. Existing
project CI remains authoritative. Dependencies must be provisioned separately;
no manifest-supplied commands or arguments. The Node gate requires installed
NAVI and Node; test code is trusted and output is not independently attested.
No shell, traversal, symlink or junction directories accepted.
