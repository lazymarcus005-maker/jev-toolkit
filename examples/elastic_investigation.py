"""Executable, provider-free illustration of the Elastic/Jev integration pattern."""

from __future__ import annotations

from dataclasses import dataclass

from jev.config import JevConfig, ProviderConfig, RoutingConfig, TelemetryConfig
from jev.core import JevCore
from jev.models import DecisionRequest, ProviderDecision


@dataclass
class SimulatedElastic:
    """Represents an Elastic MCP; it returns compact evidence, not raw logs."""

    evidence: tuple[dict, ...] = (
        {"finding": "500 rate increased at 14:20", "completed": "error_distribution"},
        {"finding": "94 percent of failures originate from pod-7f8c", "completed": "instance_distribution"},
        {"finding": "failed traces correlate with account-service resets", "completed": "trace_correlation"},
    )

    def investigate(self, action: str, round_number: int) -> dict:
        item = self.evidence[min(round_number - 1, len(self.evidence) - 1)]
        return {"action": action, **item}


class ScriptedProvider:
    name = "example"
    model = "scripted"

    def __init__(self):
        self.actions = iter(("inspect_instance", "inspect_downstream", "inspect_deployment"))

    def decide(self, request: DecisionRequest) -> ProviderDecision:
        return ProviderDecision(next(self.actions), 0.91, self.model)

    def health(self) -> bool:
        return True


def run_three_round_example() -> list[dict]:
    config = JevConfig(
        providers={"example": ProviderConfig("example", "typesafe", base_url="http://example")},
        routing=RoutingConfig("example"),
        telemetry=TelemetryConfig(enabled=False),
    )
    core = JevCore(config, providers={"example": ScriptedProvider()})
    elastic = SimulatedElastic()
    state = {"goal": "identify root cause of payment 500 spike", "findings": [], "completed_checks": []}
    rounds = []
    for iteration in range(1, 4):
        decision = core.decide(DecisionRequest(
            decision="incident_next_action",
            goal=state["goal"],
            state=state,
            choices=("inspect_instance", "inspect_downstream", "inspect_deployment", "conclude"),
            metadata={"skill": "elastic-investigation", "iteration": iteration},
        ))
        evidence = elastic.investigate(decision.choice or "conclude", iteration)
        state["findings"].append(evidence["finding"])
        state["completed_checks"].append(evidence["completed"])
        rounds.append({"round": iteration, "jev": decision.to_dict(), "evidence": evidence})
    return rounds


if __name__ == "__main__":
    import json
    print(json.dumps(run_three_round_example(), indent=2))
