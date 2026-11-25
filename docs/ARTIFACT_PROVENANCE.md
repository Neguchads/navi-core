# Public artifact provenance

The public Core CI builds the wheel and allowlisted synthetic status with a
read-only token. A separate main-only attestation job downloads those bytes,
checks their SHA-256 manifest, requests GitHub Sigstore provenance and verifies
the resulting attestations with gh. No checkout, repository script execution,
private logs or arbitrary user data in the privileged job. OIDC and attestation
write permissions are restricted to this job; PRs cannot execute it.

To independently verify a downloaded wheel:

```sh
gh attestation verify navi_engineering_core-0.3.0rc2-py3-none-any.whl --repo Neguchads/navi-core
```

This authenticates the artifact's association with the GitHub repository and
workflow, not correctness, freedom from vulnerabilities, or approval for
production. Private local proof receipts remain unsigned. No PyPI publishing is enabled. A main-only workflow can publish a verified fixed-version GitHub prerelease without overwriting existing releases.
