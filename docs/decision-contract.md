# Decision Contract

Requests contain `decision`, `goal`, compact `state`, explicit `choices`,
optional `criteria`, and optional `metadata`. A successful decision returns the
same decision name, one requested choice, normalized confidence in `0..1`,
provider/model information, latency, and fallback metadata.

`choice` must be one of the request choices. Unknown provider output is rejected
and routed through technical fallback; if no safe provider result exists, the
response sets `agent_fallback: true` and the parent agent chooses from the same
set. Secrets, raw prompts, and raw workflow state are not normal telemetry.

`rank` accepts `{decision, goal, state, choices, items}` and returns
`{"ranking":[{"id":"...","score":0.0}]}`. `enough` defaults to
`sufficient`, `insufficient`, and `contradictory` when choices are omitted.
