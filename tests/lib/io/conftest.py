import shutil
from pathlib import Path

import pytest

SACIO_ASSETS = {
    "sacfile_IB": Path(__file__).parent / "assets/testfile_iztype_is_IB.sac",
    "sacfile_no_b": Path(__file__).parent / "assets/no_b.sac",
    "sacfile_v6": Path(__file__).parent / "assets/funcgen6.sac",
    "sacfile_v7": Path(__file__).parent / "assets/funcgen7.sac",
    "sacfile_irlim": Path(__file__).parent / "assets/funcgen_irlim_v7.sac",
    "sacfile_iamph": Path(__file__).parent / "assets/funcgen_iamph_v7.sac",
    "sacfile_uneven": Path(__file__).parent / "assets/funcgen_uneven_v6.sac",
    "sacfile_ixy": Path(__file__).parent / "assets/funcgen_ixy_v6.sac",
}


@pytest.fixture()
def sacfile_IB(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_IB"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_no_b(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_no_b"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_v6(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_v6"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_v7(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_v7"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_irlim(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_irlim"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_iamph(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_iamph"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_uneven(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_uneven"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile


@pytest.fixture()
def sacfile_ixy(tmpdir_factory: pytest.TempdirFactory) -> Path:
    orgfile = SACIO_ASSETS["sacfile_ixy"]
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile
