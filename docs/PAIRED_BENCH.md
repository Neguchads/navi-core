# Paired synthetic model experiment

Run the plan (no HTTP):

```powershell
navi compare --model qwen3.5:9b --trials 3
```

Execute explicitly against a reviewed local Ollama installation:

```powershell
navi compare --model qwen3.5:9b --trials 3 --execute --output comparison.json
```

Compares one direct answer against a two-call sequential draft/review, using
identical public fixtures, explicit model tag, alternating strategy order,
same requested output-token allowance per trial, repeated seed schedule and
independent final checks. Reports partial results and stops on blocked
transport, usage mismatch or failed security gate. The draft is untrusted
JSON data only; no tools or candidate code are executed. Each trial has a
requested output cap, a post-response reported input cap and a client time
allowance. The socket timeout is not a hard total deadline, and the server
may continue computing. Model identity is a reported tag, not an attested
digest. Costs are unknown. The benchmark does not measure actual software
engineering or the Nexus runtime. Tests mock the provider transport; actual
local Ollama results must be separately obtained. Do not publish private
results, and do not interpret small visible-fixture samples as proof that
one strategy is superior. A skipped or blocked pair is not a pass.
