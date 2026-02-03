from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser
from sybil.evaluators.doctest import NUMBER
from doctest import ELLIPSIS, NORMALIZE_WHITESPACE
from shutil import copyfile, copytree
from typing import Any, Generator
from pathlib import Path
from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from pysmo.tools.iccs import MiniICCSSeismogram
from datetime import timedelta
from getpass import getuser
import random as rd
import pytest
import os
import matplotlib
import tempfile
import platform


@pytest.fixture()
def savedir() -> Path | None:
    if os.getenv("PYSMO_SAVE_FIGS", "false").lower() == "true":
        path = (
            Path("/tmp" if platform.system() == "Darwin" else tempfile.gettempdir())
            / f"pysmo_test_figs_of_{getuser()}"
        )
        path.mkdir(parents=True, exist_ok=True)
        return path
    return None


@pytest.fixture()
def mock_uuid4(monkeypatch: pytest.MonkeyPatch) -> None:
    import uuid

    rand = rd.Random()
    rand.seed(42)
    monkeypatch.setattr(
        uuid, "uuid4", lambda: uuid.UUID(int=rand.getrandbits(128), version=4)
    )


@pytest.fixture()
def mpl_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MPLBACKEND", "Agg")
    matplotlib.use("Agg")


@pytest.fixture()
def copy_testfiles(tmp_path: Path) -> Generator[None, Any, None]:
    cwd = os.getcwd()
    asset_testfile = Path(__file__).parent.parent.parent / "tests/assets/testfile.sac"
    asset_iccsdir = Path(__file__).parent.parent.parent / "tests/assets/iccs/"
    test_testfile = Path(tmp_path) / "example.sac"
    test_iccsdir = Path(tmp_path) / "iccs-example/"
    copyfile(asset_testfile, test_testfile)
    copytree(asset_iccsdir, test_iccsdir)
    try:
        os.chdir(tmp_path)
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture()
def iccs_seismograms() -> Generator[list[MiniICCSSeismogram], Any, None]:
    asset_iccsdir = Path(__file__).parent.parent.parent / "tests/assets/iccs/"
    sacfiles = sorted(asset_iccsdir.glob("*.bhz"))

    iccs_seismograms = []
    for sacfile in sacfiles:
        sac = SAC.from_file(sacfile)
        update = {"t0": sac.timestamps.t0}
        iccs_seismogram = clone_to_mini(
            MiniICCSSeismogram, sac.seismogram, update=update
        )
        iccs_seismograms.append(iccs_seismogram)

    iccs_seismograms[0].data *= -1
    iccs_seismograms[1].t0 += timedelta(seconds=-2)
    iccs_seismograms[2].t0 += timedelta(seconds=2)
    yield iccs_seismograms


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(optionflags=ELLIPSIS + NORMALIZE_WHITESPACE + NUMBER),
        PythonCodeBlockParser(future_imports=["print_function"]),
    ],
    pattern="*.py",
    fixtures=[
        "copy_testfiles",
        "iccs_seismograms",
        "savedir",
        "mpl_backend",
        "mock_uuid4",
        "_syrupy_apply_ide_patches",
    ],
).pytest()
