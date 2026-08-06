from datetime import timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import numpy.testing as npt
import pandas as pd
import pytest

from pysmo import Event, MiniStation, Seismogram, Station
from pysmo.classes import SAC
from pysmo.lib.defaults import SeismogramDefaults
from pysmo.lib.io import SacIO
from pysmo.lib.io._sacio import SAC_OPTIONAL_TIME_HEADERS


def _zip_of(entries: dict[str, bytes]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


class TestSAC:
    def test_create_instance(self) -> None:
        sac = SAC()
        assert isinstance(sac, SAC)
        assert isinstance(sac.seismogram, Seismogram)

        # coordinates for event and station are None.
        with pytest.raises(TypeError):
            assert isinstance(sac.station, Station)
            sac.station.latitude
        with pytest.raises(TypeError):
            assert isinstance(sac.event, Event)
            sac.event.latitude

    @pytest.mark.depends(on=["test_create_instance"])
    def test_defaults(self) -> None:
        sac = SAC()

        with pytest.warns(RuntimeWarning) as record:
            assert sac.seismogram.begin_time == SeismogramDefaults.begin_time
        assert (
            str(record[0].message)
            == "SAC object has no reference time (kzdate/kztime), assuming 1970-01-01T00:00:00+00:00"
        )
        assert sac.seismogram.delta == SeismogramDefaults.delta
        npt.assert_allclose(sac.seismogram.data, np.array([]))

        with pytest.raises(TypeError):
            sac.event.latitude
        with pytest.raises(TypeError):
            sac.event.longitude
        with pytest.raises(TypeError):
            sac.event.time

    @pytest.mark.depends(on=["test_create_instance"])
    def test_create_instance_from_file(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        assert isinstance(sac, SAC)
        assert isinstance(sac.seismogram, Seismogram)
        assert isinstance(sac.station, Station)
        assert isinstance(sac.event, Event)

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_seismogram(self, sacfile: Path) -> None:
        sacseis = SAC.from_file(sacfile).seismogram
        sacio = SacIO.from_file(sacfile)
        assert isinstance(sacseis, Seismogram)
        assert isinstance(sacseis.data, np.ndarray)
        assert sacseis.data.all() == sacio.data.all()
        assert list(sacseis.data[:5]) == [
            -47201.0,
            -47361.0,
            -47511.0,
            -47666.0,
            -47826.0,
        ]
        assert (
            sacseis.delta.total_seconds()
            == pytest.approx(sacio.delta, 0.001)
            == pytest.approx(0.05, 0.001)
        )
        assert sacseis.begin_time.timestamp() == pytest.approx(
            pd.Timestamp(2010, 2, 27, 6, 44, 6, 69538, tzinfo=timezone.utc).timestamp()
        )
        assert sacseis.begin_time.year == sacio.nzyear
        if sacio.nzjday:
            assert sacseis.begin_time.timetuple().tm_yday == sacio.nzjday + int(
                sacio.b / 3600
            )
        if sacio.nzmin:
            assert sacseis.begin_time.minute == (sacio.nzmin + int(sacio.b / 60)) % 60
        if sacio.nzsec:
            assert sacseis.begin_time.second == (sacio.nzsec + int(sacio.b)) % 60
        if sacio.nzmsec:
            # abs=1000: the formula truncates b's sub-millisecond part via
            # int(...*1000), so it can be off from the true microsecond
            # value by up to a full millisecond.
            assert sacseis.begin_time.microsecond == pytest.approx(
                1000 * (sacio.nzmsec + int(sacio.b * 1000)) % 1000000, abs=1000
            )
        assert sacseis.end_time.timestamp() == pytest.approx(
            pd.Timestamp(
                2010, 2, 27, 7, 31, 59, 269538, tzinfo=timezone.utc
            ).timestamp()
        )
        assert (sacseis.end_time - sacseis.begin_time).total_seconds() == pytest.approx(
            sacio.delta * (sacio.npts - 1)
        )

        # Change some values
        random_data = np.random.randn(100)
        new_time1 = pd.Timestamp.fromisoformat("2011-11-04T00:05:23.123").replace(
            tzinfo=timezone.utc
        )
        sacseis.data = random_data
        # changing data should also change end time
        assert sacseis.data.all() == random_data.all()
        assert sacseis.end_time - sacseis.begin_time == sacseis.delta * (
            len(sacseis.data) - 1
        )
        # changing delta also changes end time
        new_delta = sacseis.delta * 2
        sacseis.delta = new_delta
        assert sacseis.delta.total_seconds() == pytest.approx(new_delta.total_seconds())
        assert sacseis.end_time - sacseis.begin_time == sacseis.delta * (
            len(sacseis.data) - 1
        )
        # changing the begin time changes end time
        sacseis.begin_time = new_time1
        assert sacseis.begin_time == new_time1
        assert sacseis.end_time - sacseis.begin_time == sacseis.delta * (
            len(sacseis.data) - 1
        )

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_as_station(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        sacstation = sac.station
        sacio = SacIO.from_file(sacfile)
        assert sacstation.name == sacio.kstnm
        assert sacstation.network == sacio.knetwk
        assert sacstation.latitude == sacio.stla == pytest.approx(34.945980072021484)
        assert sacstation.longitude == sacio.stlo == pytest.approx(-106.4571304321289)
        assert sacstation.elevation == sacio.stel == pytest.approx(1671.0)

        # try changing values
        new_name = "new_name"
        new_network = "network"
        new_latitude = 23.3
        bad_latitude = 9199
        new_longitude = -123
        bad_longitude = 500
        new_elevation = 123
        sacstation.name = new_name
        sacstation.network = new_network
        sacstation.latitude = new_latitude
        sacstation.longitude = new_longitude
        sacstation.elevation = new_elevation
        assert sacstation.name == new_name == sac.kstnm
        assert sacstation.network == new_network == sac.knetwk
        assert sacstation.latitude == new_latitude == sac.stla
        assert sacstation.longitude == new_longitude == sac.stlo
        assert sacstation.elevation == new_elevation == sac.stel
        with pytest.raises(ValueError):
            sacstation.latitude = bad_latitude
        with pytest.raises(ValueError):
            sacstation.longitude = bad_longitude

        # This is also true for getting None back from attributes.
        # They may be None in sacio, but not in sac.station
        sac.kstnm = None
        with pytest.raises(TypeError):
            sacstation.name
        sac.stla = None
        with pytest.raises(TypeError):
            sacstation.latitude
        sac.stlo = None
        with pytest.raises(TypeError):
            sacstation.longitude
        sac.knetwk = None
        with pytest.raises(TypeError):
            sacstation.network
        sac.khole = None
        with pytest.raises(TypeError):
            sacstation.location
        sac.kcmpnm = None
        with pytest.raises(TypeError):
            sacstation.channel

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_as_event(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        sacevent = sac.event
        sacio = SacIO.from_file(sacfile)
        assert sacevent.latitude == sacio.evla == pytest.approx(-36.12200164794922)
        assert sacevent.longitude == sacio.evlo == pytest.approx(-72.89800262451172)
        if sacio.evdp is not None:
            assert sacevent.depth == sacio.evdp * 1000 == pytest.approx(22900)
        if sac.o is not None:
            assert sacevent.time == sac.seismogram.begin_time + pd.Timedelta(
                seconds=sac.o - sac.b
            )
        newtime = sacevent.time + pd.Timedelta(seconds=30)
        if sac.iztype == "o":
            with pytest.raises(RuntimeError):
                sacevent.time = newtime
        else:
            sacevent.time = newtime
            assert sacevent.time.timestamp() == pytest.approx(newtime.timestamp())
        sacevent.latitude, sacevent.longitude, sacevent.depth = 32, 100, 5000
        assert sacevent.latitude == 32 == sac.evla
        assert sacevent.longitude == 100 == sac.evlo
        if sac.evdp:
            assert sacevent.depth == 5000 == sac.evdp * 1000
        with pytest.raises(ValueError):
            sacevent.latitude = 100
        with pytest.raises(ValueError):
            sacevent.latitude = -100
        with pytest.raises(ValueError):
            sacevent.longitude = 500
        with pytest.raises(ValueError):
            sacevent.longitude = -500
        #
        #
        sac.evdp = None
        with pytest.raises(TypeError):
            sacevent.depth

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_timestamps(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        sacio = SacIO.from_file(sacfile)
        assert sac.timestamps.e is not None
        assert sac.timestamps.b is not None
        assert (sac.timestamps.e - sac.timestamps.b).total_seconds() == pytest.approx(
            sacio.e - sacio.b, 0.000001
        )
        now = pd.Timestamp.now(timezone.utc)
        with pytest.raises(AttributeError):
            sac.timestamps.e = now
        assert sac.timestamps.t0 is None
        sac.timestamps.t0 = now
        assert sac.timestamps.t0 is not None
        sac.timestamps.t0 = None
        assert sac.timestamps.t0 is None
        sac.timestamps.b = now
        assert sac.timestamps.b.timestamp() == pytest.approx(now.timestamp())
        with pytest.raises(TypeError):
            sac.timestamps.b = None  # type: ignore
        # Naive timestamp should be converted to UTC automatically now
        naive_now = pd.Timestamp.now()
        sac.timestamps.b = naive_now
        assert sac.timestamps.b.tzinfo == timezone.utc

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_set_sac_from_timestamp_optional_none(self, sacfile: Path) -> None:
        sac = SAC.from_file(sacfile)
        sac.event._set_sac_from_timestamp(SAC_OPTIONAL_TIME_HEADERS.o, None)
        assert getattr(sac.event._parent, SAC_OPTIONAL_TIME_HEADERS.o) is None


class TestFetch:
    def test_fetches_and_parses_single_member(
        self,
        monkeypatch: pytest.MonkeyPatch,
        assets: dict[str, Path],
        mini_station: MiniStation,
    ) -> None:
        sac_bytes = assets["orgfile"].read_bytes()
        calls: list[tuple[str, dict[str, object]]] = []

        def fake_http_get(
            url: str, fields: dict[str, object], **kwargs: object
        ) -> bytes:
            calls.append((url, fields))
            return _zip_of({"IU.ANMO.00.BHZ.SAC": sac_bytes})

        monkeypatch.setattr("pysmo.tools.web.http_get", fake_http_get)

        sac = SAC.fetch(
            station=mini_station,
            starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
            endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
        )

        assert isinstance(sac, SAC)
        assert sac.station.network == mini_station.network
        assert sac.station.name == mini_station.name

        _, fields = calls[0]
        assert fields["net"] == mini_station.network
        assert fields["sta"] == mini_station.name
        assert fields["loc"] == mini_station.location
        assert fields["cha"] == mini_station.channel
        assert fields["format"] == "sac.zip"
        assert fields["starttime"] == "2010-02-27T06:44:00+00:00"
        assert fields["endtime"] == "2010-02-27T06:54:00+00:00"

    def test_empty_response_raises(
        self, monkeypatch: pytest.MonkeyPatch, mini_station: MiniStation
    ) -> None:
        """dataselect returns an empty body (HTTP 204) for a well-formed
        request that matches no data -- not a zero-member zip archive.
        Confirmed against the live service."""
        monkeypatch.setattr("pysmo.tools.web.http_get", lambda *args, **kwargs: b"")

        with pytest.raises(ValueError, match="No waveform data returned"):
            SAC.fetch(
                station=mini_station,
                starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            )

    def test_no_members_raises(
        self, monkeypatch: pytest.MonkeyPatch, mini_station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get", lambda *args, **kwargs: _zip_of({})
        )

        with pytest.raises(ValueError, match="contains no SAC segments"):
            SAC.fetch(
                station=mini_station,
                starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            )

    def test_non_zip_response_raises(
        self, monkeypatch: pytest.MonkeyPatch, mini_station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get", lambda *args, **kwargs: b"not a zip archive"
        )

        with pytest.raises(ValueError, match="Not a valid zip archive"):
            SAC.fetch(
                station=mini_station,
                starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            )

    def test_corrupt_member_raises(
        self, monkeypatch: pytest.MonkeyPatch, mini_station: MiniStation
    ) -> None:
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: _zip_of({"segment.SAC": b"too short"}),
        )

        with pytest.raises(ValueError, match="Could not parse segment"):
            SAC.fetch(
                station=mini_station,
                starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            )

    def test_multiple_members_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
        assets: dict[str, Path],
        mini_station: MiniStation,
    ) -> None:
        sac_bytes = assets["orgfile"].read_bytes()
        monkeypatch.setattr(
            "pysmo.tools.web.http_get",
            lambda *args, **kwargs: _zip_of(
                {"segment_1.SAC": sac_bytes, "segment_2.SAC": sac_bytes}
            ),
        )

        with pytest.raises(ValueError, match="2 segments"):
            SAC.fetch(
                station=mini_station,
                starttime=pd.Timestamp("2010-02-27T06:44:00Z"),
                endtime=pd.Timestamp("2010-02-27T06:54:00Z"),
            )


class TestFromZip:
    def test_from_zip_single_segment(
        self, assets: dict[str, Path], mini_station: MiniStation
    ) -> None:
        sac_bytes = assets["orgfile"].read_bytes()
        archive = _zip_of({"IU.ANMO.00.BHZ.SAC": sac_bytes})

        sac = SAC.from_zip(archive)

        assert isinstance(sac, SAC)
        assert sac.station.network == mini_station.network
        assert sac.station.name == mini_station.name

    def test_from_zip_no_segments_raises(self) -> None:
        with pytest.raises(ValueError, match="contains no SAC segments"):
            SAC.from_zip(_zip_of({}))

    def test_from_zip_multiple_segments_raises(self, assets: dict[str, Path]) -> None:
        sac_bytes = assets["orgfile"].read_bytes()
        archive = _zip_of({"segment_1.SAC": sac_bytes, "segment_2.SAC": sac_bytes})

        with pytest.raises(ValueError, match="2 segments") as excinfo:
            SAC.from_zip(archive)
        assert "SAC.all_from_zip()" in str(excinfo.value)

    def test_from_zip_non_zip_raises(self) -> None:
        with pytest.raises(ValueError, match="Not a valid zip archive"):
            SAC.from_zip(b"not a zip archive")

    def test_from_zip_corrupt_member_raises(self) -> None:
        archive = _zip_of({"segment.SAC": b"too short"})
        with pytest.raises(ValueError, match="Could not parse segment"):
            SAC.from_zip(archive)

    def test_all_from_zip_returns_all_segments(self, assets: dict[str, Path]) -> None:
        sac_bytes = assets["orgfile"].read_bytes()
        archive = _zip_of({"segment_1.SAC": sac_bytes, "segment_2.SAC": sac_bytes})

        segments = SAC.all_from_zip(archive)

        assert len(segments) == 2
        assert all(isinstance(segment, SAC) for segment in segments)

    def test_all_from_zip_empty_archive_returns_empty_list(self) -> None:
        assert SAC.all_from_zip(_zip_of({})) == []
