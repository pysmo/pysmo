from typing import Dict
from pathlib import Path
import pytest
import shutil


@pytest.fixture()
def sacfile_IB(
    tmpdir_factory: pytest.TempdirFactory, assets: Dict[str, Path | list[Path]]
) -> Path:
    orgfile: Path = assets["sacfile_IB"]  # type: ignore
    tmpdir = tmpdir_factory.mktemp("sacfiles")
    testfile = Path(tmpdir) / "testfile.sac"
    shutil.copyfile(orgfile, testfile)
    return testfile
