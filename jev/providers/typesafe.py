from __future__ import annotations

from typing import Any

from ..config import ProviderConfig
from ..errors import InvalidProviderResponse, UnsupportedChoice
from ..models import DecisionRequest, ProviderDecision
from .base import DecisionProvider
from .http import request_json


class TypeSafeProvider(DecisionProvider):
    def __init__(self, config: ProviderConfig):
        self.name = config.name
        self.config = config
        self.model = config.model
        self._models: list[dict[str, Any]] | None = None

    def _headers(self) -> dict[str, str]:
        if not self.config.api_key:
            raise InvalidProviderResponse(f"missing API key environment variable: {self.config.api_key_env}")
        return {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}

    def list_models(self) -> list[dict[str, Any]]:
        result = request_json(f"{self.config.base_url}/v1/models", method="GET", headers=self._headers(), timeout_ms=self.config.timeout_ms)
        models = result.get("models") if isinstance(result, dict) else None
        if not isinstance(models, list):
            raise InvalidProviderResponse("TypeSafe models response has no models list")
        self._models = [model for model in models if isinstance(model, dict)]
        return self._models

    def _resolved_model(self) -> str:
        if self.config.model and self.config.model != "auto":
            return self.config.model
        models = self._models if self._models is not None else self.list_models()
        names = [item.get("name") for item in models if item.get("name")]
        if not names:
            raise InvalidProviderResponse("TypeSafe model discovery returned no models")
        return "jev-latest" if "jev-latest" in names else names[0]

    def decide(self, request: DecisionRequest) -> ProviderDecision:
        criteria = {choice: request.criteria.get(choice, choice) for choice in request.choices}
        body = {
            "model": self._resolved_model(),
            "state": {"goal": request.goal, "decision": request.decision, "state": request.state},
            "questions": {
                request.decision: {
                    "type": "choice",
                    "instructions": "Select exactly one allowed choice based on the goal and state.",
                    "criteria": criteria,
                }
            },
        }
        result = request_json(f"{self.config.base_url}/v1/systemone", method="POST", headers=self._headers(), payload=body, timeout_ms=self.config.timeout_ms)
        try:
            answer = result["answers"][request.decision]
            choice = answer["choice"]
            confidence = answer["confidence"]
            model = result.get("model") or body["model"]
        except (KeyError, TypeError) as exc:
            raise InvalidProviderResponse("TypeSafe response does not contain a choice answer") from exc
        if choice not in request.choices:
            raise UnsupportedChoice(f"provider returned unsupported choice: {choice!r}")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise InvalidProviderResponse("provider confidence is not numeric")
        return ProviderDecision(choice=choice, confidence=float(confidence), model=model)

    def health(self) -> bool:
        try:
            self.list_models()
            return True
        except Exception:
            return False
