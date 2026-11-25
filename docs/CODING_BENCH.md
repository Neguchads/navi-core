# Isolated coding benchmark

A real model repairs a deliberately broken pagination function. Two strategies,
single and sequential review, run three paired trials. Twelve independent
acceptance cases include invalid inputs, empty and exact-boundary pages.
The reference and original broken source must pass/fail respectively before
model inference. The verifier rejects unapproved Python AST constructs and
runs candidate code only in a non-root read-only container with no network,
capabilities, credentials or Docker socket, using bounded CPU/memory/PIDs.
The candidate receives inputs, never expected outputs. Docker image ID and
observed registry digests are recorded; the initial image tag is mutable.
Model calls use loopback, public fixture only, and output caps. These are
bounded coding experiments, not general autonomous repository agents. Model
quality, security isolation, and Nexus adoption are separate criteria.
The container is defense in depth, not a proof of kernel-level isolation.
No private source, credentials or generated candidate source are uploaded.

## Initial run

Run 45539334308 completed all six coding trials with 11/12 checks each, no full pass. Both strategies failed. The follow-up explicitly clarifies the already existing boundary rule; acceptance cases are unchanged. Failed case indices are recorded without supplying hidden expectations to the model. This is a new prompt revision, not a controlled improvement claim.

## Protocol v3: public development feedback

The second run 45539924660 produced one complete pass and five failures on the valid empty list case. The next protocol compares single inference with adaptive development-test feedback, rather than unconditional review. Both receive three public examples, distinct from the unchanged twelve final cases. Adaptive spends at most 256 + 256 output tokens, but skips the repair call if all development examples pass. Final acceptance outcomes are never supplied during that trial. This is a new protocol and must not be pooled with prior trials. Since fixtures are public and reused in experiment development, this is not a blind held-out benchmark. A complete pass is required for every trial; failures remain visible.

## Successful protocol v3 run

Run 45545522360: six of six complete passes; 72/72 final acceptance checks, identical generated source hash for all six trials. Both strategies used 867 input and 366 output tokens across three trials. Adaptive skipped all three repair calls because development tests passed. This proves the restricted fixture and skip-review branch; the actual repair branch is covered by mocked transport tests, not this live run. Cold-start bias prevents conclusions from observed latency. The public reused fixture is not a blind or generalized engineering benchmark.

## Reproduction and specialist model follow-up

Repeat run 45546451027 failed one of six complete trials: the direct baseline missed final case index 3, exact page boundary; adaptive passed 3/3. Across the two v3 runs direct passed 5/6 and adaptive 6/6. This disproves a guarantee of perfect reproduction. Preserve the failed run. Next compare Qwen2.5-Coder 7B Instruct Q4_K_M (Apache-2.0, manifest prefix dae161e27b0e; official https://ollama.com/library/qwen2.5-coder:7b-instruct), leaving the fixture, development tests and all final acceptance cases unchanged. Do not pool different model runs or treat this repeated public fixture as a blind benchmark.

## Maintenance reproduction
Original specialist run 45547115760: 5/6 full passes; single seed 42 failed exact-boundary case index 3, adaptive 3/3. This is model-quality failure, not infrastructure failure. Preserve this evidence. Reconcile branch with current main, pin the verifier image to the previously observed registry digest, require genuine negative-fixture mismatch rather than accepting infrastructure failure, and compare JSON results with type-sensitive serialization. Keep all twelve acceptance cases and seeds unchanged. One fresh reproduction is not proof of generalized ability or Nexus acceptance. Merge only if current CI and the unchanged strict live gate pass; do not rerun selectively until green.
