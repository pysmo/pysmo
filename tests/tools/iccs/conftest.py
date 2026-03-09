from collections.abc import Generator
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from pysmo.classes import SAC
from pysmo.functions import clone_to_mini, resample
from pysmo.tools.iccs import ICCS, MiniIccsSeismogram


@pytest.fixture()
def iccs_seismograms() -> Generator[list[MiniIccsSeismogram], Any, None]:
    seismograms: list[MiniIccsSeismogram] = []
    iccs_files = sorted((Path(__file__).parent / "assets/").glob("*.bhz"))

    for sacfile in iccs_files:
        sac = SAC.from_file(sacfile)
        update = {"t0": sac.timestamps.t0}
        seismogram = clone_to_mini(MiniIccsSeismogram, sac.seismogram, update=update)
        seismograms.append(seismogram)

    seismograms[0].data *= -1
    seismograms[1].t0 += pd.Timedelta(seconds=-2)
    seismograms[2].t0 += pd.Timedelta(seconds=2)
    resample(seismograms[3], seismograms[3].delta * 2)
    yield seismograms


@pytest.fixture()
def iccs_instance(
    iccs_seismograms: list[MiniIccsSeismogram],
) -> Generator[ICCS, Any, None]:
    iccs = ICCS(iccs_seismograms)
    yield iccs
