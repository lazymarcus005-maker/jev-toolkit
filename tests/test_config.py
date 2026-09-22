from pathlib import Path

from jev.config import load_config
from jev.config import JevConfig, ProviderConfig, RoutingConfig


def test_example_config_loads_without_embedded_secrets():
    config = load_config(Path(__file__).parents[1] / "config" / "jev.example.yaml")
    assert config.routing.default == "typesafe"
    assert config.providers["typesafe"].api_key_env == "TYPESAFE_API_KEY"
    assert config.telemetry.log_raw_state is False


def test_laya_configuration_supports_cpu_and_environment_overrides(tmp_path, monkeypatch):
    path = tmp_path / "jev.yaml"
    path.write_text("""
providers:
  laya:
    type: laya
    enabled: true
    model: typed-decisions
    device: cpu
    preload: false
    max_loaded_models: 2
    cache_dir: /models
routing:
  default: laya
""")
    monkeypatch.setenv("LAYA_MODEL", "multilingual")
    monkeypatch.setenv("LAYA_PRELOAD", "true")
    config = load_config(path)
    assert config.validate() == []
    assert config.providers["laya"].model == "multilingual"
    assert config.providers["laya"].preload is True
    assert config.providers["laya"].device == "cpu"


def test_laya_gpu_device_is_rejected():
    config = JevConfig(
        {"laya": ProviderConfig("laya", "laya", model="typed-decisions", device="cuda")},
        RoutingConfig("laya"),
    )
    assert any("only device: cpu" in problem for problem in config.validate())
