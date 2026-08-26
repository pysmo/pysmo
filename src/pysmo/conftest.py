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
from sybil.parsers.markdown.skip import SkipParser

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


_run_real_web_requests = False


def pytest_configure(config: pytest.Config) -> None:
    global _run_real_web_requests
    # `--run-real-web-requests` is only registered by tests/conftest.py's
    # pytest_addoption, which isn't guaranteed to load for an invocation
    # scoped to a path outside tests/ (e.g. `pytest src/pysmo/tools/x.py`).
    _run_real_web_requests = bool(
        config.getoption("--run-real-web-requests", default=False)
    )


@pytest.fixture()
def run_real_web_requests() -> bool:
    """Whether `--run-real-web-requests` was passed, for gating a doctest example on it.

    Takes no fixture arguments deliberately: `SybilItem` (Sybil's custom
    `pytest.Item`) requests every fixture named in `Sybil(fixtures=[...])`
    for every collected example, and requesting the built-in `request`
    fixture from one of those breaks `tmp_path` teardown for *all* of
    them — confirmed directly, not assumed. Reading a module-level flag set
    once in `pytest_configure` sidesteps that entirely.

    Pair with a `<!-- skip: next if(not run_real_web_requests) -->` comment
    (invisible in rendered docs) immediately before a docstring example that
    hits live web services, mirroring `tests/conftest.py`'s
    `real_web_request` marker for ordinary test functions.
    """
    return _run_real_web_requests


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
        SkipParser(),
    ],
    pattern="*.py",
    fixtures=[
        "copy_testfiles",
        "iccs_seismograms",
        "savedir",
        "mpl_backend",
        "mock_uuid4",
        "run_real_web_requests",
        "_syrupy_apply_ide_patches",
    ],
).pytest()
