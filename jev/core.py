from __future__ import annotations

import time
from typing import Callable

from .config import JevConfig
from .errors import InvalidProviderResponse, ProviderError, RequestValidationError
from .models import DecisionRequest, DecisionResult, ProviderDecision
from .routing import build_providers
from .telemetry import Telemetry


def normalize_confidence(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidProviderResponse("confidence must be numeric")
    value = float(value)
    if 0 <= value <= 1:
        return value
    if 1 < value <= 100:
        return value / 100
    raise InvalidProviderResponse("confidence must be between 0 and 1, or a percentage")


class JevCore:
    def __init__(self, config: JevConfig, *, providers: dict[str, object] | None = None, telemetry: Telemetry | None = None):
        problems = config.validate()
        if problems:
            raise RequestValidationError("invalid configuration: " + "; ".join(problems))
        self.config = config
        self.providers = providers or build_providers(config)
        self.telemetry = telemetry or Telemetry(config.telemetry)

    def _fallback(self, request: DecisionRequest, reason: str, started: float) -> DecisionResult:
        result = DecisionResult(
            decision=request.decision,
            choice=None,
            confidence=None,
            provider=None,
            model=None,
            fallback_used=True,
            latency_ms=int((time.monotonic() - started) * 1000),
            fallback_reason=reason,
            agent_fallback=True,
        )
        self._emit(request, result)
        return result

    def _emit(self, request: DecisionRequest, result: DecisionResult) -> None:
        metadata = request.metadata
        self.telemetry.decision(
            decision=result.decision,
            provider=result.provider,
            model=result.model,
            latency_ms=result.latency_ms,
            confidence=result.confidence,
            selected_choice=result.choice,
            candidate_count=len(request.choices),
            fallback_used=result.fallback_used,
            fallback_reason=result.fallback_reason,
            agent_override=result.agent_fallback,
            workflow_id=metadata.get("workflow_id"),
            skill_name=metadata.get("skill"),
            iteration=metadata.get("iteration"),
        )

    def decide(self, request: DecisionRequest) -> DecisionResult:
        request.validate()
        started = time.monotonic()
        provider_names = [self.config.routing.default, *self.config.routing.technical_fallback]
        errors: list[str] = []
        for provider_name in dict.fromkeys(provider_names):
            provider = self.providers.get(provider_name)
            if provider is None:
                errors.append(f"{provider_name}: unavailable")
                continue
            try:
                response: ProviderDecision = provider.decide(request)
                confidence = normalize_confidence(response.confidence)
                threshold = request.accept_threshold if request.accept_threshold is not None else self.config.default_accept_threshold
                if response.choice not in request.choices:
                    raise InvalidProviderResponse("provider returned an unsupported choice")
                if confidence < threshold:
                    return self._fallback(request, f"low_confidence:{confidence:.3f}<{threshold:.3f}", started)
                result = DecisionResult(request.decision, response.choice, confidence, provider_name, response.model, bool(errors), int((time.monotonic() - started) * 1000), ",".join(errors) if errors else None)
                self._emit(request, result)
                return result
            except ProviderError as exc:
                errors.append(f"{provider_name}:{type(exc).__name__}")
                continue
            except Exception as exc:
                errors.append(f"{provider_name}:{type(exc).__name__}")
                continue
        return self._fallback(request, "provider_error:" + ",".join(errors), started)

    def ready(self) -> bool:
        default = self.providers.get(self.config.routing.default)
        return default is not None and bool(default.health())
