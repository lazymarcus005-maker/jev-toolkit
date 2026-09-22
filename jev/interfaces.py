from __future__ import annotations

import json
from typing import Any

from .core import JevCore
from .errors import RequestValidationError
from .models import DecisionRequest


def request_from_args(arguments: dict[str, Any], *, operation: str) -> DecisionRequest:
    value = dict(arguments)
    if operation == "enough" and not value.get("choices"):
        value["choices"] = ["sufficient", "insufficient", "contradictory"]
    choices = value.get("choices", [])
    if isinstance(choices, str):
        choices = [part.strip() for part in choices.split(",") if part.strip()]
    value["choices"] = choices
    return DecisionRequest.from_dict(value)


def invoke(core: JevCore, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if operation == "health":
        return {"healthy": True, "ready": core.ready()}
    request = request_from_args(arguments, operation=operation)
    if operation == "rank":
        return core.rank(request, arguments.get("items", [])).to_dict()
    if operation == "enough":
        return core.enough(request).to_dict()
    if operation in {"decide", "evaluate"}:
        return core.decide(request).to_dict()
    raise RequestValidationError(f"unknown operation: {operation}")


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode("utf-8")
