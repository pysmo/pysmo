from pysmo.tools.iccs import ICCS, stack_pick, plotstack
from make_iccs_data import example_data
import matplotlib.pyplot as plt


def make_plots(dark: bool = False, savefig: bool = False) -> None:
    if dark:
        plt.style.use("dark_background")
    iccs_seismograms = example_data()
    iccs = ICCS(iccs_seismograms)
    _ = iccs(autoselect=True, autoflip=True)
    fname = "docs/examples/tools/iccs/stack_pick.png"
    fig, _ = stack_pick(iccs, return_fig=True)
    if dark:
        fname = fname.replace(".png", "_dark.png")
    if savefig:
        fig.savefig(fname, transparent=True)
    else:
        fig.show()
    plotstack(iccs)


if __name__ == "__main__":
    make_plots(dark=True)
    # make_plots(dark=False, savefig=True)
    # make_plots(dark=True, savefig=True)
