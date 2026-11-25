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
