"""Tests for pysmo.classes.MSeed and pysmo.lib.io.write_mseed."""

from pathlib import Path

import numpy as np
import numpy.testing as npt
import pandas as pd
import pymseed
import pytest

from pysmo import (
    MiniSeismogram,
    MiniStation,
    MiniStationCode,
    Seismogram,
    Station,
    StationCode,
)
from pysmo.classes import MSeed
from pysmo.lib.io import write_mseed

GAP_FIXTURE = Path(__file__).parent / "assets" / "mseed_gap.mseed"


def make_mseed_bytes(
    *,
    sourceid: str = "FDSN:IU_ANMO_00_B_H_Z",
    start: str = "2010-02-27T06:30:00Z",
    sample_rate_hz: float = 20.0,
    data: np.ndarray | None = None,
    sample_type: str = "i",
    encoding: pymseed.DataEncoding | None = None,
) -> bytes:
    """Build a single-segment miniSEED body for fast unit tests."""
    if data is None:
        data = np.arange(100, dtype=np.int32)
    tracelist = pymseed.MS3TraceList()
    tracelist.add_data(
        sourceid=sourceid,
        data_samples=data,
        sample_type=sample_type,
        sample_rate=sample_rate_hz,
        starttime=pd.Timestamp(start).value,
        publication_version=1,
    )
    return b"".join(
        tracelist.generate(encoding=encoding or pymseed.DataEncoding.STEIM2)
    )


class TestRead:
    def test_from_bytes(self) -> None:
        seismogram = MSeed.from_bytes(make_mseed_bytes())
        assert isinstance(seismogram, Seismogram)
        assert isinstance(seismogram, StationCode)
        assert not isinstance(seismogram, Station)
        assert seismogram.begin_time == pd.Timestamp("2010-02-27T06:30:00Z")
        assert seismogram.delta == pd.Timedelta(seconds=0.05)
        assert seismogram.sample_count == 100
        assert seismogram.publication_version == 1
        npt.assert_array_equal(seismogram.data, np.arange(100.0))

    def test_sourceid_and_nslc(self) -> None:
        seismogram = MSeed.from_bytes(make_mseed_bytes())
        assert seismogram.sourceid == "FDSN:IU_ANMO_00_B_H_Z"
        assert seismogram.network == "IU"
        assert seismogram.name == "ANMO"
        assert seismogram.location == "00"
        assert seismogram.channel == "BHZ"

    def test_data_is_float64_from_integer_encoding(self) -> None:
        seismogram = MSeed.from_bytes(make_mseed_bytes())
        assert seismogram.data.dtype == np.float64

    def test_end_time_from_mixin(self) -> None:
        seismogram = MSeed.from_bytes(make_mseed_bytes())
        assert seismogram.end_time == seismogram.begin_time + seismogram.delta * 99

    def test_from_file(self, reference_event_assets: dict[str, Path]) -> None:
        seismogram = MSeed.from_file(reference_event_assets["mseed_bhz"])
        assert seismogram.sourceid == "FDSN:IU_ANMO_00_B_H_Z"
        assert seismogram.data.dtype == np.float64
        assert seismogram.sample_count == 57465

    def test_from_file_equals_all_from_file(
        self, reference_event_assets: dict[str, Path]
    ) -> None:
        path = reference_event_assets["mseed_bhz"]
        assert MSeed.from_file(path) == MSeed.all_from_file(path)[0]

    def test_from_bytes_equals_from_file(
        self, reference_event_assets: dict[str, Path]
    ) -> None:
        path = reference_event_assets["mseed_bhz"]
        assert MSeed.from_bytes(path.read_bytes()) == MSeed.from_file(path)

    def test_malformed_bytes_raise(self) -> None:
        with pytest.raises(pymseed.MiniSEEDError):
            MSeed.from_bytes(b"\x00" * 128)


class TestGaps:
    def test_all_from_file_yields_two(self) -> None:
        segments = MSeed.all_from_file(GAP_FIXTURE)
        assert len(segments) == 2
        assert {s.sourceid for s in segments} == {"FDSN:IU_ANMO_00_B_H_Z"}

    def test_from_file_raises_pointing_at_all_from_file(self) -> None:
        with pytest.raises(ValueError, match="all_from_file"):
            MSeed.from_file(GAP_FIXTURE)

    def test_all_from_file_time_order_within_channel(self) -> None:
        first, second = MSeed.all_from_file(GAP_FIXTURE)
        assert first.begin_time < second.begin_time

    def test_from_bytes_raises_on_no_data(self) -> None:
        with pytest.raises(ValueError, match="No miniSEED data"):
            MSeed.from_bytes(b"")

    def test_all_from_bytes_groups_by_source_identifier(self) -> None:
        parts = [
            make_mseed_bytes(sourceid="FDSN:IU_ANMO_00_B_H_Z", start=start)
            for start in ("2010-01-01T01:00:00Z", "2010-01-01T00:00:00Z")
        ]
        parts.append(make_mseed_bytes(sourceid="FDSN:IU_ANMO_00_B_H_N"))
        segments = MSeed.all_from_bytes(b"".join(parts))
        assert [s.sourceid for s in segments] == [
            "FDSN:IU_ANMO_00_B_H_N",
            "FDSN:IU_ANMO_00_B_H_Z",
            "FDSN:IU_ANMO_00_B_H_Z",
        ]
        z_segments = [s for s in segments if s.channel == "BHZ"]
        assert z_segments[0].begin_time < z_segments[1].begin_time


class TestFetch:
    @pytest.fixture()
    def station(self) -> MiniStation:
        return MiniStation(
            name="ANMO",
            network="IU",
            location="00",
            channel="BHZ",
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
            return make_mseed_bytes()

        monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

        seismogram = MSeed.fetch(
            station=station,
            starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
            endtime=pd.Timestamp("2010-02-27T06:30:05Z"),
        )

        assert isinstance(seismogram, Seismogram)
        assert seismogram.sourceid == "FDSN:IU_ANMO_00_B_H_Z"

        _, fields = calls[0]
        assert fields["net"] == "IU"
        assert fields["sta"] == "ANMO"
        assert fields["loc"] == "00"
        assert fields["cha"] == "BHZ"
        assert fields["format"] == "miniseed"

    def test_no_data_raises(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr("pysmo.tools.web.http_get", lambda *args, **kwargs: b"")
        with pytest.raises(ValueError, match="No waveform data returned"):
            MSeed.fetch(
                station=station,
                starttime=pd.Timestamp("2010-02-27T06:30:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:30:05Z"),
            )

    def test_gappy_response_raises(
        self, monkeypatch: pytest.MonkeyPatch, station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: GAP_FIXTURE.read_bytes(),
        )
        with pytest.raises(ValueError, match="contiguous segments"):
            MSeed.fetch(
                station=station,
                starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:46:00Z"),
            )


class TestWrite:
    def test_round_trip_single(
        self, tmp_path: Path, reference_event_assets: dict[str, Path]
    ) -> None:
        seismogram = MSeed.from_file(reference_event_assets["mseed_bhz"])
        path = tmp_path / "out.mseed"
        seismogram.write(path)
        recovered = MSeed.from_file(path)
        assert recovered.begin_time == seismogram.begin_time
        assert recovered.delta == seismogram.delta
        npt.assert_array_equal(recovered.data, seismogram.data)
        assert (
            recovered.network,
            recovered.name,
            recovered.location,
            recovered.channel,
        ) == (
            seismogram.network,
            seismogram.name,
            seismogram.location,
            seismogram.channel,
        )

    def test_round_trip_float64_lossless(self, tmp_path: Path) -> None:
        identity = MiniStationCode(
            name="ANMO", network="IU", location="00", channel="BHZ"
        )
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=0.05),
            data=np.array([1.5, -2.25, 3.125, 4.0]),
        )
        path = tmp_path / "out.mseed"
        write_mseed([(identity, seismogram)], path)
        recovered = MSeed.from_file(path)
        npt.assert_allclose(recovered.data, seismogram.data, rtol=0, atol=0)

    def test_write_to_existing_path(self, tmp_path: Path) -> None:
        identity = MiniStationCode(
            name="ANMO", network="IU", location="00", channel="BHZ"
        )
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=0.05),
            data=np.arange(10.0),
        )
        path = tmp_path / "out.mseed"
        path.write_bytes(b"stale")
        write_mseed([(identity, seismogram)], path)
        assert MSeed.from_file(path).sample_count == 10

    def test_round_trip_multi_segment_gap(self, tmp_path: Path) -> None:
        identity = MiniStationCode(
            name="ANMO", network="IU", location="00", channel="BHZ"
        )
        first = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=0.05),
            data=np.arange(100.0),
        )
        second = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:31:00Z"),
            delta=pd.Timedelta(seconds=0.05),
            data=np.arange(100.0, 200.0),
        )
        path = tmp_path / "out.mseed"
        write_mseed([(identity, first), (identity, second)], path)
        segments = MSeed.all_from_file(path)
        assert len(segments) == 2
        assert {s.sourceid for s in segments} == {"FDSN:IU_ANMO_00_B_H_Z"}

    def test_empty_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="empty sequence"):
            write_mseed([], tmp_path / "out.mseed")

    def test_explicit_sample_type_mismatch_warns(self, tmp_path: Path) -> None:
        identity = MiniStationCode(
            name="ANMO", network="IU", location="00", channel="BHZ"
        )
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=0.05),
            data=np.array([1.5, 2.5, 3.5]),
        )
        with pytest.warns(UserWarning, match="lose precision"):
            write_mseed(
                [(identity, seismogram)], tmp_path / "out.mseed", sample_type="i"
            )

    def test_unsupported_dtype_raises(self, tmp_path: Path) -> None:
        identity = MiniStationCode(
            name="ANMO", network="IU", location="00", channel="BHZ"
        )
        seismogram = MiniSeismogram(
            begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
            delta=pd.Timedelta(seconds=0.05),
            data=np.array([1, 2, 3], dtype=np.int16),
        )
        with pytest.raises(TypeError, match="int16"):
            write_mseed([(identity, seismogram)], tmp_path / "out.mseed")

    def test_write_preserves_nslc_identity(self, tmp_path: Path) -> None:
        seismogram = MSeed.from_bytes(make_mseed_bytes())
        path = tmp_path / "out.mseed"
        seismogram.write(path)
        recovered = MSeed.from_file(path)
        assert (
            recovered.network,
            recovered.name,
            recovered.location,
            recovered.channel,
        ) == ("IU", "ANMO", "00", "BHZ")
