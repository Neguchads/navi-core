# Local execution gate

A trusted local controller may use navi_core.execution_gate to sign a
short-lived, low-risk fixture operation bound to authority, ledger,
provider, operation ID, input digest and maximum tokens. An atomic SQLite
transaction consumes the approval once and reserves budget before execution.
Settlement returns unused reservations only when usage is known; unknown
usage charges the full reservation and overrun freezes the ledger. Restart
does not release pending reservations. No high-risk operations are allowed.

The signing key and ledger must remain under the trusted controller's
exclusive access. This is an HMAC local authority mechanism, not human
authentication, remote attestation or a complete authorization service.
An untrusted worker must never get the key or database. The controller must
bind the authorized action/provider and enforce its requested cap in the
actual provider call. Server-reported usage can be wrong. No hard external
billing limit is implied. The API is not yet wired to Nexus or external
agent CLIs. It is a testable prerequisite for such an integration.

## Governed Ollama fixture call

The explicitly executed `navi providers` path now reserves context plus output allowance before the HTTP transport. It binds the exact request to a one-use HMAC approval created by the local controller. Identity mismatch, incomplete/unknown usage and reported overrun fail closed. A failed request is charged conservatively in the ephemeral ledger; it is not retried automatically. Successful reports contain reservation and settlement metadata. The temporary ledger is deleted after the call, so this is not persistent account-wide or cross-session budget enforcement. The existing paired comparison still has its own requested caps; it does not share this ledger. The live public workflow includes a real governed call. Nexus integration and remote/human authorization remain separate gates.
