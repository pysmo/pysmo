"""
Run tests for the seismogram protocol class
"""

import os
import pytest
import numpy as np
from datetime import datetime
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
    assert isinstance(sac.data, np.ndarray)
    assert list(sac.data[:5]) == [2302.0, 2313.0, 2345.0, 2377.0, 2375.0]
    assert sac.begin_time == datetime(2005, 3, 2, 7, 23, 2, 160000)
    assert sac.begin_time.year == sacio.nzyear
