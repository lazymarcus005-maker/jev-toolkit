# Docker Deployment

The recommended deployment is one stateless, non-root container exposing the
HTTP API on port 8080 and streamable HTTP MCP on port 8081. See
`docker/docker-compose.example.yml`.

The example uses a read-only root filesystem, `/tmp` tmpfs, no privileges, a
health check, and environment-based secrets. `/health` checks process health;
`/ready` checks configured default-provider readiness. Provider outages do not
make process health fail. No Redis or database is required for V1.
