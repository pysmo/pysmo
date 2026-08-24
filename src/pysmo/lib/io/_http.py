"""Shared HTTP helper for pysmo web-service requests."""

import random
import time
from typing import Any

import urllib3

__all__ = [
    "http_get",
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_REQUEST_RETRIES",
    "DEFAULT_RETRY_DELAY_SECONDS",
]

#: Default timeout/retry values for web-service calls built on `http_get`.
#: Defined here, the lowest-level module, so any caller of `http_get` can
#: reuse sensible defaults without duplicating literal values.
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_REQUEST_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 20

#: HTTP statuses considered transient and worth retrying.
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

#: Upper bound on the exponential backoff delay, in seconds.
_MAX_BACKOFF_SECONDS = 120

_pool = urllib3.PoolManager()


def _sleep_with_backoff(base_delay_seconds: int | float, attempt: int) -> None:
    delay = min(base_delay_seconds * (2**attempt), _MAX_BACKOFF_SECONDS)
    time.sleep(random.uniform(0, delay))


def http_get(
    url: str,
    fields: dict[str, Any],
    *,
    timeout_seconds: int | float,
    request_retries: int,
    retry_delay_seconds: int | float,
    redirect: bool = True,
) -> bytes:
    """Perform an HTTP GET request, retrying transient failures.

    Connection failures, timeouts, and responses with a transient status
    (429, 500, 502, 503, or 504) are retried up to `request_retries` times,
    with exponential backoff and jitter between attempts using
    `retry_delay_seconds` as the base delay. Any other HTTP error status
    raises immediately.

    Args:
        url: URL to request.
        fields: Query parameters to send with the request.
        timeout_seconds: Timeout in seconds for each request attempt.
        request_retries: Maximum number of request attempts (must be at least 1).
        retry_delay_seconds: Base delay in seconds between retries.
        redirect: Whether to automatically follow HTTP redirects.

    Returns:
        The response body.

    Raises:
        ValueError: If `request_retries` is less than 1.
        urllib3.exceptions.HTTPError: If a connection or timeout failure
            persists after all retries.
        urllib3.exceptions.ResponseError: If the server returns a
            non-retryable HTTP error status, or a transient one that
            persists after all retries.
    """
    if request_retries < 1:
        raise ValueError("request_retries must be at least 1.")

    attempt = 0
    while True:
        last_attempt = attempt >= request_retries - 1
        try:
            response = _pool.request(
                "GET",
                url,
                fields=fields,
                timeout=timeout_seconds,
                redirect=redirect,
            )
        except urllib3.exceptions.HTTPError:
            if last_attempt:
                raise
            _sleep_with_backoff(retry_delay_seconds, attempt)
            attempt += 1
            continue

        if response.status in _RETRYABLE_STATUSES and not last_attempt:
            _sleep_with_backoff(retry_delay_seconds, attempt)
            attempt += 1
            continue
        if response.status >= 400:
            raise urllib3.exceptions.ResponseError(f"HTTP {response.status}")
        return response.data
