"""Interactive pick update."""

from typing import Literal, overload

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.widgets import (
    Button,
    Cursor,
)

from .._iccs import ICCS
from ._widgets import (
    _add_save_cancel_buttons,
    _draw_stack_or_matrix,
    _left_margin,
    _widget_gridspec,
)


@overload
def update_pick(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    causal: bool = True,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes, tuple[Cursor, Line2D, Button, Button]]: ...


@overload
def update_pick(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    causal: bool = True,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_pick(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    causal: bool = True,
    return_fig: bool = True,
) -> tuple[Figure, Axes, tuple[Cursor, Line2D, Button, Button]] | None:
    """Manually set a new pick and apply it to all seismograms.

    This function launches an interactive figure to manually pick a new phase
    arrival, and then apply it to the
    [`refined_pick`][pysmo.tools.iccs.IccsSeismogram.refined_pick] attribute of
    all seismograms.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: `context_seismograms` are used.
            - `False`: `cc_seismograms` are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_matrix_image: Use the
            [matrix image][pysmo.tools.iccs.plot_matrix_image]
            instead of the [stack][pysmo.tools.iccs.plot_stack].
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
              This is the default for this function, since locating a phase
              onset by eye is exactly what zero-phase filtering's acausal
              precursor smearing distorts.
            - `False`: zero-phase filtered seismograms are used.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the stack with the picker if `return_fig` is `True`.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_pick
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax, widgets = update_pick(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_update_pick.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax, widgets = update_pick(iccs)
        ...     fig.savefig(savedir / "iccs_update_pick-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Interactively picking a new reference time on the ICCS stack.](../../../images/sybil/iccs_update_pick.png#only-light){ loading=lazy }
        ![Interactively picking a new reference time on the ICCS stack.](../../../images/sybil/iccs_update_pick-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    _draw_stack_or_matrix(ax, iccs, context, all_seismograms, causal, use_matrix_image)
    fig.subplots_adjust(
        bottom=0.2, left=_left_margin(use_matrix_image), right=0.95, top=0.93
    )

    gs_widgets = _widget_gridspec(fig, height_ratios=[1], top=0.125, bottom=0.05)
    ax_save = fig.add_subplot(gs_widgets[0, 8:10])
    ax_cancel = fig.add_subplot(gs_widgets[0, 10:12])

    ax.set_title("Update pick for all seismograms.")
    pending_pick = [0.0]

    def handle_valid_pick(xdata: float) -> None:
        pending_pick[0] = xdata
        ax.set_title(f"Click save to adjust pick by {xdata:.3f} seconds.")

    pick_line = ax.axvline(0, color="g", linewidth=2)
    cursor = Cursor(
        ax, useblit=True, color="g", linewidth=2, horizOn=False, linestyle="--"
    )

    def onclick(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if (
            event.inaxes is ax
            and event.xdata is not None
            and iccs.validate_pick(pd.Timedelta(seconds=event.xdata))
        ):
            pick_line.set_xdata(np.array((event.xdata, event.xdata)))
            handle_valid_pick(event.xdata)
            if ax.figure:
                ax.figure.canvas.draw()
                ax.figure.canvas.flush_events()

    def on_mouse_move(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if event.inaxes == ax and event.xdata is not None:
            is_valid = iccs.validate_pick(pd.Timedelta(seconds=event.xdata))
            cursor.linev.set_color("g" if is_valid else "r")

    if isinstance(ax.figure, Figure):
        ax.figure.canvas.mpl_connect("button_press_event", onclick)
        ax.figure.canvas.mpl_connect("motion_notify_event", on_mouse_move)

    def on_save(_: Event) -> None:
        iccs.update_all_picks(pd.Timedelta(seconds=pending_pick[0]))
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(ax_save, ax_cancel, on_save, on_cancel)

    if return_fig:
        return fig, ax, (cursor, pick_line, b_save, b_cancel)
    plt.show()
    return None
