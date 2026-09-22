# Jev Agent Toolkit

A shared, optional decision layer for agent ecosystems.

Tools perform actions. Skills define workflows. The main LLM reasons and
synthesizes. Jev handles bounded semantic decisions. Policy enforces hard
constraints.

## Quick start

```bash
python3.11 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/jev --config config/jev.example.yaml config validate
```

Run the HTTP API and streamable HTTP MCP endpoint with `jev serve`; use
`jev mcp` for STDIO MCP. Provider keys are read only from the environment.
The generic contract is in [docs/decision-contract.md](docs/decision-contract.md).
More command and endpoint examples are in [docs/usage.md](docs/usage.md).

The reference deployment is [docker/docker-compose.example.yml](docker/docker-compose.example.yml).
The generic skill and Elastic integration are under `skills/`, with an
executable three-round simulation in `examples/elastic_investigation.py`.
