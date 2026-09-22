# Implementation Handoff

This repository implements a reusable optional Jev decision service. It
supports TypeSafe, OpenAI-compatible/OpenRouter, and custom providers; strictly
validates bounded choices; applies confidence thresholds; emits structured
telemetry without raw state; and falls back to the parent agent when it cannot
safely decide.

Required interfaces are HTTP, CLI, STDIO MCP, and streamable HTTP MCP. Docker
deployment is multi-stage, non-root, health-checked, and configured through
environment-based secrets. The Elastic example demonstrates three investigation
rounds while keeping evidence retrieval and action execution in the skill/domain
tool layer.

Acceptance requirements include provider timeout and invalid-response fallback,
confidence normalization and threshold behavior, explicit-choice validation,
secret-safe telemetry, MCP discovery and invocation, JSON CLI state input,
configuration errors with non-zero exit, doctor diagnostics, Docker health and
non-root settings, and skill fallback to the main reasoning model.
