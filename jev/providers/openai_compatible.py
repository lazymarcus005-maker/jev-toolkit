from __future__ import annotations

import json
import re
from typing import Any

from ..config import ProviderConfig
from ..errors import InvalidProviderResponse, UnsupportedChoice
from ..models import DecisionRequest, ProviderDecision, RankResult
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

    def rank(self, request: DecisionRequest, items: list[dict[str, Any]]) -> RankResult:
        body = {
            "model": self.config.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You are a bounded ranking classifier. Return JSON only with ranking, an array containing every requested id exactly once and a score from 0 to 1."},
                {"role": "user", "content": json.dumps({"goal": request.goal, "state": request.state, "items": items}, separators=(",", ":"))},
            ],
            "response_format": {"type": "json_object"},
        }
        result = request_json(f"{self.config.base_url}/chat/completions", method="POST", headers=self._headers(), payload=body, timeout_ms=self.config.timeout_ms)
        try:
            answer = _content_json(result["choices"][0]["message"]["content"])
            ranking = answer["ranking"]
        except (KeyError, IndexError, TypeError) as exc:
            raise InvalidProviderResponse("chat completion has no ranking") from exc
        if not isinstance(ranking, list):
            raise InvalidProviderResponse("ranking must be an array")
        expected = {str(item["id"]) for item in items}
        actual = {str(item.get("id")) for item in ranking if isinstance(item, dict)}
        if actual != expected or len(actual) != len(ranking):
            raise InvalidProviderResponse("ranking must contain each requested id exactly once")
        normalized = []
        for item in ranking:
            score = item.get("score")
            if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= float(score) <= 1:
                raise InvalidProviderResponse("ranking scores must be between 0 and 1")
            normalized.append({"id": str(item["id"]), "score": float(score)})
        return RankResult(normalized, result.get("model") or self.config.model)

    def health(self) -> bool:
        if not (self.config.base_url and self.config.model and self.config.api_key):
            return False
        # A models-list ping still succeeds on gateways that reject inference
        # (auth, funding, model access), so probe a minimal completion instead.
        body = {"model": self.config.model, "max_tokens": 1, "messages": [{"role": "user", "content": "ping"}]}
        try:
            request_json(f"{self.config.base_url}/chat/completions", method="POST", headers=self._headers(), payload=body, timeout_ms=self.config.timeout_ms)
            return True
        except Exception:
            return False


class OpenRouterProvider(OpenAICompatibleProvider):
    """Named adapter for the OpenRouter-compatible endpoint."""
