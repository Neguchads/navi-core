# NAVI AutoVerify — public hash lookup preview

This is an optional external integration, separate from local-only Core commands.
It never uploads files, rescans them, executes them, or publishes releases. It
does not replace antivirus, artifact provenance, SBOMs or independent review.

## Public API conditions

Use only for authorized non-commercial public artifacts. Commercial products,
services and business workflows must not use the free API. Even queried hashes
may become part of the VirusTotal dataset. Never query private or sensitive
artifacts, ROMs, BIOS, credentials or third-party material without authorization.
Review [public API limits](https://docs.virustotal.com/reference/public-vs-premium-api)
and [file reports](https://docs.virustotal.com/reference/file-info).

The public quota is 4 requests/minute and 500/day. Each explicit invocation
makes at most one GET with no automatic retry. This does not enforce an
account-wide quota across repositories or machines. Serialize checks and respect
the shared quota, leave at least 16 seconds between requests, and stop on 429.
No additional paid account or API usage is authorized.

## Local use

From a reviewed Core checkout (or installed package):

```powershell
python -m navi_core.autoverify "C:\release\game.exe"
python -m navi_core.autoverify "C:\release\game.exe" --expected-sha256 YOUR_RELEASE_SHA256 --lookup-public-noncommercial
```

Set VT_API_KEY in the local process environment for the second command only;
never commit it or pass it as a command argument. Without explicit opt-in the
first command does not contact VirusTotal. The JSON is printed to stdout.
The optional expected hash must come from a trusted, independently verified
release manifest, not from an untrusted artifact.

Exit 0 means a matching report no more than 30 days old reports zero malicious
or suspicious detections and meets the basic response checks. Exit 2 means
unverified or review required, including offline hash-only, unknown hash, stale
analysis, timeout, quota, invalid response and detected threats. An unsupported
engine is recorded; even a zero-detection report does not prove safety.
Do not automatically dismiss generic detections or treat engine votes as proof
of malware. Review them independently. Report timestamps are UTC epoch seconds.

For an unknown public artifact, use the VirusTotal website manually only after
reviewing its disclosure terms and rights to the file. Rerun later with the same
hash. No automated binary upload in this preview.

## Reusable workflow

The optional workflow is callable only from trusted main/tag push or manual
dispatch in a public repository with explicit approval. It expects a single
named artifact from the same run and a basename within that artifact. Pass a
reviewed immutable Core commit SHA both in the workflow reference and core_sha.
Use one trusted caller, not fork PRs or pull_request_target. Add VT_API_KEY to
the caller repository secrets. Do not use secrets: inherit.

The workflow preserves a JSON report when the scan fails; it never publishes a
release. The caller must explicitly require a successful, non-skipped scan job
and independent local checks before publishing, if making this a gate. Do not
enable a publication gate before testing the full pipeline. Workflow concurrency
is repository-local, not a global quota manager. Review the actual artifact
rights and immutable provenance; a filename filter cannot establish rights.

## Acceptance status

Offline tests cover classification, hash integrity, missing key, opt-in, HTTP
errors, bounded responses and no retry. Live API authentication, workflow
end-to-end acceptance and project-specific build provenance are separate.
No real VT scan or release is claimed.
