import json

import pytest

from jev.config import ProviderConfig
from jev.errors import InvalidProviderResponse, ProviderError, UnsupportedChoice
from jev.models import DecisionRequest
from jev.providers.openai_compatible import OpenAICompatibleProvider
from jev.providers.typesafe import TypeSafeProvider


def req():
    return DecisionRequest("next", "choose", {"x": 1}, ("inspect", "conclude"), {"inspect": "look", "conclude": "stop"})


def patch_request_json(monkeypatch, module, value):
    monkeypatch.setattr(module, "request_json", lambda *args, **kwargs: value)


def test_typesafe_success_and_native_request_shape(monkeypatch):
    import jev.providers.typesafe as module

    calls = []
    def fake(*args, **kwargs):
        if kwargs["method"] == "GET":
            return {"models": [{"name": "jev-latest"}]}
        calls.append(kwargs["payload"])
        return {"model": "jev-latest", "answers": {"next": {"type": "choice", "choice": "inspect", "confidence": 0.9}}}
    monkeypatch.setattr(module, "request_json", fake)
    provider = TypeSafeProvider(ProviderConfig("typesafe", "typesafe", base_url="http://typesafe", api_key_env="KEY", model="auto"))
    monkeypatch.setenv("KEY", "secret")
    result = provider.decide(req())
    assert result.choice == "inspect"
    assert calls[0]["questions"]["next"]["type"] == "choice"
    assert calls[0]["model"] == "jev-latest"


def test_typesafe_rejects_unsupported_choice(monkeypatch):
    import jev.providers.typesafe as module
    monkeypatch.setenv("KEY", "secret")
    patch_request_json(monkeypatch, module, {"model": "m", "answers": {"next": {"choice": "danger", "confidence": 0.9}}})
    provider = TypeSafeProvider(ProviderConfig("typesafe", "typesafe", base_url="http://typesafe", api_key_env="KEY", model="m"))
    with pytest.raises(UnsupportedChoice):
        provider.decide(req())


def test_openai_compatible_valid_structured_response(monkeypatch):
    import jev.providers.openai_compatible as module
    monkeypatch.setenv("KEY", "secret")
    patch_request_json(monkeypatch, module, {"model": "served", "choices": [{"message": {"content": '{"choice":"conclude","confidence":0.8}'}}]})
    provider = OpenAICompatibleProvider(ProviderConfig("custom", "openai-compatible", base_url="http://llm/v1", api_key_env="KEY", model="m"))
    result = provider.decide(req())
    assert result.choice == "conclude"
    assert result.model == "served"


def test_openai_compatible_invalid_json_is_rejected(monkeypatch):
    import jev.providers.openai_compatible as module
    monkeypatch.setenv("KEY", "secret")
    patch_request_json(monkeypatch, module, {"choices": [{"message": {"content": "not json"}}]})
    provider = OpenAICompatibleProvider(ProviderConfig("custom", "openai-compatible", base_url="http://llm/v1", api_key_env="KEY", model="m"))
    with pytest.raises(InvalidProviderResponse):
        provider.decide(req())


def test_openai_compatible_health_probes_real_inference(monkeypatch):
    import jev.providers.openai_compatible as module
    provider = OpenAICompatibleProvider(ProviderConfig("custom", "openai-compatible", base_url="http://llm/v1", api_key_env="KEY", model="m"))
    monkeypatch.delenv("KEY", raising=False)
    assert provider.health() is False

    monkeypatch.setenv("KEY", "secret")
    calls = []
    def fake(url, *, method, headers, payload, timeout_ms):
        calls.append((method, url, payload))
        return {"choices": [{"message": {"content": "{}"}}]}
    monkeypatch.setattr(module, "request_json", fake)
    assert provider.health() is True
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/chat/completions")
    assert calls[0][2]["model"] == "m"

    def rejected(*args, **kwargs):
        raise ProviderError("provider request rejected: HTTP 402")
    monkeypatch.setattr(module, "request_json", rejected)
    assert provider.health() is False
