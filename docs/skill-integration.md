# Applying Jev to Existing Skills

Add Jev only at explicit semantic checkpoints. A parent skill should declare
the checkpoint, prepare compact state, enumerate valid choices, define its
fallback, and set an iteration/stopping limit. Deterministic work stays in
deterministic code; domain tools remain responsible for actions.

The integration recipe is:

1. identify a checkpoint such as next inspection, sufficiency, ranking, retry,
   or escalation;
2. remove invalid candidates and pass compact evidence;
3. call one generic Jev primitive;
4. validate and follow the bounded result;
5. fall back to the main model on failure or low confidence.

Parent policy remains authoritative. Jev cannot approve deletion, secret
exposure, protected-branch pushes, or other destructive actions.
