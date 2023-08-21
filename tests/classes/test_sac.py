"""
Run tests for the seismogram protocol class
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from pysmo import Seismogram, SAC
from pysmo.lib.io import SacIO


def test_sac_seismogram(sac_instance: SAC, sacio_instance: SacIO) -> None:
    sacseis = sac_instance.Seismogram
    sacio = sacio_instance
    assert isinstance(sacseis, Seismogram)
    assert isinstance(sacseis.data, np.ndarray)
    assert sacseis.data.all() == sacio.data.all()
    assert list(sacseis.data[:5]) == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0]
    assert sacseis.sampling_rate == sacio.delta == pytest.approx(0.02, 0.001)
    assert sacseis.begin_time == datetime(2005, 3, 1, 7, 23, 2, 160000)
    assert sacseis.begin_time.year == sacio.nzyear
    assert sacseis.begin_time.timetuple().tm_yday == sacio.nzjday + int(sacio.b / 3600)
    assert sacseis.begin_time.minute == (sacio.nzmin + int(sacio.b / 60)) % 60
    assert sacseis.begin_time.second == (sacio.nzsec + int(sacio.b)) % 60
    assert sacseis.begin_time.microsecond == (1000 * (sacio.nzmsec + int(sacio.b * 1000))) % 1000000
    assert sacseis.end_time == datetime(2005, 3, 1, 8, 23, 2, 139920)
    assert sacseis.end_time - sacseis.begin_time == timedelta(seconds=sacio.delta * (sacio.npts - 1))

    # Change some values
    random_data = np.random.randn(100)
    new_time1 = datetime.fromisoformat('2011-11-04T00:05:23.123')
    new_time2 = datetime.fromisoformat('2011-11-04T00:05:23.123155')
    new_time3 = datetime.fromisoformat('2011-11-04T00:05:23.123855')
    new_time4 = datetime.fromisoformat('2011-11-04T00:05:23.999500')
    sacseis.data = random_data
    # changing data should also change end time
    assert sacseis.data.all() == random_data.all()
    assert sacseis.end_time - sacseis.begin_time == timedelta(seconds=sacseis.sampling_rate * (len(sacseis.data)-1))
    # changing sampling rate also changes end time
    new_sampling_rate = sacseis.sampling_rate * 2
    sacseis.sampling_rate = new_sampling_rate
    assert sacseis.sampling_rate == new_sampling_rate
    assert sacseis.end_time - sacseis.begin_time == timedelta(seconds=sacseis.sampling_rate * (len(sacseis.data)-1))
    # changing the begin time changes end time
    sacseis.begin_time = new_time1
    assert sacseis.begin_time == new_time1
    assert sacseis.end_time - sacseis.begin_time == timedelta(seconds=sacseis.sampling_rate * (len(sacseis.data)-1))
    with pytest.warns(RuntimeWarning):
        # rounding down
        sacseis.begin_time = new_time2
        assert sacseis.begin_time.microsecond == round(new_time2.microsecond, -3)
        # rounding up
        sacseis.begin_time = new_time3
        assert sacseis.begin_time.microsecond == round(new_time3.microsecond, -3)
        # rounding up when within 500 microseconds of the next second
        sacseis.begin_time = new_time4
        assert sacseis.begin_time.second == new_time4.second + 1
        assert sacseis.begin_time.microsecond == 0


def test_sac_as_station(sac_instance: SAC, sacio_instance: SacIO) -> None:
    sacstation = sac_instance.Station
    sacio = sacio_instance
    assert sacstation.name == sacio.kstnm
    assert sacstation.network == sacio.knetwk
    assert sacstation.latitude == sacio.stla == pytest.approx(-48.46787643432617)
    assert sacstation.longitude == sacio.stlo == pytest.approx(-72.56145477294922)
    assert sacstation.elevation == sacio.stel is None  # testfile happens to not have this set...

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
    assert sacstation.name == new_name == sac_instance.kstnm
    assert sacstation.network == new_network == sac_instance.knetwk
    assert sacstation.latitude == new_latitude == sac_instance.stla
    assert sacstation.longitude == new_longitude == sac_instance.stlo
    assert sacstation.elevation == new_elevation == sac_instance.stel
    with pytest.raises(ValueError):
        sacstation.latitude = bad_latitude
    with pytest.raises(ValueError):
        sacstation.longitude = bad_longitude


def test_sac_as_event(sac_instance: SAC, sacio_instance: SacIO) -> None:
    sacevent = sac_instance.Event
    sacio = sacio_instance
    assert sacevent.latitude == sacio.evla == pytest.approx(-31.465999603271484)
    assert sacevent.longitude == sacio.evlo == pytest.approx(-71.71800231933594)
    assert sacevent.depth == sacio.evdp * 1000 == 26000
    sacevent.latitude, sacevent.longitude, sacevent.depth = 32, 100, 5000
    assert sacevent.latitude == 32 == sac_instance.evla
    assert sacevent.longitude == 100 == sac_instance.evlo
    assert sacevent.depth == 5000 == sac_instance.evdp * 1000
    with pytest.raises(ValueError):
        sacevent.latitude = 100
    with pytest.raises(ValueError):
        sacevent.latitude = -100
    with pytest.raises(ValueError):
        sacevent.longitude = 500
    with pytest.raises(ValueError):
        sacevent.longitude = -500
