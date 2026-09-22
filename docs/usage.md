# Usage

Validate configuration:

```bash
jev config validate --config config/jev.yaml
jev doctor --config config/jev.yaml
```

Make a bounded decision from a compact JSON state file:

```bash
jev decide --config config/jev.yaml \
  --decision incident_next_action \
  --goal 'identify the source of elevated API latency' \
  --state incident-state.json \
  --choices inspect_database,inspect_downstream,inspect_node,conclude
```

HTTP clients use `POST /v1/decide`, `/v1/rank`, `/v1/evaluate`, or
`/v1/enough`. MCP clients use the `jev_decide`, `jev_rank`, `jev_evaluate`,
`jev_enough`, and `jev_health` tools. STDIO MCP is `jev mcp`; streamable HTTP
MCP is available at `/mcp` on the configured MCP port.

An `agent_fallback: true` response is not an action authorization. The parent
skill must choose from its same candidates and continue according to policy.
