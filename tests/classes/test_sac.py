from attrs_strict import AttributeTypeError
import numpy as np
import numpy.testing as npt
from pysmo import Seismogram, Station, Event
from pysmo.classes import SAC
from pysmo._lib.defaults import SEISMOGRAM_DEFAULTS
from pysmo._io import SacIO
from pysmo.exc import SacHeaderUndefined
from datetime import datetime, timedelta, timezone
import pytest


class TestSAC:
    def test_create_instance(self) -> None:
        sac = SAC()
        assert isinstance(sac, SAC)
        assert isinstance(sac.seismogram, Seismogram)

        # coordinates for event and station are None.
        with pytest.raises(SacHeaderUndefined):
            assert isinstance(sac.station, Station)
            sac.station.latitude
        with pytest.raises(SacHeaderUndefined):
            assert isinstance(sac.event, Event)
            sac.event.latitude

    @pytest.mark.depends(on=["test_create_instance"])
    def test_defaults(self) -> None:
        sac = SAC()

        assert sac.seismogram.begin_time == SEISMOGRAM_DEFAULTS.begin_time
        assert sac.seismogram.end_time == SEISMOGRAM_DEFAULTS.begin_time
        assert sac.seismogram.delta == SEISMOGRAM_DEFAULTS.delta
        npt.assert_allclose(sac.seismogram.data, np.array([]))

        with pytest.raises(SacHeaderUndefined):
            sac.event.latitude
        with pytest.raises(SacHeaderUndefined):
            sac.event.longitude
        with pytest.raises(SacHeaderUndefined):
            sac.event.time

    @pytest.mark.depends(on=["test_create_instance"])
    def test_create_instance_from_file(self, sacfile: str) -> None:
        sac = SAC.from_file(sacfile)
        assert isinstance(sac, SAC)
        assert isinstance(sac.seismogram, Seismogram)
        assert isinstance(sac.station, Station)
        assert isinstance(sac.event, Event)

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_seismogram(self, sacfile: str) -> None:
        sacseis = SAC.from_file(sacfile).seismogram
        sacio = SacIO.from_file(sacfile)
        assert isinstance(sacseis, Seismogram)
        assert isinstance(sacseis.data, np.ndarray)
        assert sacseis.data.all() == sacio.data.all()
        assert list(sacseis.data[:5]) == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0]
        assert sacseis.delta == sacio.delta == pytest.approx(0.02, 0.001)
        assert sacseis.begin_time == datetime(
            2005, 3, 1, 7, 23, 2, 160000, tzinfo=timezone.utc
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
            assert (
                sacseis.begin_time.microsecond
                == (1000 * (sacio.nzmsec + int(sacio.b * 1000))) % 1000000
            )
        assert sacseis.end_time == datetime(
            2005, 3, 1, 8, 23, 2, 139920, tzinfo=timezone.utc
        )
        assert sacseis.end_time - sacseis.begin_time == timedelta(
            seconds=sacio.delta * (sacio.npts - 1)
        )

        # Change some values
        random_data = np.random.randn(100)
        new_time1 = datetime.fromisoformat("2011-11-04T00:05:23.123").replace(
            tzinfo=timezone.utc
        )
        sacseis.data = random_data
        # changing data should also change end time
        assert sacseis.data.all() == random_data.all()
        assert sacseis.end_time - sacseis.begin_time == timedelta(
            seconds=sacseis.delta * (len(sacseis.data) - 1)
        )
        # changing delta also changes end time
        new_delta = sacseis.delta * 2
        sacseis.delta = new_delta
        assert sacseis.delta == new_delta
        assert sacseis.end_time - sacseis.begin_time == timedelta(
            seconds=sacseis.delta * (len(sacseis.data) - 1)
        )
        # changing the begin time changes end time
        sacseis.begin_time = new_time1
        assert sacseis.begin_time == new_time1
        assert sacseis.end_time - sacseis.begin_time == timedelta(
            seconds=sacseis.delta * (len(sacseis.data) - 1)
        )

        # Setting attributes that are not optional in the types
        # should also not be optional in the classes:
        for item in ["begin_time", "delta", "data"]:
            with pytest.raises((TypeError, AttributeTypeError)):
                setattr(sacseis, item, None)

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_as_station(self, sacfile: str) -> None:
        sac = SAC.from_file(sacfile)
        sacstation = sac.station
        sacio = SacIO.from_file(sacfile)
        assert sacstation.name == sacio.kstnm
        assert sacstation.network == sacio.knetwk
        assert sacstation.latitude == sacio.stla == pytest.approx(-48.46787643432617)
        assert sacstation.longitude == sacio.stlo == pytest.approx(-72.56145477294922)
        assert (
            sacstation.elevation == sacio.stel is None
        )  # testfile happens to not have this set...

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

        # Setting attributes that are not optional in the types
        # should also not be optional in the classes:
        for item in ["name", "latitude", "longitude"]:
            with pytest.raises((TypeError, AttributeTypeError)):
                setattr(sacstation, item, None)

        # This is also true for getting None back from attributes.
        # They may be None in sacio, but not in sac.station
        sac.kstnm = None
        with pytest.raises(SacHeaderUndefined):
            sacstation.name
        sac.stla = None
        with pytest.raises(SacHeaderUndefined):
            sacstation.latitude
        sac.stlo = None
        with pytest.raises(SacHeaderUndefined):
            sacstation.longitude

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_as_event(self, sacfile: str) -> None:
        sac = SAC.from_file(sacfile)
        sacevent = sac.event
        sacio = SacIO.from_file(sacfile)
        assert sacevent.latitude == sacio.evla == pytest.approx(-31.465999603271484)
        assert sacevent.longitude == sacio.evlo == pytest.approx(-71.71800231933594)
        if sacio.evdp is not None:
            assert sacevent.depth == sacio.evdp * 1000 == 26000
        if sac.o is not None:
            assert sacevent.time == sac.seismogram.begin_time + timedelta(
                seconds=sac.o - sac.b
            )
        newtime = sacevent.time + timedelta(seconds=30)
        old_o = sac.o
        sacevent.time = newtime
        assert sacevent.time == newtime
        if old_o is not None:
            assert sac.o == 30.0 + old_o
        sac.o = None
        with pytest.raises(SacHeaderUndefined):
            sacevent.time
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
        # Setting attributes that are not optional in the types
        # should also not be optional in the classes:
        for item in ["depth", "latitude", "longitude", "time"]:
            with pytest.raises((TypeError, AttributeTypeError)):
                setattr(sacevent, item, None)
        sac.evdp = None
        with pytest.raises(SacHeaderUndefined):
            sacevent.depth

    @pytest.mark.depends(on=["test_create_instance_from_file"])
    def test_sac_timestamps(self, sacfile: str) -> None:
        sac = SAC.from_file(sacfile)
        sacio = SacIO.from_file(sacfile)
        assert sac.timestamps.e is not None
        assert sac.timestamps.b is not None
        assert (sac.timestamps.e - sac.timestamps.b).total_seconds() == pytest.approx(
            sacio.e - sacio.b, 0.000001
        )
        now = datetime.now(timezone.utc)
        with pytest.raises(AttributeError):
            sac.timestamps.e = now
        assert sac.timestamps.t0 is None
        sac.timestamps.b = now
        assert sac.timestamps.b == now
        with pytest.raises(TypeError):
            sac.timestamps.b = datetime.now()
