import json
import logging

from jev.cli import build_parser
from jev.config import JevConfig, ProviderConfig, RoutingConfig, TelemetryConfig
from jev.core import JevCore
from jev.models import DecisionRequest, ProviderDecision
from jev.providers.laya import LayaLocalProvider


class Model:
    def predict(self, state, questions, **kwargs):
        return {"answers": {"check": {"choice": "yes", "confidence": 0.91}}}


def laya_core():
    config = JevConfig(
        {"laya": ProviderConfig("laya", "laya", model="typed-decisions", preload=True)},
        RoutingConfig("laya"),
        telemetry=TelemetryConfig(enabled=True),
    )
    provider = LayaLocalProvider(config.providers["laya"], loader=lambda _: Model())
    return JevCore(config, providers={"laya": provider})


def test_readiness_reports_laya_model_and_cpu():
    ready, providers = laya_core().readiness()
    assert ready is True
    assert providers["laya"] == {"status": "ready", "model": "typed-decisions", "device": "cpu"}


def test_laya_device_is_present_in_structured_telemetry(caplog):
    caplog.set_level(logging.INFO, logger="jev.telemetry")
    laya_core().decide(DecisionRequest("check", "check", {}, ("yes", "no")))
    assert '"device":"cpu"' in caplog.text


def test_cli_supports_laya_diagnostics_and_benchmark_commands():
    args = build_parser().parse_args(["providers", "test", "laya"])
    assert args.provider_command == "test"
    assert args.provider_name == "laya"
    args = build_parser().parse_args(["providers", "list"])
    assert args.provider_command == "list"
    args = build_parser().parse_args(["benchmark", "laya", "--runs", "4", "--warmup", "1"])
    assert args.command == "benchmark"
    assert args.runs == 4
    assert args.warmup == 1
