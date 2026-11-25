# Experimental live inference benchmark

This separate CI workflow exercises actual local CPU inference on a standard
public GitHub-hosted runner, without private input or API credentials.
It downloads the official Ollama v0.40.18 Linux amd64 release with its
published SHA-256 and the Apache-2.0 Qwen2.5 1.5B instruct Q4_K_M model.
The model tag is checked against the published manifest digest prefix
65ec06548149 and the full observed digest is recorded. A prefix check is
not full cryptographic pinning of the model. The workflow is restricted to
same-repository PRs modifying this workflow and explicit manual dispatch.
It does not run for every change. No model weights, server logs, or private
data are uploaded; only runtime/model metadata and the synthetic report.

One paired DAG trial is a live transport/inference smoke, not a statistical
comparison, coding benchmark, Nexus validation, or production security
certification. A model gate failure is deliberately reported as failure.
The runner downloads public dependencies/models from the network; inference
uses loopback with cloud disabled as requested by configuration. This is
not an independently verified network sandbox. A 20-minute job deadline
and explicit client timeouts bound the experiment.
