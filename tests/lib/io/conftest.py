from typing import Dict
import pytest
import os
import shutil


@pytest.fixture()
def sacfile_IB(tmpdir_factory: pytest.TempdirFactory, assets: Dict[str, str]) -> str:
    orgfile = assets['sacfile_IB']
    tmpdir = tmpdir_factory.mktemp('sacfiles')
    testfile = os.path.join(tmpdir, 'testfile.sac')
    shutil.copyfile(orgfile, testfile)
    return testfile
