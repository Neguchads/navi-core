# Copilot Free routing

Use the free Copilot account as an optional manual micro-task assistant.
Do not schedule model calls from Actions, assign cloud agents, or enable paid
overage. GitHub documents 2,000 monthly completions and limited AI credits
for Free, with automatic model selection. Credits are not fixed chat counts.
Check current account usage and disable additional paid usage in billing.
The included monthly allowance resets at 00:00 UTC on the first of the month.

- 70% monthly target, 30% reserve; estimated per-task share at most 5%.
- Only low-risk public tasks, at most two files and 80 changed lines.
- Format/lint use deterministic tools; private/unknown inputs remain local.
- Unknown, stale, over-budget or paid-usage-enabled requests are not routed to Copilot.
- Larger tasks pause for human review; no automatic provider calls or switches.

Example (illustrative usage only, replace with current observed values):

```powershell
navi copilot-plan --kind docs --risk low --visibility public --files 1 --lines 20 --used-percent 25 --estimate-percent 2 --checked-on ([DateTime]::UtcNow.ToString('yyyy-MM-dd')) --paid-usage-blocked
```

Round actual used credits upward, and use a conservative estimated percentage
of the included monthly allowance. If unknown, omit the value; the gate will
choose local review. Confirm billing separately at https://github.com/settings/billing.
The flag is a human attestation, not a setting change. Same-day usage can
be stale; check immediately before the request and again afterwards. The
policy has no atomic cross-session reservation, no actual usage API, no
cost guarantee and cannot prevent direct Copilot use outside NAVI. The
completion allowance is separate. If available, use the official CLI
session limit, which is a preview soft cap with minimum 30 AI credits;
do not use that limit as proof of zero overage.

The common repository policy and conditional Free micro-task profile are emitted by
`navi agents --host copilot --mode apply` for repositories with a manifest.
Existing differing instructions are never overwritten. The Core repository explicitly opts into the Free micro-task policy. Other providers are not required.

Official references:
- https://docs.github.com/en/copilot/get-started/plans
- https://docs.github.com/en/copilot/concepts/billing-and-usage/individuals/billing
- https://docs.github.com/en/copilot/how-tos/manage-and-track-spending/monitor-ai-usage
- https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli/set-session-limit
