from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .core import JevCore
from .mcp import handle_message


class _McpHandler(BaseHTTPRequestHandler):
    core: JevCore
    server_version = "jev-mcp/0.1"

    def do_POST(self) -> None:
        if self.path not in {"/", "/mcp"}:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            message = json.loads(self.rfile.read(length))
            response = handle_message(self.core, message)
            if response is None:
                self.send_response(202)
                self.end_headers()
                return
            payload = json.dumps(response, separators=(",", ":")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error(400, str(exc))

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_mcp_server(core: JevCore, host: str, port: int) -> ThreadingHTTPServer:
    handler = type("JevMcpHandler", (_McpHandler,), {"core": core})
    return ThreadingHTTPServer((host, port), handler)
