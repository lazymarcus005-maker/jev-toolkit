from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .core import JevCore
from .errors import JevError
from .interfaces import invoke


class _Handler(BaseHTTPRequestHandler):
    core: JevCore
    server_version = "jev/0.1"

    def _send(self, status: int, value: Any) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        elif self.path == "/ready":
            ready = self.core.ready()
            self._send(200 if ready else 503, {"status": "ready" if ready else "not_ready"})
        elif self.path == "/v1/providers":
            self._send(200, {"providers": sorted(self.core.providers)})
        elif self.path == "/v1/models":
            models = []
            for provider in self.core.providers.values():
                try:
                    models.extend(provider.list_models())
                except Exception:
                    continue
            self._send(200, {"models": models})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(length))
            operation = {"/v1/decide": "decide", "/v1/rank": "rank", "/v1/evaluate": "evaluate", "/v1/enough": "enough"}.get(self.path)
            if operation is None:
                self._send(404, {"error": "not_found"})
                return
            self._send(200, invoke(self.core, operation, body))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            self._send(400, {"error": "invalid_request", "message": str(exc)})
        except JevError as exc:
            self._send(400, {"error": "request_error", "message": str(exc)})
        except Exception as exc:
            self._send(500, {"error": "internal_error", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        return


def create_server(core: JevCore, host: str, port: int) -> ThreadingHTTPServer:
    handler = type("JevHandler", (_Handler,), {"core": core})
    return ThreadingHTTPServer((host, port), handler)


def serve_in_thread(core: JevCore, host: str, port: int) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = create_server(core, host, port)
    thread = threading.Thread(target=server.serve_forever, name="jev-http", daemon=True)
    thread.start()
    return server, thread
