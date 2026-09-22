import logging

import pytest

from jev.config import JevConfig, ProviderConfig, RoutingConfig, TelemetryConfig
from jev.core import JevCore, normalize_confidence
from jev.errors import InvalidProviderResponse, RequestValidationError
from jev.models import DecisionRequest, ProviderDecision


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def decide(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return self.result

    def health(self):
        return True


def config(*fallback):
    return JevConfig(
        providers={
            "primary": ProviderConfig("primary", "typesafe", base_url="http://primary"),
            "backup": ProviderConfig("backup", "openai-compatible", base_url="http://backup", model="model"),
        },
        routing=RoutingConfig("primary", tuple(fallback)),
        telemetry=TelemetryConfig(enabled=False),
    )


def request(**overrides):
    values = dict(decision="next", goal="choose next step", state={"signal": 2}, choices=("inspect", "conclude"))
    values.update(overrides)
    return DecisionRequest(**values)


def test_confidence_normalization_accepts_fraction_and_percentage():
    assert normalize_confidence(0.72) == 0.72
    assert normalize_confidence(72) == 0.72


def test_confidence_out_of_range_is_rejected():
    with pytest.raises(InvalidProviderResponse):
        normalize_confidence(101)


def test_successful_decision_has_stable_contract():
    provider = FakeProvider(ProviderDecision("inspect", 0.88, "jev"))
    result = JevCore(config(), providers={"primary": provider}).decide(request())
    assert result.to_dict() == {
        "decision": "next", "choice": "inspect", "confidence": 0.88,
        "provider": "primary", "model": "jev", "fallback_used": False,
        "latency_ms": result.latency_ms, "fallback_reason": None, "agent_fallback": False,
    }


def test_timeout_uses_configured_technical_fallback():
    primary = FakeProvider(error=TimeoutError())
    backup = FakeProvider(ProviderDecision("conclude", 0.91, "backup-model"))
    result = JevCore(config("backup"), providers={"primary": primary, "backup": backup}).decide(request())
    assert result.choice == "conclude"
    assert result.provider == "backup"
    assert result.fallback_used is True
    assert backup.calls == 1


def test_invalid_provider_response_uses_fallback():
    primary = FakeProvider(ProviderDecision("not-allowed", 0.95))
    backup = FakeProvider(ProviderDecision("inspect", 0.91))
    result = JevCore(config("backup"), providers={"primary": primary, "backup": backup}).decide(request())
    assert result.choice == "inspect"
    assert result.provider == "backup"


def test_low_confidence_falls_back_to_agent():
    primary = FakeProvider(ProviderDecision("inspect", 0.69))
    backup = FakeProvider(ProviderDecision("conclude", 0.99))
    result = JevCore(config("backup"), providers={"primary": primary, "backup": backup}).decide(request())
    assert result.choice is None
    assert result.agent_fallback is True
    assert result.fallback_reason.startswith("low_confidence")
    assert backup.calls == 0


def test_request_requires_at_least_one_choice():
    with pytest.raises(RequestValidationError):
        JevCore(config(), providers={"primary": FakeProvider()}).decide(request(choices=()))


def test_secrets_and_raw_state_are_not_logged(caplog):
    provider = FakeProvider(ProviderDecision("inspect", 0.88))
    with caplog.at_level(logging.INFO, logger="jev.telemetry"):
        JevCore(config(), providers={"primary": provider}).decide(request(state={"secret": "do-not-log"}))
    assert "do-not-log" not in caplog.text
