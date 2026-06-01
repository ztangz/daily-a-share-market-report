from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import CN_HEADERS


class FetchError(RuntimeError):
    """Raised when a market data endpoint cannot be fetched after retries."""


def fetch_json(url: str, params: dict[str, Any], retries: int = 3, timeout: int = 15) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    target = f"{url}?{query}"
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(target, headers=CN_HEADERS)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
            return json.loads(body)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.2 * attempt)

    raise FetchError(f"Failed to fetch {url}: {last_error}")

