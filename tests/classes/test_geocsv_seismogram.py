"""Tests for pysmo.classes.GeoCsvSeismogram."""

from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from pysmo import MiniStation, Seismogram
from pysmo.classes import GeoCsvSeismogram

FIXTURE = (
    Path(__file__).parent.parent
    / "lib"
    / "io"
    / "assets"
    / "dataselect_response.geocsv"
)

TEXT = """\
# dataset: GeoCSV 2.0
# delimiter: ,
# field_unit: UTC, Counts
# field_type: datetime, INTEGER
# SID: IU_ANMO_00_LHZ
# sample_count: 3
# sample_rate_hz: 2.0
# start_time: 2010-02-27T06:30:00Z
Time, Sample
2010-02-27T06:30:00.0Z, 1
2010-02-27T06:30:00.5Z, 2
2010-02-27T06:30:01.0Z, 3
"""


class TestGeoCsvSeismogram:
    def test_from_text(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        assert isinstance(seismogram, Seismogram)
        assert seismogram.begin_time == pd.Timestamp("2010-02-27T06:30:00Z")
        assert seismogram.delta == pd.Timedelta(seconds=0.5)
        npt.assert_allclose(seismogram.data, [1.0, 2.0, 3.0])
        assert seismogram.sourceid == "IU_ANMO_00_LHZ"
        assert seismogram.sample_count == 3

    def test_end_time(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        assert seismogram.end_time == pd.Timestamp("2010-02-27T06:30:01Z")

    def test_from_text_multi_dataset(self) -> None:
        continuation = TEXT.replace(
            "start_time: 2010-02-27T06:30:00Z", "start_time: 2010-02-27T06:30:01.5Z"
        )
        seismogram = GeoCsvSeismogram.from_text(TEXT + continuation)
        assert seismogram.sample_count == 6
        assert len(seismogram.data) == 6

    def test_from_text_empty(self) -> None:
        with pytest.raises(ValueError, match="No GeoCSV datasets"):
            GeoCsvSeismogram.from_text("")

    def test_from_real_response(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(FIXTURE.read_text())
        assert seismogram.sourceid == "IU_ANMO_00_LHZ"
        assert seismogram.delta == pd.Timedelta(seconds=1)
        assert seismogram.sample_count == 60

    def test_sample_count_tracks_data(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        assert seismogram.sample_count == 3
        seismogram.data = np.array([1.0, 2.0])
        assert seismogram.sample_count == 2

    def test_setattr_converters(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        seismogram.begin_time = "2011-01-01T00:00:00"  # type: ignore[assignment]
        assert seismogram.begin_time == pd.Timestamp("2011-01-01T00:00:00Z")
        seismogram.data = [4.0, 5.0]  # type: ignore[assignment]
        assert isinstance(seismogram.data, np.ndarray)

    def test_invalid_delta(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        with pytest.raises(ValueError):
            seismogram.delta = pd.Timedelta(seconds=-1)

    def test_invalid_sourceid(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        with pytest.raises(TypeError):
            seismogram.sourceid = 42  # type: ignore[assignment]

    def test_rejects_unknown_attributes(self) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        with pytest.raises(AttributeError):
            seismogram.t0 = 60  # type: ignore[attr-defined]


class TestFetch:
    @pytest.fixture()
    def station(self) -> MiniStation:
        return MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="LHZ",
            latitude=34.945981,
            longitude=-106.457133,
        )

    def test_fetches_and_parses(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_http_get(
            url: str, fields: dict[str, object], **kwargs: object
        ) -> bytes:
            calls.append((url, fields))
            return TEXT.encode("utf-8")

        monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

        seismogram = GeoCsvSeismogram.fetch(
            station=station,
            starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
            endtime=pd.Timestamp("2010-02-27T06:30:01Z"),
        )

        assert isinstance(seismogram, Seismogram)
        assert seismogram.sourceid == "IU_ANMO_00_LHZ"
        npt.assert_allclose(seismogram.data, [1.0, 2.0, 3.0])

        _, fields = calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "LHZ"
        assert fields["format"] == "geocsv"
        assert fields["starttime"] == "2010-02-27T06:30:00+00:00"
        assert fields["endtime"] == "2010-02-27T06:30:01+00:00"

    def test_no_data_raises(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr("pysmo.tools.web.http_get", lambda *args, **kwargs: b"\n")

        with pytest.raises(ValueError, match="No waveform data returned"):
            GeoCsvSeismogram.fetch(
                station=station,
                starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:30:03Z"),
            )


class TestWrite:
    def test_round_trip(self, tmp_path: Path) -> None:
        seismogram = GeoCsvSeismogram.from_text(TEXT)
        path = tmp_path / "out.geocsv"
        seismogram.write(path)
        recovered = GeoCsvSeismogram.from_text(path.read_text())
        assert recovered.sourceid == seismogram.sourceid
        assert recovered.begin_time == seismogram.begin_time
        assert recovered.delta == seismogram.delta
        npt.assert_allclose(recovered.data, seismogram.data)
