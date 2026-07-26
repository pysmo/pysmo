"""Tests for pysmo.tools.web."""

import json
from typing import Any

import numpy.testing as npt
import pandas as pd
import pytest

from pysmo import MiniEvent, MiniStation
from pysmo.classes import GeoCsvSeismogram
from pysmo.tools.web import fetch_seismogram, fetch_travel_times

WAVEFORM_RESPONSE = b"""\
# dataset: GeoCSV 2.0
# delimiter: ,
# field_unit: UTC, Counts
# field_type: datetime, INTEGER
# SID: IU_ANMO_00_LHZ
# sample_count: 3
# sample_rate_hz: 1.0
# start_time: 2010-02-27T06:30:00Z
Time, Sample
2010-02-27T06:30:00Z, 1
2010-02-27T06:30:01Z, 2
2010-02-27T06:30:02Z, 3
"""

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


@pytest.fixture()
def event() -> MiniEvent:
    return MiniEvent(
        latitude=-36.122,
        longitude=-72.898,
        depth=22900.0,
        time=pd.Timestamp("2010-02-27T06:34:11.53Z"),
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


class TestFetchSeismogram:
    def test_absolute_window(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"dataselect": WAVEFORM_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        seismogram, arrivals = fetch_seismogram(
            station=station,
            starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
            endtime=pd.Timestamp("2010-02-27T06:30:03Z"),
        )

        assert isinstance(seismogram, GeoCsvSeismogram)
        assert seismogram.begin_time == pd.Timestamp("2010-02-27T06:30:00Z")
        assert seismogram.sid == "IU_ANMO_00_LHZ"
        npt.assert_allclose(seismogram.data, [1.0, 2.0, 3.0])
        assert arrivals == {}

        (url, fields) = fake.calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "LHZ"
        assert fields["format"] == "geocsv"

    def test_absolute_window_with_event(
        self,
        monkeypatch: pytest.MonkeyPatch,
        station: MiniStation,
        event: MiniEvent,
    ) -> None:
        fake = FakeHttpGet({"dataselect": WAVEFORM_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        _, arrivals = fetch_seismogram(
            station=station,
            event=event,
            starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
            endtime=pd.Timestamp("2010-02-27T06:30:03Z"),
            phases=["P", "S"],
            travel_time_backend=lambda depth, dist, phases: {"P": 100.0, "S": 200.0},
        )

        assert arrivals == {
            "P": event.time + pd.Timedelta(seconds=100),
            "S": event.time + pd.Timedelta(seconds=200),
        }

    def test_absolute_window_with_event_arrivals_unavailable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        station: MiniStation,
        event: MiniEvent,
    ) -> None:
        """A failure computing predicted arrivals must not lose the seismogram."""
        fake = FakeHttpGet({"dataselect": WAVEFORM_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        def broken_backend(
            depth: float, dist: float, phases: list[str]
        ) -> dict[str, float]:
            raise RuntimeError("travel-time service unavailable")

        with pytest.warns(UserWarning, match="Could not compute predicted arrivals"):
            seismogram, arrivals = fetch_seismogram(
                station=station,
                event=event,
                starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:30:03Z"),
                travel_time_backend=broken_backend,
            )

        assert isinstance(seismogram, GeoCsvSeismogram)
        assert arrivals == {}

    def test_relative_window(
        self,
        monkeypatch: pytest.MonkeyPatch,
        station: MiniStation,
        event: MiniEvent,
    ) -> None:
        fake = FakeHttpGet({"dataselect": WAVEFORM_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        _, arrivals = fetch_seismogram(
            station=station,
            event=event,
            pre=pd.Timedelta(seconds=60),
            post=pd.Timedelta(seconds=120),
            travel_time_backend=lambda depth, dist, phases: {"P": 100.0},
        )

        predicted = event.time + pd.Timedelta(seconds=100)
        assert arrivals == {"P": predicted}
        (_, fields) = fake.calls[0]
        assert fields["starttime"] == (predicted - pd.Timedelta(seconds=60)).isoformat()
        assert fields["endtime"] == (predicted + pd.Timedelta(seconds=120)).isoformat()

    def test_relative_window_no_arrivals(
        self,
        monkeypatch: pytest.MonkeyPatch,
        station: MiniStation,
        event: MiniEvent,
    ) -> None:
        fake = FakeHttpGet({"dataselect": WAVEFORM_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        with pytest.raises(ValueError, match="No arrivals found"):
            fetch_seismogram(
                station=station,
                event=event,
                pre=pd.Timedelta(seconds=60),
                post=pd.Timedelta(seconds=120),
                travel_time_backend=lambda depth, dist, phases: {},
            )

    def test_relative_window_phase_not_in_travel_times(
        self,
        monkeypatch: pytest.MonkeyPatch,
        station: MiniStation,
        event: MiniEvent,
    ) -> None:
        fake = FakeHttpGet({"dataselect": WAVEFORM_RESPONSE})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        with pytest.raises(ValueError, match="None of the requested phases"):
            fetch_seismogram(
                station=station,
                event=event,
                pre=pd.Timedelta(seconds=60),
                post=pd.Timedelta(seconds=120),
                phases=["P"],
                travel_time_backend=lambda depth, dist, phases: {"S": 100.0},
            )

    def test_no_data(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        fake = FakeHttpGet({"dataselect": b"\n"})
        monkeypatch.setattr("pysmo.tools.web.http_get", fake)

        with pytest.raises(ValueError, match="No waveform data returned"):
            fetch_seismogram(
                station=station,
                starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:30:03Z"),
            )

    @pytest.mark.parametrize(
        "kwargs,match",
        [
            ({}, "not both or neither"),
            (
                {
                    "starttime": pd.Timestamp("2010-02-27T06:30:00Z"),
                    "endtime": pd.Timestamp("2010-02-27T06:30:03Z"),
                    "pre": pd.Timedelta(seconds=60),
                    "post": pd.Timedelta(seconds=120),
                },
                "not both or neither",
            ),
            (
                {"starttime": pd.Timestamp("2010-02-27T06:30:00Z")},
                "both starttime and endtime",
            ),
            ({"pre": pd.Timedelta(seconds=60)}, "both pre and post"),
        ],
    )
    def test_inconsistent_windows(
        self, station: MiniStation, kwargs: dict[str, Any], match: str
    ) -> None:
        with pytest.raises(ValueError, match=match):
            fetch_seismogram(station=station, **kwargs)

    def test_relative_window_requires_event(self, station: MiniStation) -> None:
        with pytest.raises(ValueError, match="event is required"):
            fetch_seismogram(
                station=station,
                pre=pd.Timedelta(seconds=60),
                post=pd.Timedelta(seconds=120),
            )


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
