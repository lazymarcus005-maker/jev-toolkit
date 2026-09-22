from __future__ import annotations

from .config import JevConfig
from .errors import ConfigurationError
from .providers import LayaLocalProvider, OpenAICompatibleProvider, OpenRouterProvider, TypeSafeProvider


def build_providers(config: JevConfig) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, provider_config in config.providers.items():
        if not provider_config.enabled:
            continue
        if provider_config.type == "typesafe":
            result[name] = TypeSafeProvider(provider_config)
        elif provider_config.type == "laya":
            result[name] = LayaLocalProvider(provider_config)
        elif provider_config.type == "openai-compatible":
            result[name] = OpenRouterProvider(provider_config) if name == "openrouter" else OpenAICompatibleProvider(provider_config)
        else:
            raise ConfigurationError(f"unsupported provider type: {provider_config.type}")
    return result
