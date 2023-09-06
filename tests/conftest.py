from typing import Dict
import pytest
import os
import shutil

TESTDATA = dict(
    orgfile=os.path.join(os.path.dirname(__file__), 'assets/testfile.sac'),
    orgfile_special_IB=os.path.join(os.path.dirname(__file__), 'assets/testfile_iztype_is_IB.sac')
)


@pytest.fixture()
def assets() -> Dict[str, str]:
    return dict(
        sacfile=TESTDATA['orgfile'],
        sacfile_IB=TESTDATA['orgfile_special_IB']
    )


@pytest.fixture()
def empty_file(tmpdir_factory: pytest.TempdirFactory) -> str:
    tmpdir = tmpdir_factory.mktemp('empty_files')
    return os.path.join(tmpdir, 'empty_file')


@pytest.fixture()
def sacfile(tmpdir_factory: pytest.TempdirFactory, assets: Dict[str, str]) -> str:
    orgfile = assets['sacfile']
    tmpdir = tmpdir_factory.mktemp('sacfiles')
    testfile = os.path.join(tmpdir, 'testfile.sac')
    shutil.copyfile(orgfile, testfile)
    return testfile
