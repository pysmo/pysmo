"""Interactive minimum correlation coefficient update."""

from typing import Literal, overload

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.widgets import (
    Button,
    Cursor,
)

from .._defaults import IccsDefaults
from .._iccs import ICCS
from ._matrix_image import draw_common_matrix_image
from ._widgets import _add_save_cancel_buttons, _ScrollIndexTracker, _widget_gridspec


@overload
def update_min_cc(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[
    Figure, Axes, tuple[Cursor, Line2D, Button, Button, _ScrollIndexTracker]
]: ...


@overload
def update_min_cc(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_min_cc(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    return_fig: bool = True,
) -> (
    tuple[
        Figure,
        Axes,
        tuple[Cursor, Line2D, Button, Button, _ScrollIndexTracker],
    ]
    | None
):
    """Interactively pick a new `min_cc`.

    This function launches an interactive figure to manually pick a new
    [`min_cc`][pysmo.tools.iccs.ICCS.min_cc], which is used when
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm with
    `autoselect` set to `True`.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: `context_seismograms` are used.
            - `False`: `cc_seismograms` are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used. This is the
              default for this function: it sorts/thresholds by correlation
              coefficient, and zero-phase is what's actually used for the
              correlation being thresholded, so it's the more representative
              view.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure with the selector widgets if `return_fig` is `True`.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_min_cc
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs()
        >>> fig, ax, widgets = update_min_cc(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_update_min_cc.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax, widgets = update_min_cc(iccs)
        ...     fig.savefig(savedir / "iccs_update_min_cc-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Interactively setting the minimum correlation coefficient on the matrix image.](../../../images/sybil/iccs_update_min_cc.png#only-light){ loading=lazy }
        ![Interactively setting the minimum correlation coefficient on the matrix image.](../../../images/sybil/iccs_update_min_cc-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    matrix = draw_common_matrix_image(ax, iccs, context, all_seismograms, causal)
    fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)

    gs_widgets = _widget_gridspec(fig, height_ratios=[1], top=0.125, bottom=0.05)
    ax_save = fig.add_subplot(gs_widgets[0, 8:10])
    ax_cancel = fig.add_subplot(gs_widgets[0, 10:12])

    ax.set_title("Pick a new minimal cross-correlation coefficient.")
    pending_val = [iccs.min_cc]

    def handle_valid_pick(new_val: float) -> None:
        pending_val[0] = new_val
        ax.set_title(f"Click save to set min_cc to {new_val:.4f}")

    # Sort by |cc| to match the matrix image's row order (it sorts by |cc|).
    current_ccs = sorted(
        abs(i)
        for i, s in zip(iccs.ccs, iccs.seismograms)
        if s.select or all_seismograms
    )
    if not current_ccs:
        ax.set_title("No seismograms selected - nothing to pick.")
    start_index = int(np.searchsorted(current_ccs, iccs.min_cc))
    max_index = len(matrix) - 1

    pick_line = ax.axhline(start_index, color="g", linewidth=2)
    pick_line_cursor = ax.axhline(start_index, color="g", linewidth=2, linestyle="--")

    def snap_ydata(ydata: float) -> int:
        return max(0, round(min(ydata, max_index)))

    def calc_cc(line: Line2D) -> float:
        if not current_ccs:
            return iccs.min_cc
        index = round(np.asarray(line.get_ydata())[0], 0)
        if index == 0:
            return IccsDefaults.index_zero_multiplier * current_ccs[0]
        return float(np.mean(current_ccs[index - 1 : index + 1]))

    def onclick(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if event.inaxes is ax and event.ydata is not None:
            ydata = snap_ydata(event.ydata)
            pick_line.set_ydata((ydata, ydata))
            pick_line.set_visible(True)
            handle_valid_pick(calc_cc(pick_line))
            if ax.figure:
                ax.figure.canvas.draw_idle()

    def on_mouse_move(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if event.inaxes is ax and event.ydata is not None:
            ydata = snap_ydata(event.ydata)
            pick_line_cursor.set_ydata((ydata, ydata))
            pick_line_cursor.set_visible(True)
        else:
            pick_line_cursor.set_visible(False)
        if ax.figure:
            ax.figure.canvas.draw_idle()

    cursor = Cursor(ax, useblit=True, vertOn=False, horizOn=False)

    if isinstance(ax.figure, Figure):
        tracker = _ScrollIndexTracker(ax, ax.figure)
        ax.figure.canvas.mpl_connect("scroll_event", tracker.on_scroll)
        ax.figure.canvas.mpl_connect("button_press_event", onclick)
        ax.figure.canvas.mpl_connect("motion_notify_event", on_mouse_move)
    else:
        tracker = _ScrollIndexTracker(ax, Figure())

    def on_save(_: Event) -> None:
        iccs.min_cc = pending_val[0]
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(ax_save, ax_cancel, on_save, on_cancel)

    if return_fig:
        return fig, ax, (cursor, pick_line, b_save, b_cancel, tracker)
    plt.show()
    return None
