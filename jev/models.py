from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import RequestValidationError


@dataclass(frozen=True)
class DecisionRequest:
    decision: str
    goal: str
    state: Any = field(default_factory=dict)
    choices: tuple[str, ...] = ()
    criteria: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    accept_threshold: float | None = None

    def validate(self) -> None:
        if not isinstance(self.decision, str) or not self.decision.strip():
            raise RequestValidationError("decision must be a non-empty string")
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise RequestValidationError("goal must be a non-empty string")
        if not isinstance(self.choices, tuple) or not self.choices:
            raise RequestValidationError("at least one choice is required")
        if any(not isinstance(choice, str) or not choice.strip() for choice in self.choices):
            raise RequestValidationError("choices must be non-empty strings")
        if len(set(self.choices)) != len(self.choices):
            raise RequestValidationError("choices must be unique")
        if not isinstance(self.criteria, dict):
            raise RequestValidationError("criteria must be an object")
        if self.accept_threshold is not None and not 0 <= self.accept_threshold <= 1:
            raise RequestValidationError("accept_threshold must be between 0 and 1")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DecisionRequest":
        if not isinstance(value, dict):
            raise RequestValidationError("request must be an object")
        choices = value.get("choices", ())
        if isinstance(choices, list):
            choices = tuple(choices)
        return cls(
            decision=value.get("decision", ""),
            goal=value.get("goal", ""),
            state=value.get("state", {}),
            choices=choices,
            criteria=value.get("criteria", {}),
            metadata=value.get("metadata", {}),
            accept_threshold=value.get("accept_threshold"),
        )


@dataclass(frozen=True)
class ProviderDecision:
    choice: str
    confidence: float
    model: str | None = None


@dataclass(frozen=True)
class DecisionResult:
    decision: str
    choice: str | None
    confidence: float | None
    provider: str | None
    model: str | None
    fallback_used: bool
    latency_ms: int
    fallback_reason: str | None = None
    agent_fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "choice": self.choice,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "fallback_used": self.fallback_used,
            "latency_ms": self.latency_ms,
            "fallback_reason": self.fallback_reason,
            "agent_fallback": self.agent_fallback,
        }


@dataclass(frozen=True)
class RankResult:
    ranking: list[dict[str, Any]]
    provider: str | None = None
    fallback_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"ranking": self.ranking, "provider": self.provider, "fallback_used": self.fallback_used}
