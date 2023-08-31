import pytest
import os
import shutil
from pysmo import SAC, Seismogram, Station, MiniSeismogram, MiniStation
from pysmo.classes.mini import MiniHypocenter
from pysmo.lib.io import SacIO
from pysmo.types import Hypocenter

TESTDATA = dict(
    orgfile=os.path.join(os.path.dirname(__file__), 'assets/testfile.sac'),
    orgfile_special_IB=os.path.join(os.path.dirname(__file__), 'assets/testfile_iztype_is_IB.sac')
)


@pytest.fixture()
def sacfiles(tmpdir_factory: pytest.TempdirFactory) -> tuple[str, ...]:
    """Define temporary files for testing.

    - sacfile1: copy of reference file, which is not modified during test
    - sacfile2: copy of reference file, which is modified during test
    - sacfile3: used to write a new sac file
    - sacfile_special_IB: copy of sacfile with IZTYPE=IB
    """
    orgfile, orgfile_special_IB = TESTDATA['orgfile'], TESTDATA['orgfile_special_IB']
    tmpdir = tmpdir_factory.mktemp('sacfiles')
    sacfile1 = os.path.join(tmpdir, 'tmpfile1.sac')
    sacfile2 = os.path.join(tmpdir, 'tmpfile2.sac')
    sacfile3 = os.path.join(tmpdir, 'tmpfile3.sac')
    sacfile_special_IB = os.path.join(tmpdir, 'tmpfile_special_IB.sac')
    shutil.copyfile(orgfile, sacfile1)
    shutil.copyfile(orgfile, sacfile2)
    shutil.copyfile(orgfile_special_IB, sacfile_special_IB)
    return sacfile1, sacfile2, sacfile3, sacfile_special_IB


@pytest.fixture()
def picklefiles(tmpdir_factory: pytest.TempdirFactory) -> tuple[str, ...]:
    """Define picklefiles"""
    tmpdir = tmpdir_factory.mktemp('picklefiles')
    picklefile1 = os.path.join(tmpdir, 'tmpfile1.pickle')
    picklefile2 = os.path.join(tmpdir, 'tmpfile2.pickle')
    return picklefile1, picklefile2


@pytest.fixture()
def sacio_instances(sacfiles: tuple[str, ...]) -> tuple[SacIO, ...]:
    """Create SacIO instances"""
    sacio1 = SacIO.from_file(sacfiles[0])
    sacio2 = SacIO.from_file(sacfiles[1])
    sacio3 = SacIO.from_file(sacfiles[3])
    return sacio1, sacio2, sacio3


@pytest.fixture()
def sacio_instance(sacio_instances: tuple[SacIO, ...]) -> SacIO:
    """Return single SacIO instance"""
    return sacio_instances[0]


@pytest.fixture()
def sac_instance(sacfiles: tuple[str, ...]) -> SAC:
    """Returns a SAC instance created from testfile.sac"""
    return SAC.from_file(sacfiles[0])


@pytest.fixture()
def sac_seismogram(sac_instance: SAC) -> Seismogram:
    return sac_instance.seismogram


@pytest.fixture()
def mini_seismogram(sac_seismogram: Seismogram) -> Seismogram:
    return MiniSeismogram(begin_time=sac_seismogram.begin_time, sampling_rate=sac_seismogram.sampling_rate,
                          data=sac_seismogram.data)


@pytest.fixture()
def seismograms(sac_seismogram: Seismogram, mini_seismogram: Seismogram) -> list[Seismogram]:
    return [sac_seismogram, mini_seismogram]


@pytest.fixture()
def sac_station(sac_instance: SAC) -> Station:
    return sac_instance.station


@pytest.fixture()
def mini_station(sac_station: Station) -> Station:
    return MiniStation(latitude=sac_station.latitude, longitude=sac_station.longitude, name=sac_station.name,
                       elevation=sac_station.elevation, network=sac_station.network)


@pytest.fixture()
def stations(sac_station: Station, mini_station: Station) -> tuple[Station, ...]:
    return sac_station, mini_station


@pytest.fixture()
def sac_event(sac_instance: SAC):  # type: ignore
    return sac_instance.event


@pytest.fixture()
def mini_hypocenter(sac_event) -> Hypocenter:  # type:ignore
    return MiniHypocenter(latitude=sac_event.latitude, longitude=sac_event.longitude, depth=sac_event.depth)


@pytest.fixture()
def hypocenters(sac_event: Hypocenter, mini_hypocenter: Hypocenter) -> tuple[Hypocenter, ...]:
    return sac_event, mini_hypocenter
