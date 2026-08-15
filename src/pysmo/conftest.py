import os
import random as rd
from doctest import ELLIPSIS, NORMALIZE_WHITESPACE
from pathlib import Path
from shutil import copyfile
from typing import Any, Generator

import matplotlib
import pandas as pd
import pytest
from sybil import Sybil
from sybil.evaluators.doctest import NUMBER
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser

from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from pysmo.tools.iccs import MiniIccsSeismogram

DOCS_IMAGE_DIR = Path(__file__).parent.parent.parent / "docs/images/sybil"


@pytest.fixture(scope="module")
def savedir() -> Path | None:
    if os.getenv("PYSMO_SAVE_FIGS", "false").lower() == "true":
        return DOCS_IMAGE_DIR
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
def copy_testfiles(
    tmp_path: Path, reference_event_assets: dict[str, Path]
) -> Generator[None, Any, None]:
    cwd = os.getcwd()
    test_testfile = Path(tmp_path) / "example.sac"
    test_stationxml = Path(tmp_path) / "example_response.xml"
    test_sacpz = Path(tmp_path) / "SACPZ.IU.ANMO.00.BHZ"
    copyfile(reference_event_assets["sac_bhz"], test_testfile)
    copyfile(reference_event_assets["stationxml_bhz"], test_stationxml)
    copyfile(reference_event_assets["sacpz_bhz"], test_sacpz)
    try:
        os.chdir(tmp_path)
        yield
    finally:
        os.chdir(cwd)


@pytest.fixture()
def iccs_seismograms(
    iccs_events_assets: dict[str, dict[str, Path]],
) -> Generator[list[MiniIccsSeismogram], Any, None]:
    event_stations = iccs_events_assets["solomon_islands"]
    sacfiles = [event_stations[station] for station in sorted(event_stations)]

    iccs_seismograms = []
    for sacfile in sacfiles:
        sac = SAC.from_file(sacfile)
        update = {"t0": sac.timestamps.t0}
        iccs_seismogram = clone_to_mini(
            MiniIccsSeismogram, sac.seismogram, update=update
        )
        iccs_seismograms.append(iccs_seismogram)

    iccs_seismograms[0].data *= -1
    iccs_seismograms[1].t0 += pd.Timedelta(seconds=-2)
    iccs_seismograms[2].t0 += pd.Timedelta(seconds=2)
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
