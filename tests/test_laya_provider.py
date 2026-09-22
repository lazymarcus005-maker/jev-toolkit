import threading
import time

import pytest

from jev.config import ProviderConfig
from jev.errors import InvalidProviderResponse, ProviderError, UnsupportedChoice
from jev.models import DecisionRequest
from jev.providers.laya import LayaLocalProvider


def config(**overrides):
    values = {
        "name": "laya",
        "type": "laya",
        "enabled": True,
        "model": "typed-decisions",
        "device": "cpu",
        "preload": False,
        "max_loaded_models": 2,
        "cache_dir": "/models",
        "timeout_ms": 3000,
    }
    values.update(overrides)
    return ProviderConfig(**values)


def request():
    return DecisionRequest(
        "incident_next_action",
        "identify the next investigation step",
        {"findings": ["database latency is elevated"]},
        ("inspect_database", "inspect_downstream", "conclude"),
        {"inspect_database": "inspect database signals", "inspect_downstream": "inspect dependency signals", "conclude": "stop investigation"},
    )


class FakeModel:
    def __init__(self, choice="inspect_database", confidence=0.88):
        self.choice = choice
        self.confidence = confidence
        self.calls = []

    def predict(self, state, questions, **kwargs):
        self.calls.append((state, questions, kwargs))
        return {"answers": {"incident_next_action": {"type": "choice", "choice": self.choice, "confidence": self.confidence}}}


def test_translation_and_lazy_model_loading():
    model = FakeModel()
    calls = []
    provider = LayaLocalProvider(config(), loader=lambda cfg: calls.append(cfg) or model)

    result = provider.decide(request())

    assert result.choice == "inspect_database"
    assert result.confidence == 0.88
    assert result.model == "typed-decisions"
    assert len(calls) == 1
    state, questions, kwargs = model.calls[0]
    assert state["goal"] == request().goal
    assert state["state"] == request().state
    assert questions["incident_next_action"]["type"] == "choice"
    assert questions["incident_next_action"]["criteria"]["conclude"] == "stop investigation"


@pytest.mark.parametrize("model,subfolder", [("typed-decisions", "typed-decisions"), ("multilingual", "multilingual")])
def test_model_selection_passes_checkpoint_to_loader(model, subfolder):
    calls = []
    provider = LayaLocalProvider(config(model=model), loader=lambda cfg: calls.append(cfg.model) or FakeModel())
    provider.decide(request())
    assert calls == [model]


def test_concurrent_first_load_initializes_once():
    model = FakeModel()
    calls = []
    lock = threading.Lock()

    def loader(cfg):
        with lock:
            calls.append(cfg.model)
        time.sleep(0.03)
        return model

    provider = LayaLocalProvider(config(), loader=loader)
    results = []
    threads = [threading.Thread(target=lambda: results.append(provider.decide(request()))) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(calls) == 1
    assert len(results) == 6


def test_preload_loads_before_first_decision():
    calls = []
    provider = LayaLocalProvider(config(preload=True), loader=lambda cfg: calls.append(cfg.model) or FakeModel())
    assert calls == ["typed-decisions"]
    assert provider.status()["status"] == "ready"


def test_invalid_choice_is_rejected():
    provider = LayaLocalProvider(config(), loader=lambda cfg: FakeModel(choice="not-allowed"))
    with pytest.raises(UnsupportedChoice):
        provider.decide(request())


def test_missing_answer_is_rejected():
    class MissingModel:
        def predict(self, state, questions, **kwargs):
            return {"answers": {}}

    provider = LayaLocalProvider(config(), loader=lambda cfg: MissingModel())
    with pytest.raises(InvalidProviderResponse):
        provider.decide(request())


def test_model_load_failure_is_not_reported_as_lazy_ready():
    provider = LayaLocalProvider(config(), loader=lambda cfg: (_ for _ in ()).throw(RuntimeError("weights unavailable")))
    with pytest.raises(ProviderError):
        provider.decide(request())
    assert provider.status()["status"] == "not_ready"
