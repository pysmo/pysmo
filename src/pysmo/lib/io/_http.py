"""Shared HTTP helper for pysmo web-service requests.

[`http_get`][pysmo.lib.io.http_get] wraps `urllib3` with the
retry-on-server-error policy needed by every pysmo caller that fetches
data over HTTP (e.g.
[`SAC.from_earthscope`][pysmo.lib.io.SacIO.from_earthscope] and
[`pysmo.tools.web`][pysmo.tools.web]), so that policy is written once
rather than duplicated at each call site, and gives those call sites a
single, shared seam to patch in tests.
"""

import time
from typing import Any

import urllib3

__all__ = ["http_get"]

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
    """Perform an HTTP GET request with retries on server errors.

    Requests returning HTTP 500 are retried up to `request_retries` times,
    sleeping `retry_delay_seconds` between attempts. Any other HTTP error
    status raises immediately.

    Args:
        url: URL to request.
        fields: Query parameters to send with the request.
        timeout_seconds: Timeout in seconds for each request attempt.
        request_retries: Maximum number of request attempts (must be at least 1).
        retry_delay_seconds: Delay in seconds between request attempts.
        redirect: Whether to automatically follow HTTP redirects.

    Returns:
        The response body.

    Raises:
        ValueError: If `request_retries` is less than 1.
        urllib3.exceptions.ResponseError: If the server returns an HTTP
            error status.
    """
    if request_retries < 1:
        raise ValueError("request_retries must be at least 1.")
    for attempt in range(request_retries):
        response = _pool.request(
            "GET",
            url,
            fields=fields,
            timeout=timeout_seconds,
            redirect=redirect,
        )
        if response.status == 500 and attempt < request_retries - 1:
            time.sleep(retry_delay_seconds)
            continue
        if response.status >= 400:
            raise urllib3.exceptions.ResponseError(f"HTTP {response.status}")
        break
    return response.data
