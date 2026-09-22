from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import DecisionRequest, ProviderDecision


class DecisionProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def decide(self, request: DecisionRequest) -> ProviderDecision:
        raise NotImplementedError

    def rank(self, request: DecisionRequest, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def health(self) -> bool:
        return True

    def list_models(self) -> list[dict[str, Any]]:
        return []
