"""Tests for pysmo.tools.web."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pysmo import MiniStation, Response, StagedResponse
from pysmo.classes import SacPZ, StationXML
from pysmo.tools.web import (
    fetch_sac,
    fetch_sacpz,
    fetch_stationxml,
    fetch_travel_times,
)

STATIONXML_SINGLE_EPOCH = (
    Path(__file__).parent.parent
    / "lib"
    / "io"
    / "assets"
    / "stationxml_anmo_single.xml"
).read_bytes()
SACPZ_SINGLE = (
    Path(__file__).parent.parent / "lib" / "io" / "assets" / "sacpz_anmo_single.txt"
).read_text()
SACPZ_BULK = (
    Path(__file__).parent.parent / "lib" / "io" / "assets" / "sacpz_anmo_bulk.txt"
).read_text()
SAC_ZIP_BYTES = b"not a real zip archive -- fetch_sac() does no interpretation"

TRAVELTIME_RESPONSE = json.dumps(
    {
        "arrivals": [
            {"phase": "P", "time": 480.2},
            {"phase": "P", "time": 490.0},
            {"phase": "S", "time": 900.1},
        ]
    }
).encode()


@pytest.fixture()
def station() -> MiniStation:
    return MiniStation(
        name="ANMO",
        network="IU",
        location="00",
        channel="LHZ",
        latitude=34.945981,
        longitude=-106.457133,
    )


class FakeHttpGet:
    """Stand-in for http_get returning canned responses per URL."""

    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, fields: dict[str, Any], **kwargs: Any) -> bytes:
        self.calls.append((url, fields))
        for fragment, response in self.responses.items():
            if fragment in url:
                return response
        raise AssertionError(f"Unexpected URL in test: {url}")


class TestFetchTravelTimes:
    def test_travel_time_backend(self) -> None:
        calls = []

        def backend(
            depth_km: float, dist_deg: float, phases: list[str]
        ) -> dict[str, float]:
            calls.append((depth_km, dist_deg, phases))
            return {"P": 123.4}

        result = fetch_travel_times(22.9, 60.0, ["P"], travel_time_backend=backend)
        assert result == {"P": 123.4}
        assert calls == [(22.9, 60.0, ["P"])]

    def test_web_service(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = FakeHttpGet({"traveltime": TRAVELTIME_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        result = fetch_travel_times(22.9, 60.0, ["P", "S"], model="prem")

        assert result == {"P": 480.2, "S": 900.1}
        (_, fields) = fake.calls[0]
        assert fields["model"] == "prem"
        assert fields["phases"] == "P,S"


class TestFetchStationxml:
    def test_returns_raw_bytes(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"station": STATIONXML_SINGLE_EPOCH})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        xml = fetch_stationxml(station=station)

        assert xml == STATIONXML_SINGLE_EPOCH
        (url, fields) = fake.calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "LHZ"
        assert fields["level"] == "response"

    def test_round_trip_with_stationxml_from_bytes(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"station": STATIONXML_SINGLE_EPOCH})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        xml = fetch_stationxml(station=station)
        response = StationXML.from_bytes(xml, time=pd.Timestamp("2016-01-01T00:00:00Z"))

        assert isinstance(response, Response)
        assert isinstance(response, StagedResponse)
        assert response.input_units == "m/s"
        assert len(response.stages) == 2


class TestFetchSacpz:
    def test_returns_raw_text(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"sacpz": SACPZ_SINGLE.encode("ascii")})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        text = fetch_sacpz(station=station)

        assert text == SACPZ_SINGLE
        (url, fields) = fake.calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "LHZ"
        assert "level" not in fields

    def test_round_trip_with_sacpz_from_text(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"sacpz": SACPZ_SINGLE.encode("ascii")})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        text = fetch_sacpz(station=station)
        response = SacPZ.from_text(text)

        assert isinstance(response, Response)
        assert response.network == "IU"
        assert response.station == "ANMO"

    def test_bulk_fixture_round_trip_with_all_from_text(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"sacpz": SACPZ_BULK.encode("ascii")})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        text = fetch_sacpz(station=station)
        responses = SacPZ.all_from_text(text)

        assert len(responses) == 9

    def test_sub_second_time_truncated_with_warning(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"sacpz": SACPZ_SINGLE.encode("ascii")})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        with pytest.warns(UserWarning, match="sub-second precision"):
            fetch_sacpz(station=station, time=pd.Timestamp("2010-02-27T06:37:51.0936Z"))

        (_, fields) = fake.calls[0]
        assert fields["time"] == "2010-02-27T06:37:51+00:00"

    def test_whole_second_time_not_truncated_no_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        station: MiniStation,
        recwarn: pytest.WarningsRecorder,
    ) -> None:
        fake = FakeHttpGet({"sacpz": SACPZ_SINGLE.encode("ascii")})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        fetch_sacpz(station=station, time=pd.Timestamp("2010-02-27T06:37:51Z"))

        assert len(recwarn) == 0
        (_, fields) = fake.calls[0]
        assert fields["time"] == "2010-02-27T06:37:51+00:00"


class TestFetchSac:
    def test_returns_raw_bytes(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"dataselect": SAC_ZIP_BYTES})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        data = fetch_sac(
            station=station,
            starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
            endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        )

        assert data == SAC_ZIP_BYTES
        (url, fields) = fake.calls[0]
        assert "dataselect" in url
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "LHZ"
        assert fields["format"] == "sac.zip"
        assert fields["starttime"] == "2010-02-27T06:44:00+00:00"
        assert fields["endtime"] == "2010-02-27T06:54:00+00:00"
