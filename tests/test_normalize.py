"""
Run tests for all functions defined in pysmo.sac.sacfunc
"""

from pysmo import Station, Seismogram, SAC
from pysmo.functions import normalize
from typing import Any
import os
import shutil
import pytest
import numpy as np


@pytest.fixture()
def sacfile() -> str:
    """Determine absolute path of the test SAC file."""
    return os.path.join(os.path.dirname(__file__), 'assets/testfile.sac')


@pytest.fixture()
def data_objects(tmp_path_factory: pytest.TempPathFactory, sacfile: str) -> tuple[list[Seismogram], list[Station],
                                                                                  list[Any]]:
    """Returns instances of test objects to use with functions"""
    seismograms: list = []
    stations: list = []
    events: list = []
    # SAC provides seismogram, station and event
    test_sacfile = tmp_path_factory.mktemp("data") / "testfile.sac"
    shutil.copyfile(sacfile, test_sacfile)
    sacobj = SAC.from_file(str(test_sacfile))
    seismograms.append(sacobj.Seismogram)
    stations.append(sacobj.Station)
    events.append(sacobj.Event)
    return seismograms, stations, events


def test_normalize(data_objects: tuple[list[Seismogram], ...]) -> None:
    """Normalize data with its absolute maximum value"""
    seismograms, *_ = data_objects
    for seis in seismograms:
        normalized_seis = normalize(seis)
        assert np.max(normalized_seis.data) <= 1
