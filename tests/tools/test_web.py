"""Tests for pysmo.tools.web."""

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import pytest

from pysmo import MiniStation, Response, StagedResponse
from pysmo.classes import QuakeML, SacPZ, StationXML
from pysmo.tools.web import (
    fetch_quakeml,
    fetch_sac,
    fetch_sacpz,
    fetch_station_inventory,
    fetch_stationxml,
)

QUAKEML_BYTES = b"<q:quakeml/> -- fetch_quakeml() does no interpretation"
STATIONS_XML_BYTES = (
    b"<FDSNStationXML/> -- fetch_station_inventory() does no interpretation"
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
        epoch = StationXML.from_bytes(xml, time=pd.Timestamp("2016-01-01T00:00:00Z"))
        response = epoch.response

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


class TestFetchQuakeml:
    def test_returns_raw_bytes_and_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeHttpGet({"event": QUAKEML_BYTES})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        data = fetch_quakeml()

        assert data == QUAKEML_BYTES
        (url, fields) = fake.calls[0]
        parsed_url = urlparse(url)
        assert parsed_url.hostname == "earthquake.usgs.gov"
        assert "event" in parsed_url.path
        assert fields == {"format": "xml", "nodata": "404"}

    def test_parameter_assembly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = FakeHttpGet({"event": QUAKEML_BYTES})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        fetch_quakeml(
            starttime=pd.Timestamp("2010-02-01T00:00:00Z"),
            minmagnitude=7.0,
            mindepth_km=10.0,
            orderby="magnitude",
            eventtype="earthquake,explosion",
        )

        (_, fields) = fake.calls[0]
        assert fields["starttime"] == "2010-02-01T00:00:00+00:00"
        assert fields["minmagnitude"] == 7.0
        assert fields["mindepth"] == 10.0  # sent to FDSN under its own name
        assert fields["orderby"] == "magnitude"
        assert fields["eventtype"] == "earthquake,explosion"
        assert "endtime" not in fields
        assert "maxmagnitude" not in fields

    def test_round_trip_with_quakeml_all_from_bytes(
        self, monkeypatch: pytest.MonkeyPatch, reference_event_assets: dict
    ) -> None:
        quakeml = reference_event_assets["quakeml"].read_bytes()
        fake = FakeHttpGet({"event": quakeml})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        events = QuakeML.all_from_query(minmagnitude=8.0)

        assert len(events) == 1
        assert events[0].magnitude == 8.8


class TestFetchStations:
    def test_returns_raw_bytes_and_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeHttpGet({"station": STATIONS_XML_BYTES})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        data = fetch_station_inventory(network="IU,II", channel="BH?")

        assert data == STATIONS_XML_BYTES
        (url, fields) = fake.calls[0]
        assert "station" in url
        assert fields["net"] == "IU,II"
        assert fields["cha"] == "BH?"
        assert fields["sta"] == "*"
        assert fields["loc"] == "*"
        assert fields["format"] == "xml"
        assert fields["nodata"] == "404"
        assert fields["level"] == "channel"

    def test_optional_params_and_booleans(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        fake = FakeHttpGet({"station": STATIONS_XML_BYTES})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        fetch_station_inventory(
            network="IU",
            channel="BHZ",
            starttime=pd.Timestamp("2010-01-01T00:00:00Z"),
            includerestricted=False,
            matchtimeseries=True,
        )

        (_, fields) = fake.calls[0]
        assert fields["starttime"] == "2010-01-01T00:00:00+00:00"
        assert fields["includerestricted"] == "false"
        assert fields["matchtimeseries"] == "true"
        assert "endtime" not in fields
