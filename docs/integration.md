# Agent Integration

Prefer MCP, use the CLI when MCP is inconvenient, and use HTTP for custom
harnesses. All three call the same Jev Core and return the same decision
contract. Existing domain MCP servers remain unchanged; do not route every tool
call through Jev.

When Jev is unavailable, times out, returns invalid output, or has low
confidence, the skill's primary model chooses among the exact same bounded
choices. Jev is optional and must not be used as a hard security policy engine.
