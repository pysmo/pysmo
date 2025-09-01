from pysmo.tools.iccs import ICCS, plotstack
from make_iccs_data import example_data
import matplotlib
import matplotlib.pyplot as plt


matplotlib.use("TkAgg")


def make_plots(dark: bool = False, savefig: bool = False) -> None:
    if dark:
        plt.style.use("dark_background")
    iccs_seismograms = example_data()
    iccs = ICCS(iccs_seismograms)
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_initial.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)

    iccs()
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_first_run.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)

    iccs(autoselect=True)
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_autoselect.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)

    iccs(autoflip=True)
    fig = plotstack(iccs)
    fname = "docs/examples/tools/iccs/stack_autoflip.png"
    if dark:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)


if __name__ == "__main__":
    make_plots(dark=True)
    # make_plots(dark=True, savefig=True)
    # make_plots(dark=False, savefig=True)
