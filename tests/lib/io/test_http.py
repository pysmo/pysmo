"""Tests for pysmo.lib.io._http."""

from collections.abc import Iterator, Sequence
from typing import Any
from unittest.mock import MagicMock

import pytest
import urllib3

import pysmo.lib.io._http as http_mod


class FakeResponse:
    def __init__(self, status: int, data: bytes = b"body") -> None:
        self.status = status
        self.data = data


class MultiResponse:
    """Returns a sequence of canned responses/exceptions on successive `request` calls."""

    def __init__(self, responses: Sequence[FakeResponse | Exception]) -> None:
        self._iter: Iterator[FakeResponse | Exception] = iter(responses)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        result = next(self._iter)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def patch_pool(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the module-level pool with a `MagicMock` so no test hits the network.

    Tests that need canned responses replace this again via `make_pool`.
    """
    pool = MagicMock()
    monkeypatch.setattr(http_mod, "_pool", pool)
    return pool


def make_pool(
    responses: Sequence[FakeResponse | Exception], monkeypatch: pytest.MonkeyPatch
) -> MultiResponse:
    multi = MultiResponse(responses)
    monkeypatch.setattr(http_mod, "_pool", multi)
    return multi


class TestHttpGet:
    def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pool = make_pool([FakeResponse(200, b"ok")], monkeypatch)
        result = http_mod.http_get(
            "http://example.com",
            {"key": "val"},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        assert result == b"ok"
        assert len(pool.calls) == 1
        method, url, kwargs = pool.calls[0]
        assert method == "GET"
        assert url == "http://example.com"
        assert kwargs["fields"] == {"key": "val"}
        assert kwargs["timeout"] == 5

    def test_4xx_raises_immediately(self, monkeypatch: pytest.MonkeyPatch) -> None:
        make_pool([FakeResponse(404)], monkeypatch)
        with pytest.raises(urllib3.exceptions.ResponseError, match="HTTP 404"):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=3,
                retry_delay_seconds=0,
            )

    def test_500_then_200_retries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pool = make_pool(
            [FakeResponse(500), FakeResponse(200, b"recovered")], monkeypatch
        )
        result = http_mod.http_get(
            "http://example.com",
            {},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        assert result == b"recovered"
        assert len(pool.calls) == 2

    def test_500_exhausts_retries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        pool = make_pool([FakeResponse(500)] * 3, monkeypatch)
        with pytest.raises(urllib3.exceptions.ResponseError, match="HTTP 500"):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=3,
                retry_delay_seconds=0,
            )
        assert len(pool.calls) == 3

    def test_zero_retries_raises(self) -> None:
        with pytest.raises(ValueError, match="request_retries must be at least 1"):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=0,
                retry_delay_seconds=0,
            )

    @pytest.mark.parametrize("status", [429, 502, 503, 504])
    def test_transient_status_then_200_retries(
        self, status: int, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pool = make_pool(
            [FakeResponse(status), FakeResponse(200, b"recovered")], monkeypatch
        )
        result = http_mod.http_get(
            "http://example.com",
            {},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        assert result == b"recovered"
        assert len(pool.calls) == 2

    def test_connection_error_then_200_retries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pool = make_pool(
            [urllib3.exceptions.TimeoutError("timed out"), FakeResponse(200, b"ok")],
            monkeypatch,
        )
        result = http_mod.http_get(
            "http://example.com",
            {},
            timeout_seconds=5,
            request_retries=3,
            retry_delay_seconds=0,
        )
        assert result == b"ok"
        assert len(pool.calls) == 2

    def test_connection_error_exhausts_retries(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        make_pool([urllib3.exceptions.TimeoutError("timed out")] * 3, monkeypatch)
        with pytest.raises(urllib3.exceptions.TimeoutError):
            http_mod.http_get(
                "http://example.com",
                {},
                timeout_seconds=5,
                request_retries=3,
                retry_delay_seconds=0,
            )

    def test_backoff_grows_exponentially_and_is_capped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        make_pool([FakeResponse(500)] * 3 + [FakeResponse(200)], monkeypatch)
        sleeps: list[float] = []
        monkeypatch.setattr(http_mod.time, "sleep", sleeps.append)
        monkeypatch.setattr(http_mod.random, "uniform", lambda low, high: high)

        http_mod.http_get(
            "http://example.com",
            {},
            timeout_seconds=5,
            request_retries=4,
            retry_delay_seconds=10,
        )

        assert sleeps == [10, 20, 40]
