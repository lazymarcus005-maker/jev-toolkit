from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .core import JevCore
from .interfaces import invoke


TOOLS = [
    {"name": "jev_decide", "description": "Select one bounded choice.", "inputSchema": {"type": "object"}},
    {"name": "jev_rank", "description": "Rank bounded candidates by relevance.", "inputSchema": {"type": "object"}},
    {"name": "jev_evaluate", "description": "Classify state into bounded choices.", "inputSchema": {"type": "object"}},
    {"name": "jev_enough", "description": "Evaluate whether evidence is sufficient.", "inputSchema": {"type": "object"}},
    {"name": "jev_health", "description": "Return Jev health and readiness.", "inputSchema": {"type": "object"}},
]


def _result(request_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(value, separators=(",", ":"))}]}}


def handle_message(core: JevCore, message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "jev", "version": "0.1.0"}}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params", {})
        name = params.get("name", "")
        operation = name.removeprefix("jev_")
        try:
            value = invoke(core, operation, params.get("arguments", {}))
            return _result(request_id, value)
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}


def run_stdio(core: JevCore, input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> None:
    for line in input_stream:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_message(core, message)
            if response is not None:
                output_stream.write(json.dumps(response, separators=(",", ":")) + "\n")
                output_stream.flush()
        except json.JSONDecodeError:
            output_stream.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}) + "\n")
            output_stream.flush()
