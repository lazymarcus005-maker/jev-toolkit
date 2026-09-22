import json
import os
import subprocess
from pathlib import Path

from jev.config import JevConfig, ProviderConfig, RoutingConfig, TelemetryConfig
from jev.core import JevCore
from jev.errors import InvalidProviderResponse
from jev.models import DecisionRequest, ProviderDecision


ROOT = Path(__file__).parents[1]


class Provider:
    name = "provider"
    model = "model"

    def __init__(self, choice="inspect"):
        self.choice = choice

    def decide(self, request):
        return ProviderDecision(self.choice, 0.9, self.model)

    def rank(self, request, items):
        return type("Rank", (), {"ranking": [{"id": str(item["id"]), "score": 1.0 if index == 0 else 0.2} for index, item in enumerate(items)]})()

    def health(self):
        return True


def core():
    config = JevConfig({"provider": ProviderConfig("provider", "typesafe", base_url="http://provider")}, RoutingConfig("provider"), telemetry=TelemetryConfig(enabled=False))
    return JevCore(config, providers={"provider": Provider()})


def test_mcp_operations_share_core_contract():
    from jev.interfaces import invoke
    request = {"decision": "check", "goal": "classify", "state": {}, "choices": ["inspect", "conclude"]}
    assert invoke(core(), "decide", request)["choice"] == "inspect"
    assert invoke(core(), "evaluate", request)["choice"] == "inspect"
    enough_config = JevConfig({"provider": ProviderConfig("provider", "typesafe", base_url="http://provider")}, RoutingConfig("provider"), telemetry=TelemetryConfig(enabled=False))
    enough_core = JevCore(enough_config, providers={"provider": Provider("sufficient")})
    assert invoke(enough_core, "enough", {"decision": "evidence_sufficient", "goal": "check", "state": {}})["choice"] == "sufficient"
    ranking = invoke(core(), "rank", {"decision": "relevance", "goal": "find", "state": {}, "items": [{"id": "a"}, {"id": "b"}]})
    assert [item["id"] for item in ranking["ranking"]] == ["a", "b"]


def test_no_choice_provider_response_is_rejected():
    class BadProvider(Provider):
        def decide(self, request):
            raise InvalidProviderResponse("missing choice")
    result = JevCore(JevConfig({"provider": ProviderConfig("provider", "typesafe", base_url="http://provider")}, RoutingConfig("provider"), telemetry=TelemetryConfig(enabled=False)), providers={"provider": BadProvider()}).decide(DecisionRequest("d", "g", {}, ("a", "b")))
    assert result.agent_fallback is True
    assert result.choice is None


def test_cli_reads_json_state_and_configuration_errors_are_nonzero(tmp_path):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"signal": "x"}))
    config = tmp_path / "config.yaml"
    config.write_text("""
providers:
  fake:
    type: typesafe
    enabled: true
    base_url: http://fake
routing:
  default: fake
telemetry:
  enabled: false
""")
    # The provider is unreachable, but the CLI still returns the safe agent fallback JSON.
    completed = subprocess.run([str(ROOT / ".venv/bin/jev"), "decide", "--config", str(config), "--decision", "d", "--goal", "g", "--state", str(state), "--choices", "a,b"], capture_output=True, text=True)
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["agent_fallback"] is True
    bad = subprocess.run([str(ROOT / ".venv/bin/jev"), "--config", str(tmp_path / "missing.yaml"), "config", "validate"], capture_output=True, text=True)
    assert bad.returncode != 0
