# Architecture

The agent host and skill layer own workflow and domain tools. Jev Core owns
request validation, provider routing, strict response validation, confidence
policy, fallback signaling, and telemetry. MCP, CLI, and HTTP are adapters over
that same core.

```text
Agent -> Skill -> (Domain tools, Jev adapter) -> Jev Core -> Provider
```

Tools perform actions; skills define workflow; the main LLM reasons and
synthesizes; Jev makes bounded semantic decisions; policy enforces hard rules.
Jev never executes domain actions and has no domain-tool dependency.
