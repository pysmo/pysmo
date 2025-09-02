from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser
from sybil.evaluators.doctest import NUMBER
from doctest import ELLIPSIS, NORMALIZE_WHITESPACE
from shutil import copyfile, copytree
from typing import Any, Generator
from pathlib import Path
from glob import glob
from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from pysmo.tools.iccs import MiniICCSSeismogram
from datetime import timedelta
import pytest
import os


@pytest.fixture()
def copy_testfiles(tmp_path: Path) -> Generator[None, Any, None]:
    cwd = os.getcwd()
    asset_testfile = str(
        os.path.join(os.path.dirname(__file__), "../tests/assets/testfile.sac"),
    )
    asset_iccsdir = str(
        os.path.join(os.path.dirname(__file__), "../tests/assets/iccs/")
    )
    test_testfile = str(tmp_path) + "/example.sac"
    test_iccsdir = str(tmp_path) + "/iccs-example/"
    copyfile(asset_testfile, test_testfile)
    copytree(asset_iccsdir, test_iccsdir)
    try:
        os.chdir(tmp_path)
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture()
def iccs_seismograms() -> Generator[list[MiniICCSSeismogram], Any, None]:
    asset_iccsdir = str(
        os.path.join(os.path.dirname(__file__), "../tests/assets/iccs/")
    )
    sacfiles = sorted(glob(asset_iccsdir + "*.bhz"))

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
    fixtures=["copy_testfiles", "iccs_seismograms"],
).pytest()
