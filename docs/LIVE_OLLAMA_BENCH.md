# Experimental live inference benchmark

This separate CI workflow exercises actual local CPU inference on a standard
public GitHub-hosted runner, without private input or API credentials.
It downloads the official Ollama v0.40.18 Linux amd64 release with its
published SHA-256 and the Apache-2.0 Qwen2.5 7B instruct Q4_K_M model.
The model tag is checked against the published manifest digest prefix
845dbda0ea48 and the full observed digest is recorded. A prefix check is
not full cryptographic pinning of the model. The workflow is restricted to
same-repository PRs modifying this workflow and explicit manual dispatch.
It does not run for every change. No model weights, server logs, or private
data are uploaded; only runtime/model metadata and the synthetic report.

Three paired DAG trials is a live transport/inference smoke, not a statistical
comparison, coding benchmark, Nexus validation, or production security
certification. A model gate failure is deliberately reported as failure.
The runner downloads public dependencies/models from the network; inference
uses loopback with cloud disabled as requested by configuration. This is
not an independently verified network sandbox. A 30-minute job deadline
and explicit client timeouts bound the experiment.

Initial 1.5B trial (run 45537870089): both strategies failed correctness; one direct call used 121 input/23 output tokens, sequential review 294 input/46 output. Full report remains in the original Actions run. This follow-up changes model capacity and repetition count, not the fixture or verifier. It is not a controlled cross-model speed comparison.
