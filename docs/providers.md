# Provider Configuration

Jev separates the decision contract from providers. Skills call generic Jev
primitives and never depend on provider response fields.

TypeSafe uses `POST /v1/systemone` and `GET /v1/models`, with Bearer auth and
`model: auto` discovery. OpenRouter and custom endpoints use the OpenAI
compatible `POST /chat/completions` contract with strict JSON parsing. A custom
provider specifies its own base URL, model, timeout, and API-key environment
variable.

Laya Local is an optional CPU-only provider. Install it with
`jev-agent-toolkit[laya]`, choose `typed-decisions`, `multilingual`, or
`router`, and set `HF_HOME`/`cache_dir` to a persistent model cache. Its
translation to Laya typed questions is private to `LayaLocalProvider`.

Technical failures try the configured provider fallback list. Low confidence
normally returns to the primary agent, not another provider. API keys belong in
environment variables; never put secret values in YAML or commit `.env` files.
