# Jev Agent Toolkit — System Design

Jev is a reusable decision primitive for bounded semantic checkpoints in agent
workflows. Existing skills remain authoritative for workflow, allowed
transitions, candidate choices, safety constraints, and stopping conditions.

The core owns request validation, provider routing, provider-result
normalization, strict choice validation, confidence policy, technical fallback,
and telemetry. It does not execute shell commands, push branches, mutate
databases, deploy resources, or enforce hard security policy.

```text
Agent host -> Skill -> Jev adapter -> Jev Core -> TypeSafe/OpenRouter/custom
             Skill -> domain tools -> compact workflow state
```

Finite choices such as `inspect_trace`, `inspect_metrics`, or `conclude` belong
in Jev. Open-ended reasoning and final synthesis remain with the main LLM. A
low-confidence or failed Jev call returns control to the main agent. V1 is
stateless and does not require Redis or a database. Stable primitives are
`decide`, `rank`, `evaluate`, and `enough`.
