"""
Run tests for the seismogram protocol class
"""

import os
import pytest
import numpy as np
from datetime import datetime, timedelta
from pysmo import SAC, _SacIO
from pysmo.core.protocols import Seismogram, Station


@pytest.fixture()
def sac() -> SAC:
    sacfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    return SAC.from_file(sacfile)


@pytest.fixture()
def sacio() -> _SacIO:
    sacfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    return _SacIO.from_file(sacfile)


def test_sac_as_seismogram(sac: Seismogram, sacio: _SacIO) -> None:
    assert isinstance(sac.data, np.ndarray)
    assert sac.data.all() == sacio.data.all()
    assert list(sac.data[:5]) == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0]
    assert sac.sampling_rate == sacio.delta == pytest.approx(0.02, 0.001)
    assert sac.begin_time == datetime(2005, 3, 1, 7, 23, 2, 160000)
    assert sac.begin_time.year == sacio.nzyear
    assert sac.begin_time.timetuple().tm_yday == sacio.nzjday + int(sacio.b / 3600)
    assert sac.begin_time.minute == (sacio.nzmin + int(sacio.b / 60)) % 60
    assert sac.begin_time.second == (sacio.nzsec + int(sacio.b)) % 60
    assert sac.begin_time.microsecond == (1000 * (sacio.nzmsec + int(sacio.b * 1000))) % 1000000
    assert sac.end_time == datetime(2005, 3, 1, 8, 23, 2, 139920)
    assert sac.end_time - sac.begin_time == timedelta(seconds=sacio.delta * (sacio.npts - 1))

    # Change some values
    random_data = np.random.randn(100)
    new_time1 = datetime.fromisoformat('2011-11-04T00:05:23.123')
    new_time2 = datetime.fromisoformat('2011-11-04T00:05:23.123155')
    new_time3 = datetime.fromisoformat('2011-11-04T00:05:23.123855')
    new_time4 = datetime.fromisoformat('2011-11-04T00:05:23.999500')
    sac.data = random_data
    # changing data should also change end time
    assert sac.data.all() == random_data.all()
    assert sac.end_time - sac.begin_time == timedelta(seconds=sac.sampling_rate * (len(sac.data)-1))
    # changing sampling rate also changes end time
    new_sampling_rate = sac.sampling_rate * 2
    sac.sampling_rate = new_sampling_rate
    assert sac.sampling_rate == new_sampling_rate
    assert sac.end_time - sac.begin_time == timedelta(seconds=sac.sampling_rate * (len(sac.data)-1))
    # changing the begin time changes end time
    sac.begin_time = new_time1
    assert sac.begin_time == new_time1
    assert sac.end_time - sac.begin_time == timedelta(seconds=sac.sampling_rate * (len(sac.data)-1))
    with pytest.warns(RuntimeWarning):
        # rounding down
        sac.begin_time = new_time2
        assert sac.begin_time.microsecond == round(new_time2.microsecond, -3)
        # rounding up
        sac.begin_time = new_time3
        assert sac.begin_time.microsecond == round(new_time3.microsecond, -3)
        # rounding up when within 500 microseconds of the next second
        sac.begin_time = new_time4
        assert sac.begin_time.second == new_time4.second + 1
        assert sac.begin_time.microsecond == 0


def test_sac_as_station(sac: Station, sacio: _SacIO) -> None:
    assert sac.name == sacio.kstnm
    assert sac.station_latitude == sacio.stla == pytest.approx(-48.46787643432617)
    assert sac.station_longitude == sacio.stlo == pytest.approx(-72.56145477294922)
    assert sac.station_elevation == sacio.stel is None  # testfile happens to not have this set...

    # try changing values
    new_name = "new_name"
    new_latitude = 23.3
    bad_latitude = 9199
    new_longitude = -123
    bad_longitude = 500
    new_elevation = 123
    sac.name = new_name
    sac.station_latitude = new_latitude
    sac.station_longitude = new_longitude
    sac.station_elevation = new_elevation
    assert sac.name == new_name
    assert sac.station_latitude == new_latitude == sac.stla
    assert sac.station_longitude == new_longitude == sac.stlo
    assert sac.station_elevation == new_elevation == sac.stel
    with pytest.raises(ValueError):
        sac.station_latitude = bad_latitude
    with pytest.raises(ValueError):
        sac.station_longitude = bad_longitude
