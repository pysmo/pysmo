"""Shared HTTP helper for pysmo web-service requests."""

from typing import Any

import urllib3
from urllib3.util.retry import Retry

__all__ = [
    "DEFAULT_REQUEST_RETRIES",
    "DEFAULT_RETRY_DELAY_SECONDS",
    "DEFAULT_TIMEOUT_SECONDS",
    "http_get",
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
    (429, 500, 502, 503, or 504) are retried up to `request_retries` times.
    The first retry is immediate; retry `n` thereafter waits
    `retry_delay_seconds * 2 ** (n - 1)` seconds plus a random jitter of up
    to `retry_delay_seconds`, capped at 120 seconds total. A `Retry-After`
    header on a 429 or 503 response replaces that wait, clamped to 6 hours.
    Any other HTTP error status raises immediately.

    Args:
        url: URL to request.
        fields: Query parameters to send with the request.
        timeout_seconds: Timeout in seconds for each request attempt.
        request_retries: Maximum number of request attempts (must be at least 1).
        retry_delay_seconds: Base delay for the backoff schedule, and the
            width of the random jitter added to each wait.
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

    # raise_on_status=False: hand the exhausted response back so the status
    # check below raises a consistent ResponseError for any error status.
    retries = Retry(
        total=request_retries - 1,
        status_forcelist=_RETRYABLE_STATUSES,
        backoff_factor=retry_delay_seconds,
        backoff_max=_MAX_BACKOFF_SECONDS,
        backoff_jitter=retry_delay_seconds,
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    response = _pool.request(
        "GET",
        url,
        fields=fields,
        timeout=timeout_seconds,
        redirect=redirect,
        retries=retries,
    )
    if response.status >= 400:
        raise urllib3.exceptions.ResponseError(f"HTTP {response.status}")
    return response.data
