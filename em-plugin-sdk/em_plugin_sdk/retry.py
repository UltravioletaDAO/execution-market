"""Retry logic with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

# Status codes that trigger automatic retry
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_FACTOR = 0.5  # seconds
DEFAULT_BACKOFF_MAX = 8.0  # max wait between retries


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    backoff_max: float = DEFAULT_BACKOFF_MAX,
    retryable_codes: frozenset[int] = RETRYABLE_STATUS_CODES,
    **kwargs: Any,
) -> httpx.Response:
    """Execute an HTTP request with automatic retry on transient failures."""
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            resp = await client.request(method, url, **kwargs)

            if resp.status_code not in retryable_codes or attempt == max_retries:
                return resp

            # Use Retry-After header if present (for 429s)
            retry_after = resp.headers.get("retry-after")
            if retry_after:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = _backoff_delay(attempt, backoff_factor, backoff_max)
            else:
                wait = _backoff_delay(attempt, backoff_factor, backoff_max)

            await asyncio.sleep(wait)

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            last_exc = exc
            if attempt == max_retries:
                raise
            await asyncio.sleep(_backoff_delay(attempt, backoff_factor, backoff_max))

    # Should not reach here, but satisfy type checker
    if last_exc:
        raise last_exc
    raise RuntimeError("Retry loop exited unexpectedly")  # pragma: no cover


def _backoff_delay(attempt: int, factor: float, maximum: float) -> float:
    """Calculate delay with exponential backoff + jitter."""
    delay = factor * (2 ** attempt)
    delay = min(delay, maximum)
    # Add ±25% jitter
    jitter = delay * 0.25 * (2 * random.random() - 1)
    return max(0, delay + jitter)
