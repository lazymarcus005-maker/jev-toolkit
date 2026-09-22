from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    type: str
    enabled: bool = True
    base_url: str = ""
    api_key_env: str | None = None
    model: str = ""
    timeout_ms: int = 5000
    device: str = "cpu"
    preload: bool = False
    max_loaded_models: int = 1
    cache_dir: str | None = None

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None


@dataclass(frozen=True)
class RoutingConfig:
    default: str
    technical_fallback: tuple[str, ...] = ()


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool = True
    log_decisions: bool = True
    log_latency: bool = True
    log_confidence: bool = True
    log_raw_state: bool = False


@dataclass(frozen=True)
class ServerConfig:
    http_enabled: bool = True
    http_host: str = "127.0.0.1"
    http_port: int = 8080
    mcp_stdio: bool = True
    mcp_http_enabled: bool = True
    mcp_http_host: str = "127.0.0.1"
    mcp_http_port: int = 8081


@dataclass(frozen=True)
class JevConfig:
    providers: dict[str, ProviderConfig]
    routing: RoutingConfig
    default_accept_threshold: float = 0.70
    server: ServerConfig = field(default_factory=ServerConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)

    def validate(self, require_credentials: bool = False) -> list[str]:
        problems: list[str] = []
        if not self.providers:
            problems.append("at least one provider must be configured")
        if self.routing.default not in self.providers:
            problems.append(f"routing.default provider is unknown: {self.routing.default}")
        for name in (self.routing.default, *self.routing.technical_fallback):
            provider = self.providers.get(name)
            if provider is None:
                problems.append(f"routing provider is unknown: {name}")
            elif name == self.routing.default and not provider.enabled:
                problems.append(f"default provider is disabled: {name}")
        if not 0 <= self.default_accept_threshold <= 1:
            problems.append("decision_policy.default_accept_threshold must be between 0 and 1")
        for provider in self.providers.values():
            if provider.enabled and provider.type != "laya" and not provider.base_url:
                problems.append(f"enabled provider has no base_url: {provider.name}")
            if provider.enabled and provider.type not in {"typesafe", "openai-compatible", "laya"}:
                problems.append(f"unsupported provider type: {provider.type}")
            if provider.type == "laya":
                if provider.device != "cpu":
                    problems.append("laya supports only device: cpu in V1")
                if provider.model not in {"typed-decisions", "multilingual", "router"}:
                    problems.append(f"unsupported laya model: {provider.model}")
                if provider.max_loaded_models < 1:
                    problems.append("laya max_loaded_models must be at least 1")
            if provider.timeout_ms <= 0:
                problems.append(f"provider timeout_ms must be positive: {provider.name}")
            if require_credentials and provider.enabled and provider.api_key_env and not provider.api_key:
                problems.append(f"missing environment variable: {provider.api_key_env}")
        return problems


def _as_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _env_or(value: Any, env_name: str, default: Any = None) -> Any:
    return os.environ.get(env_name, value if value is not None else default)


def load_config(path: str | Path) -> JevConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text()) or {}
    except FileNotFoundError as exc:
        raise ConfigurationError(f"config file not found: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError("configuration root must be an object")

    server = raw.get("server", {}) or {}
    http = server.get("http", {}) or {}
    mcp = server.get("mcp", {}) or {}
    streamable = mcp.get("streamable_http", {}) or {}
    providers: dict[str, ProviderConfig] = {}
    for name, value in (raw.get("providers", {}) or {}).items():
        if not isinstance(value, dict):
            raise ConfigurationError(f"provider config must be an object: {name}")
        is_laya = value.get("type") == "laya"
        providers[name] = ProviderConfig(
            name=name,
            type=value.get("type", ""),
            enabled=_as_bool(value.get("enabled"), True),
            base_url=str(value.get("base_url", "")).rstrip("/"),
            api_key_env=value.get("api_key_env"),
            model=str(_env_or(value.get("model"), "LAYA_MODEL", "typed-decisions") if is_laya else value.get("model", "")),
            timeout_ms=int(value.get("timeout_ms", 5000)),
            device=str(_env_or(value.get("device"), "LAYA_DEVICE", "cpu") if is_laya else value.get("device", "cpu")),
            preload=_as_bool(_env_or(value.get("preload"), "LAYA_PRELOAD", False) if is_laya else value.get("preload"), False),
            max_loaded_models=int(_env_or(value.get("max_loaded_models"), "LAYA_MAX_LOADED_MODELS", 1) if is_laya else value.get("max_loaded_models", 1)),
            cache_dir=_env_or(value.get("cache_dir"), "LAYA_CACHE_DIR") if is_laya else value.get("cache_dir"),
        )
    routing_raw = raw.get("routing", {}) or {}
    fallback_raw = routing_raw.get("fallback", {}) or {}
    fallback = fallback_raw.get("technical_error", ()) if isinstance(fallback_raw, dict) else fallback_raw
    if isinstance(fallback, str):
        fallback = (fallback,)
    policy = raw.get("decision_policy", {}) or {}
    telemetry = raw.get("telemetry", {}) or {}
    return JevConfig(
        providers=providers,
        routing=RoutingConfig(
            default=str(routing_raw.get("default", "")),
            technical_fallback=tuple(fallback or ()),
        ),
        default_accept_threshold=float(policy.get("default_accept_threshold", 0.70)),
        server=ServerConfig(
            http_enabled=_as_bool(http.get("enabled"), True),
            http_host=str(http.get("host", "127.0.0.1")),
            http_port=int(http.get("port", 8080)),
            mcp_stdio=_as_bool(mcp.get("stdio"), True),
            mcp_http_enabled=_as_bool(streamable.get("enabled"), True),
            mcp_http_host=str(streamable.get("host", "127.0.0.1")),
            mcp_http_port=int(streamable.get("port", 8081)),
        ),
        telemetry=TelemetryConfig(
            enabled=_as_bool(telemetry.get("enabled"), True),
            log_decisions=_as_bool(telemetry.get("log_decisions"), True),
            log_latency=_as_bool(telemetry.get("log_latency"), True),
            log_confidence=_as_bool(telemetry.get("log_confidence"), True),
            log_raw_state=_as_bool(telemetry.get("log_raw_state"), False),
        ),
    )
