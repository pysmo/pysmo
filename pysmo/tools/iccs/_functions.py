"""Functions for the ICCS class."""

from __future__ import annotations
from typing import TYPE_CHECKING

# from datetime import timedelta
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.cm import ScalarMappable

# from matplotlib.widgets import Cursor, Button

if TYPE_CHECKING:
    from ._iccs import ICCS
    from matplotlib.figure import Figure

    # from typing import Any
    # from matplotlib.backend_bases import Event, MouseEvent

__all__ = ["plotstack"]

CMAP = mpl.colormaps["cool"]
NORM = PowerNorm(vmin=0, vmax=1, gamma=2)


def plotstack(iccs: ICCS) -> Figure:
    """Plot the stack with the seismograms."""

    time = np.linspace(
        iccs.window_pre.total_seconds(),
        iccs.window_post.total_seconds(),
        len(iccs.stack),
    )
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
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
    plt.show()
    return fig


# def stack_pick(iccs: ICCS) -> None:
#     window_pre_in_seconds = iccs.window_pre.total_seconds()
#     window_post_in_seconds = iccs.window_post.total_seconds()
#     padding_in_seconds = iccs.plot_padding.total_seconds()
#     seismograms = iccs.seismograms_for_plotting
#     time_seis = np.linspace(
#         window_pre_in_seconds - padding_in_seconds,
#         window_post_in_seconds + padding_in_seconds,
#         len(seismograms[0]),
#     )
#     stack = iccs.stack
#     time_stack = np.linspace(window_pre_in_seconds, window_post_in_seconds, len(stack))
#     fig, ax = plt.subplots()
#     fig.subplots_adjust(bottom=0.2)
#     for seismogram in seismograms:
#         ax.plot(time_seis, seismogram.data, color="k", alpha=0.1)
#     ax.plot(time_stack, stack.data, color="purple")
#     plt.xlabel("Time relative to pick [s]")
#     plt.ylabel("Normalised amplitude")
#     plt.xlim(window_pre_in_seconds, window_post_in_seconds)
#     plt.ylim(auto=None)
#     pick_line = ax.axvline(0, color="g", linewidth=1)
#     _ = Cursor(ax, useblit=True, color="grey", linewidth=1, horizOn=False)
#
#     class SaveOrAbort:
#         def save(self, _: Event) -> None:
#             pickdelta = timedelta(seconds=pick_line.get_xdata(orig=True)[0])  # type: ignore
#             # update_pick(iccs, pickdelta)
#
#         def close(self, _: Event) -> None:
#             plt.close()
#
#     callback = SaveOrAbort()
#     ax_save = fig.add_axes((0.7, 0.05, 0.1, 0.075))
#     ax_abort = fig.add_axes((0.81, 0.05, 0.1, 0.075))
#     b_save = Button(ax_save, "Save")
#     b_save.on_clicked(callback.save)
#     b_close = Button(ax_abort, "Close")
#     b_close.on_clicked(callback.close)
#
#     def onclick(event: MouseEvent) -> Any:
#         if event.inaxes is ax:
#             pick_line.set_xdata(np.array((event.xdata, event.xdata)))
#             fig.canvas.draw()
#             fig.canvas.flush_events()
#
#     _ = fig.canvas.mpl_connect("button_press_event", onclick)  # type: ignore
#
#     plt.show()
