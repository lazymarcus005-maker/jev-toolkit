from __future__ import annotations

import json
import re
from typing import Any

from ..config import ProviderConfig
from ..errors import InvalidProviderResponse, UnsupportedChoice
from ..models import DecisionRequest, ProviderDecision
from .base import DecisionProvider
from .http import request_json


def _content_json(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise InvalidProviderResponse("chat completion content is not JSON text")
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise InvalidProviderResponse("chat completion content is not valid JSON") from exc
    if not isinstance(value, dict):
        raise InvalidProviderResponse("chat completion JSON must be an object")
    return value


class OpenAICompatibleProvider(DecisionProvider):
    def __init__(self, config: ProviderConfig):
        self.name = config.name
        self.config = config
        self.model = config.model

    def _headers(self) -> dict[str, str]:
        if not self.config.api_key:
            raise InvalidProviderResponse(f"missing API key environment variable: {self.config.api_key_env}")
        return {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}

    def decide(self, request: DecisionRequest) -> ProviderDecision:
        prompt = {
            "decision": request.decision,
            "goal": request.goal,
            "state": request.state,
            "allowed_choices": list(request.choices),
            "criteria": request.criteria,
            "output_schema": {"choice": "one allowed choice", "confidence": "number from 0 to 1"},
        }
        body = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You are a bounded decision classifier. Return JSON only with exactly choice and confidence. Never invent a choice."},
                {"role": "user", "content": json.dumps(prompt, separators=(",", ":"))},
            ],
            "response_format": {"type": "json_object"},
        }
        result = request_json(f"{self.config.base_url}/chat/completions", method="POST", headers=self._headers(), payload=body, timeout_ms=self.config.timeout_ms)
        try:
            content = result["choices"][0]["message"]["content"]
            answer = _content_json(content)
            choice = answer["choice"]
            confidence = answer["confidence"]
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidProviderResponse("chat completion has no decision message") from exc
        if choice not in request.choices:
            raise UnsupportedChoice(f"provider returned unsupported choice: {choice!r}")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise InvalidProviderResponse("provider confidence is not numeric")
        return ProviderDecision(choice=choice, confidence=float(confidence), model=result.get("model") or self.config.model)

    def health(self) -> bool:
        return bool(self.config.base_url and self.config.model and self.config.api_key)


class OpenRouterProvider(OpenAICompatibleProvider):
    """Named adapter for the OpenRouter-compatible endpoint."""
