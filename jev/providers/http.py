from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any

from ..errors import InvalidProviderResponse, ProviderError, ProviderTimeout


def request_json(url: str, *, method: str, headers: dict[str, str], payload: Any = None, timeout_ms: int) -> Any:
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_ms / 1000) as response:
            raw = response.read()
    except (TimeoutError, socket.timeout) as exc:
        raise ProviderTimeout(f"provider timed out: {url}") from exc
    except urllib.error.HTTPError as exc:
        if exc.code >= 500:
            raise ProviderError(f"provider server error: HTTP {exc.code}") from exc
        raise ProviderError(f"provider request rejected: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError("provider unavailable") from exc
    try:
        return json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProviderResponse("provider did not return JSON") from exc
