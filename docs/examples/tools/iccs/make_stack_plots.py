from pysmo.classes import SAC
from pysmo.functions import clone_to_mini
from pysmo.tools.iccs import MiniICCSSeismogram, ICCS, plotstack
from glob import glob
from datetime import timedelta
from copy import deepcopy
import matplotlib
import matplotlib.pyplot as plt
import numpy as np


matplotlib.use("TkAgg")


def make_iccs_seismograms() -> list[MiniICCSSeismogram]:
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

    iccs_random = deepcopy(iccs_seismograms[-1])
    iccs_random.data = np.random.rand(len(iccs_random))
    iccs_seismograms.append(iccs_random)
    return iccs_seismograms


def make_plots(dark: bool = False) -> None:
    if dark:
        plt.style.use("dark_background")
    iccs_seismograms = make_iccs_seismograms()
    iccs = ICCS(iccs_seismograms)
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_initial.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    fig.savefig(fname, transparent=True)

    iccs()
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_first_run.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    fig.savefig(fname, transparent=True)

    iccs(autoselect=True)
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_autoselect.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    fig.savefig(fname, transparent=True)

    iccs(autoflip=True)
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_autoflip.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    fig.savefig(fname, transparent=True)


if __name__ == "__main__":
    make_plots(dark=False)
    make_plots(dark=True)
