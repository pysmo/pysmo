"""Functions for the ICCS class."""

from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import timedelta
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.cm import ScalarMappable
from matplotlib.widgets import Cursor, Button

if TYPE_CHECKING:
    from ._iccs import ICCS
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from typing import Any
    from matplotlib.backend_bases import Event, MouseEvent

__all__ = ["plotstack", "stack_pick", "update_pick"]

CMAP = mpl.colormaps["cool"]
NORM = PowerNorm(vmin=0, vmax=1, gamma=2)


def _plot_common_stack(
    iccs: ICCS, figsize: tuple[float, float] = (10, 5), constrained: bool = True
) -> tuple[Figure, Axes]:
    time = np.linspace(
        iccs.window_pre.total_seconds(),
        iccs.window_post.total_seconds(),
        len(iccs.stack),
    )
    layout = None
    if constrained:
        layout = "constrained"
    fig, ax = plt.subplots(figsize=figsize, layout=layout)

    for prepared_seismogram, seismogram, ccnorm in zip(
        iccs.seismograms_prepared, iccs.seismograms, iccs.seismograms_ccnorm
    ):
        if seismogram.select:
            color = CMAP(NORM(abs(ccnorm)))
            ax.plot(time, prepared_seismogram.data, linewidth=0.4, color=color)
    ax.plot(
        time,
        iccs.stack.data,
        color=ax.spines["bottom"].get_edgecolor(),
        linewidth=2,
        label="Stack",
    )
    plt.ylabel("Normalised amplitude")
    plt.xlabel("Time relative to pick [s]")
    plt.xlim(iccs.window_pre.total_seconds(), iccs.window_post.total_seconds())
    plt.ylim(auto=None)
    ax.legend(loc="upper left")
    fig.colorbar(
        ScalarMappable(norm=NORM, cmap=CMAP), ax=ax, label="|Correlation coefficient|"
    )
    return fig, ax


def plotstack(iccs: ICCS) -> Figure:
    """Plot the ICCS stack.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.

    Returns:
        Figure of the stack with the seismograms.
    """

    fig, _ = _plot_common_stack(iccs)
    plt.show()
    return fig


def update_pick(iccs: ICCS, pickdelta: timedelta) -> None:
    """Update [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] in all seismograms.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        pickdelta: delta applied to all picks.
    """
    for seismogram in iccs.seismograms:
        current_pick = seismogram.t1 or seismogram.t0
        seismogram.t1 = current_pick + pickdelta
    iccs._clear_caches()  # seismograms and stack need to be refreshed


def stack_pick(iccs: ICCS) -> Figure:
    """Manually pick [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] in the stack and apply it to all seismograms.

    This function launches an interactive figure to manually pick a new phase
    arrival in the stack, and then apply it to all seismograms.

    ![Stack Pick Figure](/examples/tools/iccs/stack_pick.png#only-light){ loading=lazy }
    ![Stack Pick Figure](/examples/tools/iccs/stack_pick_dark.png#only-dark){ loading=lazy }

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.

    Returns:
        Figure of the stack with the picker.
    """

    fig, ax = _plot_common_stack(iccs, figsize=(10, 6), constrained=False)

    fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.96)

    pick_line = ax.axvline(0, color="g", linewidth=2)

    cursor = Cursor(  # noqa: F841
        ax, useblit=True, color="r", linewidth=2, horizOn=False
    )

    class SaveOrCancel:
        def save(self, _: Event) -> None:
            pickdelta = timedelta(seconds=pick_line.get_xdata(orig=True)[0])  # type: ignore
            plt.close()
            update_pick(iccs, pickdelta)

        def cancel(self, _: Event) -> None:
            plt.close()

    callback = SaveOrCancel()
    ax_save = fig.add_axes((0.7, 0.05, 0.1, 0.075))
    ax_cancel = fig.add_axes((0.81, 0.05, 0.1, 0.075))
    b_save = Button(ax_save, "Save", color="darkgreen", hovercolor="green")
    b_save.on_clicked(callback.save)
    b_abort = Button(ax_cancel, "Cancel", color="darkred", hovercolor="red")
    b_abort.on_clicked(callback.cancel)

    def onclick(event: MouseEvent) -> Any:
        if event.inaxes is ax:
            pick_line.set_xdata(np.array((event.xdata, event.xdata)))
            fig.canvas.draw()
            fig.canvas.flush_events()

    _ = fig.canvas.mpl_connect("button_press_event", onclick)  # type: ignore

    plt.show()
    return fig
