"""Tests for pysmo.lib.io._http."""

import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
import urllib3
from urllib3.util.retry import Retry

import pysmo.lib.io._http as http_mod


class FakeResponse:
    def __init__(self, status: int, data: bytes = b"body") -> None:
        self.status = status
        self.data = data


class CapturingPool:
    """Records the arguments of each `request` call and returns a canned response."""

    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        return self.response


@pytest.fixture
def capturing_pool(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[FakeResponse], CapturingPool]:
    def _install(response: FakeResponse) -> CapturingPool:
        pool = CapturingPool(response)
        monkeypatch.setattr(http_mod, "_pool", pool)
        return pool

    return _install


class TestWrapperBehaviour:
    """Behaviour owned by `http_get` itself, independent of urllib3's retrying."""

    def test_success_returns_body(
        self, capturing_pool: Callable[[FakeResponse], CapturingPool]
    ) -> None:
        pool = capturing_pool(FakeResponse(200, b"ok"))
        result = http_mod.http_get(
            "http://example.com",
            {"key": "val"},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        assert result == b"ok"
        method, url, kwargs = pool.calls[0]
        assert method == "GET"
        assert url == "http://example.com"
        assert kwargs["fields"] == {"key": "val"}
        assert kwargs["timeout"] == 5
        assert kwargs["redirect"] is True

    def test_non_retryable_status_raises(
        self, capturing_pool: Callable[[FakeResponse], CapturingPool]
    ) -> None:
        capturing_pool(FakeResponse(404))
        with pytest.raises(urllib3.exceptions.ResponseError, match="HTTP 404"):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=3,
                retry_delay_seconds=0,
            )

    def test_exhausted_retryable_status_raises(
        self, capturing_pool: Callable[[FakeResponse], CapturingPool]
    ) -> None:
        # With raise_on_status=False, urllib3 hands back the final 503 and
        # http_get is responsible for turning it into an error.
        capturing_pool(FakeResponse(503))
        with pytest.raises(urllib3.exceptions.ResponseError, match="HTTP 503"):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=3,
                retry_delay_seconds=0,
            )

    def test_zero_retries_raises(self) -> None:
        with pytest.raises(ValueError, match="request_retries must be at least 1"):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=0,
                retry_delay_seconds=0,
            )

    def test_retry_policy_configuration(
        self, capturing_pool: Callable[[FakeResponse], CapturingPool]
    ) -> None:
        pool = capturing_pool(FakeResponse(200))
        http_mod.http_get(
            "http://example.com",
            {},
            timeout_seconds=5,
            request_retries=4,
            retry_delay_seconds=10,
        )
        retries = pool.calls[0][2]["retries"]
        assert isinstance(retries, Retry)
        assert retries.total == 3
        assert set(retries.status_forcelist or set()) == {429, 500, 502, 503, 504}
        assert retries.backoff_factor == 10
        assert retries.backoff_max == http_mod._MAX_BACKOFF_SECONDS
        assert retries.backoff_jitter == 10
        assert retries.respect_retry_after_header is True
        assert retries.raise_on_status is False


ServerFactory = Callable[
    [list[tuple[int, dict[str, str], bytes]]], tuple[str, "list[str]"]
]


@pytest.fixture
def http_server() -> Iterator[ServerFactory]:
    """Start throwaway localhost HTTP servers that replay a fixed response sequence.

    Returns a factory taking a list of ``(status, headers, body)`` tuples; the
    last entry is repeated once the sequence is exhausted. The factory yields
    the base URL and a list that accumulates the paths the server received.
    """
    started: list[ThreadingHTTPServer] = []

    def _start(
        responses: list[tuple[int, dict[str, str], bytes]],
    ) -> tuple[str, list[str]]:
        received: list[str] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                index = min(len(received), len(responses) - 1)
                received.append(self.path)
                status, headers, body = responses[index]
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: Any) -> None:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        started.append(server)
        return f"http://127.0.0.1:{server.server_address[1]}", received

    yield _start

    for server in started:
        server.shutdown()


class TestRetryIntegration:
    """End-to-end checks that the Retry policy is actually wired into the request."""

    def test_transient_status_then_success(self, http_server: ServerFactory) -> None:
        url, received = http_server(
            [
                (503, {"Retry-After": "0"}, b""),
                (200, {}, b"recovered"),
            ]
        )
        result = http_mod.http_get(
            url,
            {},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        assert result == b"recovered"
        assert len(received) == 2

    def test_transient_status_exhausts_retries(
        self, http_server: ServerFactory
    ) -> None:
        url, received = http_server([(503, {}, b"")])
        with pytest.raises(urllib3.exceptions.ResponseError, match="HTTP 503"):
            http_mod.http_get(
                url,
                {},
                timeout_seconds=5,
                request_retries=2,
                retry_delay_seconds=0,
            )
        assert len(received) == 2

    def test_retry_after_header_is_respected(self, http_server: ServerFactory) -> None:
        url, _ = http_server(
            [
                (503, {"Retry-After": "1"}, b""),
                (200, {}, b"ok"),
            ]
        )
        start = time.monotonic()
        result = http_mod.http_get(
            url,
            {},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        elapsed = time.monotonic() - start
        assert result == b"ok"
        assert elapsed >= 1.0

    def test_connection_failure_raises_httperror(self) -> None:
        # Port 1 is reserved and never listening, so the connection fails fast.
        with pytest.raises(urllib3.exceptions.HTTPError):
            http_mod.http_get(
                "http://127.0.0.1:1",
                {},
                timeout_seconds=1,
                request_retries=1,
                retry_delay_seconds=0,
            )
