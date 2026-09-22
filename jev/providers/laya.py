from __future__ import annotations

import importlib.util
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Any, Callable

from ..config import ProviderConfig
from ..errors import InvalidProviderResponse, ProviderError, ProviderTimeout, UnsupportedChoice
from ..models import DecisionRequest, ProviderDecision
from .base import DecisionProvider


LayaLoader = Callable[[ProviderConfig], Any]


class LayaLocalProvider(DecisionProvider):
    """CPU-only adapter for Laya's typed-question decision API."""

    REPOSITORY = "convaiinnovations/laya"

    def __init__(self, config: ProviderConfig, *, loader: LayaLoader | None = None):
        self.name = config.name
        self.config = config
        self.model = config.model
        self._loader = loader or self._load_from_laya
        self._injected_loader = loader is not None
        self._load_lock = threading.Lock()
        self._model: Any | None = None
        self._load_error: str | None = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="jev-laya")
        self._configure_cache()
        if config.preload:
            try:
                self._ensure_loaded()
            except ProviderError:
                # Readiness exposes the diagnostic; construction must not prevent
                # technical fallback from keeping the service available.
                pass

    def _configure_cache(self) -> None:
        if self.config.cache_dir:
            os.environ.setdefault("HF_HOME", self.config.cache_dir)

    def _load_from_laya(self, config: ProviderConfig) -> Any:
        try:
            import laya
        except ImportError as exc:
            raise ProviderError("Laya is not installed; install jev-agent-toolkit[laya]") from exc
        self._configure_cache()
        if config.model == "router":
            return laya.Router(device="cpu", max_loaded=config.max_loaded_models, preload=config.preload)
        subfolder = config.model if config.model in {"typed-decisions", "multilingual"} else None
        return laya.load(self.REPOSITORY, device="cpu", subfolder=subfolder)

    def _ensure_loaded(self) -> Any:
        if self._model is not None:
            return self._model
        with self._load_lock:
            if self._model is not None:
                return self._model
            try:
                self._model = self._loader(self.config)
                self._load_error = None
            except ProviderError as exc:
                self._load_error = str(exc)
                raise
            except Exception as exc:
                self._load_error = str(exc) or type(exc).__name__
                raise ProviderError(f"Laya model load failed: {self._load_error}") from exc
            return self._model

    def _questions(self, request: DecisionRequest) -> dict[str, dict[str, Any]]:
        return {
            request.decision: {
                "type": "choice",
                "instructions": "Select exactly one allowed choice based on the goal and compact state.",
                "criteria": {choice: request.criteria.get(choice, choice) for choice in request.choices},
            }
        }

    def _predict(self, model: Any, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        if self.config.model == "router":
            return model.predict(state, questions)
        return model.predict(state, questions)

    def decide(self, request: DecisionRequest) -> ProviderDecision:
        model = self._ensure_loaded()
        state = {"goal": request.goal, "decision": request.decision, "state": request.state}
        questions = self._questions(request)
        future = self._executor.submit(self._predict, model, state, questions)
        try:
            response = future.result(timeout=self.config.timeout_ms / 1000)
        except FutureTimeout as exc:
            future.cancel()
            raise ProviderTimeout("Laya inference timed out") from exc
        except Exception as exc:
            raise ProviderError(f"Laya inference failed: {exc}") from exc
        try:
            answer = response["answers"][request.decision]
            choice = answer["choice"]
            confidence = answer["confidence"]
        except (KeyError, TypeError) as exc:
            raise InvalidProviderResponse("Laya response does not contain a choice answer") from exc
        if choice not in request.choices:
            raise UnsupportedChoice(f"provider returned unsupported choice: {choice!r}")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise InvalidProviderResponse("Laya confidence is not numeric")
        routing = response.get("routing", {}) if isinstance(response, dict) else {}
        model_name = routing.get("model") if isinstance(routing, dict) else None
        return ProviderDecision(choice=choice, confidence=float(confidence), model=model_name or self.config.model)

    def list_models(self) -> list[dict[str, Any]]:
        return [{"name": self.config.model, "device": self.config.device, "loaded": self._model is not None}]

    def status(self) -> dict[str, Any]:
        if self._model is not None:
            state = "ready"
        elif self._load_error:
            state = "not_ready"
        elif self._injected_loader or importlib.util.find_spec("laya") is not None:
            state = "lazy"
        else:
            state = "not_ready"
        result = {"status": state, "model": self.config.model, "device": self.config.device}
        if self._load_error:
            result["error"] = self._load_error
        return result

    def health(self) -> bool:
        return self.status()["status"] in {"ready", "lazy"}

    def diagnostics(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            self._ensure_loaded()
            return {
                "status": "ok",
                "model": self.config.model,
                "device": self.config.device,
                "latency_ms": int((time.perf_counter() - started) * 1000),
            }
        except ProviderError as exc:
            return {
                "status": "error",
                "model": self.config.model,
                "device": self.config.device,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "error": str(exc),
            }

    def telemetry_context(self) -> dict[str, Any]:
        return {"device": self.config.device}
