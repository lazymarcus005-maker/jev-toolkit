from __future__ import annotations

import json
import logging
from typing import Any

from .config import TelemetryConfig


class Telemetry:
    def __init__(self, config: TelemetryConfig):
        self.config = config
        self.logger = logging.getLogger("jev.telemetry")

    def decision(self, **fields: Any) -> None:
        if not self.config.enabled:
            return
        allowed = {"decision", "provider", "model", "device", "latency_ms", "confidence", "selected_choice", "candidate_count", "fallback_used", "fallback_reason", "agent_override", "workflow_id", "skill_name", "iteration"}
        event = {key: value for key, value in fields.items() if key in allowed}
        if not self.config.log_decisions:
            event.pop("decision", None)
            event.pop("provider", None)
            event.pop("model", None)
            event.pop("selected_choice", None)
        if not self.config.log_latency:
            event.pop("latency_ms", None)
        if not self.config.log_confidence:
            event.pop("confidence", None)
        self.logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
