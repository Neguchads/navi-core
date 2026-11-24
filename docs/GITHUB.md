# GitHub integration

The reusable workflow uses workflow_call and requires the consumer to provide a valid .navi/project.toml. For an independently reviewed Core commit, use the same full 40-character SHA in both the uses ref and core_sha input.

```yaml
name: NAVI pilot
on:
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  verify:
    uses: Neguchads/navi-core/.github/workflows/reusable-ci.yml@REVIEWED_SHA
    with:
      core_sha: REVIEWED_SHA
```

REVIEWED_SHA is a placeholder, not an executable ref. No secrets are required. Only a supported profile can execute. Python/native projects must provision their own reviewed dependencies when needed. The gate runs trusted project code, does not certify production readiness, and should not be required until pilot CI passes. Use a fresh branch; rollback by reverting the integration commit. Do not configure automatic merge or cross-repository write access.
