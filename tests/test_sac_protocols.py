"""
Run tests for the seismogram protocol class
"""

import os
import pytest
import numpy as np
from datetime import datetime, timedelta
from pysmo import SAC, _SacIO
from pysmo.core.protocols import Seismogram


@pytest.fixture()
def sac() -> SAC:
    sacfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    return SAC.from_file(sacfile)


@pytest.fixture()
def sacio() -> _SacIO:
    sacfile = os.path.join(os.path.dirname(__file__), 'testfile.sac')
    return _SacIO.from_file(sacfile)


def test_sac_as_seismogram(sac: Seismogram, sacio: _SacIO) -> None:
    # First read and compare attributes from Seismogram and _SacIO objects,
    # which is somewhat redundant, as they are calculated the same way...
    assert isinstance(sac.data, np.ndarray)
    assert sac.data.all() == sacio.data.all()
    assert sac.sampling_rate == sacio.delta
    assert sac.begin_time.year == sacio.nzyear
    assert sac.begin_time.timetuple().tm_yday == sacio.nzjday + int(sacio.b / 3600)
    assert sac.begin_time.minute == (sacio.nzmin + int(sacio.b / 60)) % 60
    assert sac.begin_time.second == (sacio.nzsec + int(sacio.b)) % 60
    assert sac.begin_time.microsecond == (1000 * (sacio.nzmsec + int(sacio.b * 1000))) % 1000000
    assert sac.end_time - sac.begin_time == timedelta(seconds=sacio.delta * (sacio.npts - 1))

    # ... which is why it is a good idea to look at the actual values
    assert list(sac.data[:5]) == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0]
    assert sac.sampling_rate == pytest.approx(0.02, 0.001)
    assert sac.begin_time == datetime(2005, 3, 1, 7, 23, 2, 160000)
    assert sac.end_time == datetime(2005, 3, 1, 8, 23, 2, 139920)

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
