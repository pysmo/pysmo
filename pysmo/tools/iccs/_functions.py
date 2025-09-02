"""Functions for the ICCS class."""

from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import timedelta
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm
from matplotlib.cm import ScalarMappable
from matplotlib.widgets import Cursor, Button, SpanSelector

if TYPE_CHECKING:
    from ._iccs import ICCS
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from typing import Any
    from matplotlib.backend_bases import Event, MouseEvent

__all__ = ["plotstack", "stack_pick", "stack_tw_pick", "update_pick"]

CMAP = mpl.colormaps["cool"]
NORM = PowerNorm(vmin=0, vmax=1, gamma=2)


def _plot_common_stack(
    iccs: ICCS,
    padded: bool = True,
    figsize: tuple[float, float] = (10, 5),
    constrained: bool = True,
) -> tuple[Figure, Axes]:
    """Returns a basic stack plot for use in other plots."""

    layout = None
    if constrained:
        layout = "constrained"
    fig, ax = plt.subplots(figsize=figsize, layout=layout)

    seismograms_prepared = iccs.seismograms_prepared
    stack = iccs.stack
    xmin, xmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    if padded:
        ax.axvspan(xmin, xmax, color="lightgreen", alpha=0.2, label="Time Window")
        seismograms_prepared = iccs.seismograms_for_plotting
        stack = iccs.stack_for_plotting
        xmin, xmax = (
            (iccs.window_pre - iccs.plot_padding).total_seconds(),
            (iccs.window_post + iccs.plot_padding).total_seconds(),
        )

    time = np.linspace(xmin, xmax, len(stack))

    for seismogram_prepared, seismogram, ccnorm in zip(
        seismograms_prepared, iccs.seismograms, iccs.seismograms_ccnorm
    ):
        if seismogram.select:
            color = CMAP(NORM(abs(ccnorm)))
            ax.plot(time, seismogram_prepared.data, linewidth=0.4, color=color)
    ax.plot(
        time,
        stack.data,
        color=ax.spines["bottom"].get_edgecolor(),
        linewidth=2,
        label="Stack",
    )
    plt.ylabel("Normalised amplitude")
    plt.xlabel("Time relative to pick [s]")
    plt.xlim(xmin, xmax)
    plt.ylim(auto=None)
    ax.legend(loc="upper left")
    fig.colorbar(
        ScalarMappable(norm=NORM, cmap=CMAP), ax=ax, label="|Correlation coefficient|"
    )
    return fig, ax


def plotstack(iccs: ICCS, padded: bool = True) -> Figure:
    """Plot the ICCS stack.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].

    Returns:
        Figure of the stack with the seismograms.

    Examples:
        The default plotting mode is to pad the stack beyond the time window
        used for the cross-correlations (highlighted in light green). This is
        useful particularly useful for narrow time windows. Note that because
        of the padding, the displayed stack isn't exactly what is used for the
        cross-correlations.

        ```python
        >>> from pysmo.tools.iccs import ICCS, plotstack
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> plotstack(iccs)
        <Figure size...
        >>>
        ```

        ![plotstack padded](/examples/tools/iccs/plotstack_padded.png#only-light){ loading=lazy }
        ![plotstack padded](/examples/tools/iccs/plotstack_padded_dark.png#only-dark){ loading=lazy }

        To view the stack exactly as it is used in the cross-correlations, set
        the `padded` argument to `False`:

        ```python
        >>> plotstack(iccs, padded=False)
        <Figure size...
        >>>
        ```

        ![plotstack](/examples/tools/iccs/plotstack.png#only-light){ loading=lazy }
        ![plotstack](/examples/tools/iccs/plotstack_dark.png#only-dark){ loading=lazy }
    """

    fig, _ = _plot_common_stack(iccs, padded)
    plt.show()
    return fig


def update_pick(iccs: ICCS, pickdelta: timedelta) -> None:
    """Update [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] in all seismograms by the same amount.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        pickdelta: delta applied to all picks.
    """
    for seismogram in iccs.seismograms:
        current_pick = seismogram.t1 or seismogram.t0
        seismogram.t1 = current_pick + pickdelta
    iccs._clear_caches()  # seismograms and stack need to be refreshed


def stack_pick(iccs: ICCS, padded: bool = True) -> Figure:
    """Manually pick [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] in the stack and apply it to all seismograms.

    This function launches an interactive figure to manually pick a new phase
    arrival in the stack, and then apply it to all seismograms.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].


    Returns:
        Figure of the stack with the picker.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, stack_pick
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> stack_pick(iccs)
        <Figure size...
        >>>
        ```

        ![Stack Pick Figure](/examples/tools/iccs/stack_pick.png#only-light){ loading=lazy }
        ![Stack Pick Figure](/examples/tools/iccs/stack_pick_dark.png#only-dark){ loading=lazy }
    """

    fig, ax = _plot_common_stack(iccs, padded, figsize=(10, 6), constrained=False)

    fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.96)

    pick_line = ax.axvline(0, color="g", linewidth=2)

    cursor = Cursor(  # noqa: F841
        ax, useblit=True, color="r", linewidth=2, horizOn=False
    )

    def onclick(event: MouseEvent) -> Any:
        if event.inaxes is ax:
            pick_line.set_xdata(np.array((event.xdata, event.xdata)))
            fig.canvas.draw()
            fig.canvas.flush_events()

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

    _ = fig.canvas.mpl_connect("button_press_event", onclick)  # type: ignore

    plt.show()
    return fig


def stack_tw_pick(iccs: ICCS, padded: bool = True) -> Figure:
    """Pick new time window limits in the stack.

    This function launches an interactive figure to pick new values for
    [`window_pre`][pysmo.tools.iccs.ICCS.window_pre] and
    [`window_post`][pysmo.tools.iccs.ICCS.window_post].

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].

    Returns:
        Figure of the stack with the picker.

    Info:
        The new time window may not be chosen such that the pick lies
        outside the the window. The picker will therefore automatically correct
        itself for invalid window choices.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, stack_tw_pick
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> stack_tw_pick(iccs)
        <Figure size...
        >>>
        ```

        ![Stack Pick Figure](/examples/tools/iccs/stack_tw_pick.png#only-light){ loading=lazy }
        ![Stack Pick Figure](/examples/tools/iccs/stack_tw_pick_dark.png#only-dark){ loading=lazy }
    """

    fig, ax = _plot_common_stack(iccs, padded, figsize=(10, 6), constrained=False)

    fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.96)

    def onselect(xmin: float, xmax: float) -> None:
        # phase arrival pick must be inside time window
        if xmin >= 0:
            xmin = -iccs.stack.delta.total_seconds()
        if xmax <= 0:
            xmax = iccs.stack.delta.total_seconds()

        # time window should not excced the plot
        xlim_min, xlim_max = ax.get_xlim()
        if xmin < xlim_min:
            xmin = xlim_min
        if xmax > xlim_max:
            xmax = xlim_max

        span.extents = (xmin, xmax)

    span = SpanSelector(
        ax,
        onselect,
        "horizontal",
        useblit=True,
        props=dict(alpha=0.5, facecolor="tab:blue"),
        interactive=True,
        drag_from_anywhere=True,
    )

    span.extents = (
        iccs.window_pre.total_seconds(),
        iccs.window_post.total_seconds(),
    )

    class SaveOrCancel:
        def save(self, _: Event) -> None:
            iccs.window_pre = timedelta(seconds=span.extents[0])
            iccs.window_post = timedelta(seconds=span.extents[1])
            plt.close()

        def cancel(self, _: Event) -> None:
            plt.close()

    callback = SaveOrCancel()
    ax_save = fig.add_axes((0.7, 0.05, 0.1, 0.075))
    ax_cancel = fig.add_axes((0.81, 0.05, 0.1, 0.075))
    b_save = Button(ax_save, "Save", color="darkgreen", hovercolor="green")
    b_save.on_clicked(callback.save)
    b_abort = Button(ax_cancel, "Cancel", color="darkred", hovercolor="red")
    b_abort.on_clicked(callback.cancel)

    plt.show()
    return fig
