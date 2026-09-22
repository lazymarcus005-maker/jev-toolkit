---
name: jev-decision
description: >
  Apply Jev as an optional bounded-decision primitive inside agent workflows.
  Use only for meaningful semantic choices, ranking, sufficiency checks, and
  workflow branching. Never use it as a mandatory hop for deterministic work.
---

# Jev Decision Skill

Tools perform actions. Skills define workflows. The main LLM reasons and
synthesizes. Jev makes bounded semantic decisions. Policy enforces hard rules.

Invoke Jev only when there is a real checkpoint, at least two valid enumerable
choices, and semantic interpretation is required. Do not use it for parsing,
arithmetic, exact policy checks, direct reads, one-action choices, open-ended
analysis, code generation, shell generation, or security authorization.

Prepare compact state containing the goal, scope, material findings, completed
checks, and relevant hypotheses. Do not send large raw logs or secrets.

Supported primitives:

- `decide`: choose exactly one bounded outcome.
- `rank`: order pre-filtered candidates.
- `evaluate`: classify into bounded categories.
- `enough`: classify evidence as `sufficient`, `insufficient`, or `contradictory`.

Accept a result only when confidence meets the configured threshold (default
0.70). On failure, timeout, invalid output, invalid choice, or low confidence,
the parent workflow chooses from the exact same choices using its primary model.
Jev never overrides parent-skill constraints and never authorizes destructive
actions.
