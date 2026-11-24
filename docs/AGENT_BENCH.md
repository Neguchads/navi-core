# NAVI Agent Bench — Phase 3C

This is an **offline synthetic evaluation harness**, not a measured LLM or
Nexus benchmark. Four public fixtures cover DAG order, artifact integrity,
budget reservation and untrusted instruction/governance decisions. A trusted
reference solver and separate verifier module exercise the harness.
Candidate submissions are JSON data only, never executed.

```sh
navi bench
navi bench --mode reference
navi bench --mode evaluate --case BENCH-DAG-001 --submission answer.json
```

Use --output to write a new local report (no overwrite). Evaluate requires an
explicit case. Reports contain answer and fixture hashes, verifier/harness
hashes, Python/platform, byte budget, observed local verification time and
the mandatory correctness/security/byte-budget gates. No aggregate score can
override a failed gate. Provider generation time, tokens and cost are null
for external submissions; reference generation time is Python only.

## Comparative protocol (planned)

Compare single-agent, sequential, static DAG and Nexus-adaptive using the
same pinned model/version, task revision, identical fresh workspaces,
tool permissions, acceptance tests, time/token/cost ceilings and repeated
trials. Keep independent held-out tests outside the model context. Record
actual provider usage when available; unknown usage remains unknown.
Report pass rate and paired results, median and tail latency, cost and
recovery, sample size, failures and variance. Stop any strategy on a critical
security violation. No autonomous publication.

The four current fixtures are visible synthetic smoke cases; they are not
held-out tasks and cannot establish agent quality. Actual coding benchmarks
require isolated filesystem/network and process-tree termination, approved
providers, budget reservation, trusted external telemetry and independent
verification. No arbitrary candidate execution, hard provider deadline,
token reservation or live comparison is implemented in Phase 3C.
No private Nexus code or data is included.
