# Universal Agent Interface (UAI)

NAVI assists the selected external agent. The generic portable interface is
available without installing any AI SDK, subscription, credential or other agent.
The named repository adapters remain optional. Manus and other interfaces can
consume the portable packet if they support copying/uploading context; no native
Manus integration, automatic ingestion or authenticated host execution is claimed.

## Portable packet

    navi assist --profile game-recomp --format markdown
    navi assist --profile knowledge-system --format json

Save or paste the output into the selected host's instructions/context interface.
The packet contains only public references, the canonical policy, profile,
lifecycle, and brief/handoff/lesson contracts. No project files, raw prompts,
private memory, environment variables or credentials are included. It does not
install, configure, or invoke a host. If a host cannot run commands, its responses
remain advisory and execution checks must be independently verified.

## Structured handoff

    navi handoff-check --file handoff.json

Use the handoff contract for session transfer. In-progress and blocked tasks need
next steps; blocked tasks need blockers. Complete requires passed acceptance
criteria with evidence and no blockers. Passed verification must report exit
code zero and evidence. These are structural checks on self-reported data,
not attestation or a gate that prevents arbitrary host writes.

## Optional MCP

The optional extra uses the official Python MCP SDK 1.x, MIT licensed.
Install in a separate reviewed virtual environment:

    python -m pip install ".[mcp]"
    python -m navi_core mcp

Configure your selected MCP-capable host with the absolute Python executable and
arguments ["-I", "-m", "navi_core", "mcp"]. The server uses stdio only. It
exposes five public/reference tools: profiles, reference, assist, intake and
handoff-check. No filesystem-path arguments, private data retrieval, shell
execution, writes, external network or model calls are exposed. Input briefs
and handoffs are not retained by NAVI; do not include sensitive data because
the host may retain or transmit its own tool inputs. The extra is not required
for the CLI or any other agent. Transitive dependencies resolve at install;
review the environment and dependency advisories before use. Test the actual
host configuration separately. The SDK smoke test establishes protocol
interop with a real SDK client, not compatibility with every host or latest
protocol version.

SDK documentation: https://py.sdk.modelcontextprotocol.io/v1/
Transport documentation: https://py.sdk.modelcontextprotocol.io/v1/client/transports/
