# Manual host acceptance lab

This test checks whether an authenticated host can retrieve a fresh challenge
from its repository instructions and solve a small independent dependency task.
It does not call Codex, Claude or Copilot automatically, read tokens, change
billing, or install global configuration.

```powershell
navi host-lab --mode prepare --directory D:\NAVI-Lab\host-acceptance
```

Open only the corresponding codex, claude or copilot subdirectory in that
host's normal authenticated interface. Use a read-only/no-tools mode where
available. Copy PROMPT.txt from the parent yourself; do not give the host
access to expected.json. Do not open private repositories for this test.
If a host needs a Git repository, initialize only the synthetic directory
with an empty Git template and no remote. Record the actual host version
or UI version as shown by the host. For Copilot, confirm available Free
credits, no paid overage, and one short request. Do not retry automatically.

Save the host's JSON response outside its workspace, for example
D:\NAVI-Lab\codex-answer.json, then:

```powershell
navi host-lab --mode check --directory D:\NAVI-Lab\host-acceptance --host codex --submission D:\NAVI-Lab\codex-answer.json --reported-version ACTUAL_VERSION --output D:\NAVI-Lab\codex-receipt.json
```

Repeat for claude and copilot, using independent answers. Missing credentials,
unavailable host, or failed challenge remain unverified. These are manually
submitted answers and reported versions, not attested host identity or proof
that a host automatically loaded the instructions, used no global config, or
obeyed filesystem restrictions. Never expose actual account or session data.
Generated files are synthetic. Keep receipts local. Global skills and private
archives are not part of this test and remain quarantined.
