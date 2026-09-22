from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..models import DecisionRequest, ProviderDecision, RankResult


class DecisionProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def decide(self, request: DecisionRequest) -> ProviderDecision:
        raise NotImplementedError

    def rank(self, request: DecisionRequest, items: list[dict[str, Any]]) -> RankResult:
        """Fallback ranking contract for providers that only expose choice selection."""
        if not items:
            return RankResult([])
        choices = tuple(str(item.get("id", index)) for index, item in enumerate(items))
        result = self.decide(DecisionRequest(request.decision, request.goal, {"state": request.state, "items": items}, choices, request.criteria, request.metadata))
        selected = result.choice
        ranking = [{"id": item_id, "score": 1.0 if item_id == selected else 0.0} for item_id in choices]
        ranking.sort(key=lambda item: item["score"], reverse=True)
        return RankResult(ranking, self.name)

    def health(self) -> bool:
        return True

    def list_models(self) -> list[dict[str, Any]]:
        return []
