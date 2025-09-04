from collections.abc import Generator
from tests.conftest import TESTDATA
from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from datetime import timedelta
from pysmo.tools.iccs import MiniICCSSeismogram, ICCS
from typing import Any
import pytest


@pytest.fixture()
def iccs_seismograms() -> Generator[list[MiniICCSSeismogram], Any, None]:
    seismograms: list[MiniICCSSeismogram] = []
    for sacfile in TESTDATA["iccs_files"]:
        sac = SAC.from_file(sacfile)
        update = {"t0": sac.timestamps.t0}
        seismogram = clone_to_mini(MiniICCSSeismogram, sac.seismogram, update=update)
        seismograms.append(seismogram)

    seismograms[0].data *= -1
    seismograms[1].t0 += timedelta(seconds=-2)
    seismograms[2].t0 += timedelta(seconds=2)
    yield seismograms


@pytest.fixture()
def iccs_instance(
    iccs_seismograms: list[MiniICCSSeismogram],
) -> Generator[ICCS, Any, None]:
    iccs = ICCS(iccs_seismograms)
    yield iccs
