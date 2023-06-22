import pytest
import os
import shutil
from pysmo import SAC
from pysmo.io import _SacIO


@pytest.fixture()
def orgfiles() -> tuple[str, ...]:
    """Returns full path of test sac files"""
    orgfile = os.path.join(os.path.dirname(__file__), 'assets/testfile.sac')
    orgfile_special_IB = os.path.join(os.path.dirname(__file__), 'assets/testfile_iztype_is_IB.sac')
    return orgfile, orgfile_special_IB


@pytest.fixture()
def sacfiles(tmpdir_factory: pytest.TempdirFactory, orgfiles: tuple[str, ...]) -> tuple[str, ...]:
    """
    Define temporary files for testing.
    - sacfile1: copy of reference file, which is not modified during test
    - sacfile2: copy of reference file, which is modified during test
    - sacfile3: used to write a new sac file
    - sacfile_special_IB: copy of sacfile with IZTYPE=IB
    """
    orgfile, orgfile_special_IB = orgfiles
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
    """Defile picklefiles"""
    tmpdir = tmpdir_factory.mktemp('picklefiles')
    picklefile1 = os.path.join(tmpdir, 'tmpfile1.pickle')
    picklefile2 = os.path.join(tmpdir, 'tmpfile2.pickle')
    return picklefile1, picklefile2


@pytest.fixture()
def sacio_instances(sacfiles: tuple[str, ...]) -> tuple[_SacIO, ...]:
    """Create _SacIO instances"""
    sacio1 = _SacIO.from_file(sacfiles[0])
    sacio2 = _SacIO.from_file(sacfiles[1])
    sacio3 = _SacIO.from_file(sacfiles[3])
    return sacio1, sacio2, sacio3


@pytest.fixture()
def sacio_instance(sacio_instances: tuple[_SacIO, ...]) -> _SacIO:
    """Return single _SacIO instance"""
    return sacio_instances[0]


@pytest.fixture()
def sac_instance(sacfiles: tuple[str, ...]) -> SAC:
    """Returns a SAC instance created from testfile.sac"""
    return SAC.from_file(sacfiles[0])
