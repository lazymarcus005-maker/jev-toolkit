from pathlib import Path

from jev.config import load_config


def test_example_config_loads_without_embedded_secrets():
    config = load_config(Path(__file__).parents[1] / "config" / "jev.example.yaml")
    assert config.routing.default == "typesafe"
    assert config.providers["typesafe"].api_key_env == "TYPESAFE_API_KEY"
    assert config.telemetry.log_raw_state is False
