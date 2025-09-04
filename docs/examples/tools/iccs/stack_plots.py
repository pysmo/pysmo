from pysmo.tools.iccs import ICCS, plotstack
from make_iccs_data import example_data
import matplotlib.pyplot as plt


def make_plots(dark: bool = False, savefig: bool = False) -> None:
    if dark is True:
        plt.style.use("dark_background")

    iccs_seismograms = example_data()
    iccs = ICCS(iccs_seismograms)
    fig, _ = plotstack(iccs, False, return_fig=True)
    fname = "docs/examples/tools/iccs/stack_initial.png"
    if dark is True:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)

    _ = iccs()
    fig, _ = plotstack(iccs, False, return_fig=True)
    fname = "docs/examples/tools/iccs/stack_first_run.png"
    if dark is True:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)

    _ = iccs(autoselect=True)
    fig, _ = plotstack(iccs, False, return_fig=True)
    fname = "docs/examples/tools/iccs/stack_autoselect.png"
    if dark is True:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)

    _ = iccs(autoflip=True)
    fig, _ = plotstack(iccs, False, return_fig=True)
    fname = "docs/examples/tools/iccs/stack_autoflip.png"
    if dark is True:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)


if __name__ == "__main__":
    make_plots()
    make_plots(dark=True)
    # make_plots(savefig=True)
    # make_plots(dark=True, savefig=True)
