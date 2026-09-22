# Operations

`/health` is a process check and should be used by load balancers and Docker.
`/ready` verifies that the configured default provider is available; it may
perform provider model discovery. A provider outage should normally produce a
safe agent fallback for a decision rather than crash the workflow.

Telemetry records decision name, provider, model, latency, confidence, choice,
candidate count, fallback metadata, skill/workflow metadata, and iteration.
Raw state logging is disabled by default and provider API keys are never
included. Keep the service stateless and restrict outbound network access to
configured provider endpoints.
