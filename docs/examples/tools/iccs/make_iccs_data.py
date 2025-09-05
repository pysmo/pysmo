from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from pysmo.tools.iccs import MiniICCSSeismogram
from datetime import timedelta
from copy import deepcopy
from glob import glob
import numpy as np


def example_data() -> list[MiniICCSSeismogram]:
    sacfiles = sorted(glob("tests/assets/iccs/*.bhz"))
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

    np.random.seed(0)
    iccs_random = deepcopy(iccs_seismograms[-1])
    iccs_random.data = np.random.rand(len(iccs_random))
    iccs_seismograms.append(iccs_random)
    return iccs_seismograms
