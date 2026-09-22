---
name: elastic-investigation-with-jev
description: >
  Investigate API incidents through an Elastic MCP and use Jev for bounded
  next-step decisions without sending raw logs to the decision service.
---

# Elastic Incident Investigation with Jev

Elastic MCP retrieves and aggregates evidence. Jev selects among bounded
branches. The main LLM maintains hypotheses and writes the final RCA. The
skill owns workflow, guardrails, valid choices, and stopping conditions.

## Workflow

1. Define incident question, service, environment, time window, and IDs.
2. Establish a compact baseline: rates, latency percentiles, error types,
   instance distribution, traces, and dependency latency.
3. Keep compact state with findings and completed checks; do not pass raw logs.
4. At a checkpoint with two or more valid branches, call `incident_next_action`
   with only choices valid for the current incident.
5. Translate the returned intent into an Elastic MCP query. Jev never creates
   or executes ES|QL/KQL.
6. Reduce results, update hypotheses, and repeat up to 12 iterations.
7. Use `evidence_sufficient` when it is genuinely unclear whether to continue.
   `sufficient` leads to final synthesis; `insufficient` continues; and
   `contradictory` revisits hypotheses.

Typical bounded choices are `inspect_trace`, `inspect_metrics`,
`inspect_downstream`, `inspect_upstream`, `inspect_instance`,
`inspect_deployment`, `inspect_error_pattern`, `widen_time_window`,
`narrow_time_window`, `compare_healthy_period`, and `conclude`.

If Jev fails, times out, returns an invalid action, or falls below the
threshold, the main model chooses from the same bounded set. At the iteration
limit, synthesize current evidence and state what remains uncertain.

The final report includes scope, timeline, strongest evidence, root-cause
hypothesis, supporting and contradictory evidence, impact, remediation, and
remaining uncertainty. High Jev confidence is not proof of causality.
