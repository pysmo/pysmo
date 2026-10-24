"""Interactive time window update."""

from typing import Literal, overload

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event
from matplotlib.figure import Figure
from matplotlib.widgets import (
    Button,
    SpanSelector,
)

from .._iccs import ICCS
from ._widgets import (
    _add_save_cancel_buttons,
    _draw_stack_or_matrix,
    _left_margin,
    _widget_gridspec,
)


@overload
def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    causal: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes, tuple[SpanSelector, Button, Button]]: ...


@overload
def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    causal: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    causal: bool = False,
    return_fig: bool = True,
) -> tuple[Figure, Axes, tuple[SpanSelector, Button, Button]] | None:
    """Pick new time window limits.

    This function launches an interactive figure to pick new values for
    [`window_pre`][pysmo.tools.iccs.ICCS.window_pre] and
    [`window_post`][pysmo.tools.iccs.ICCS.window_post].

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
            - `False`: zero-phase filtered seismograms are used. This is
              the default for this function: `window_pre`/`window_post`
              crop [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms]
              (zero-phase), which is what cross-correlation, stacking, and
              MCCC actually run on regardless of what's displayed here.
              Picking the window against the causal display risks
              misjudging the pre-arrival margin: the causal view's clean
              quiet period before the onset doesn't reflect that the
              zero-phase data being cropped may already carry acausal
              precursor energy inside that same interval.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the stack with the picker if `return_fig` is `True`.

    Info: Window is clamped around the pick
        The new time window may not be chosen such that the pick lies
        outside the window. The picker will therefore automatically correct
        itself for invalid window choices.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_timewindow
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax, widgets = update_timewindow(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_update_timewindow.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax, widgets = update_timewindow(iccs)
        ...     fig.savefig(savedir / "iccs_update_timewindow-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Interactively adjusting the cross-correlation time window on the ICCS stack.](../../../images/sybil/iccs_update_timewindow.png#only-light){ loading=lazy }
        ![Interactively adjusting the cross-correlation time window on the ICCS stack.](../../../images/sybil/iccs_update_timewindow-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    _draw_stack_or_matrix(ax, iccs, context, all_seismograms, causal, use_matrix_image)
    fig.subplots_adjust(
        bottom=0.2, left=_left_margin(use_matrix_image), right=0.95, top=0.93
    )

    gs_widgets = _widget_gridspec(fig, height_ratios=[1], top=0.125, bottom=0.05)
    ax_save = fig.add_subplot(gs_widgets[0, 8:10])
    ax_cancel = fig.add_subplot(gs_widgets[0, 10:12])

    ax.set_title("Pick a new time window.")
    pending_window = [iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()]

    def handle_valid_selection(xmin: float, xmax: float) -> None:
        pending_window[0], pending_window[1] = xmin, xmax
        ax.set_title(f"Click save to set window at {xmin:.3f} to {xmax:.3f} seconds.")

    old_extents = (iccs.window_pre.total_seconds(), iccs.window_post.total_seconds())
    default_title_color = ax.title.get_color()

    def onselect(xmin: float, xmax: float) -> None:
        nonlocal old_extents
        if iccs.validate_time_window(
            pd.Timedelta(seconds=xmin), pd.Timedelta(seconds=xmax)
        ):
            old_extents = xmin, xmax
            ax.title.set_color(default_title_color)
            if ax.figure:
                ax.figure.canvas.draw_idle()
            handle_valid_selection(xmin, xmax)
        else:
            span.extents = old_extents
            ax.set_title("Invalid window choice.", color="red")
            if ax.figure:
                ax.figure.canvas.draw_idle()

    span = SpanSelector(
        ax,
        onselect,
        "horizontal",
        useblit=True,
        props={"alpha": 0.5, "facecolor": "tab:blue"},
        interactive=True,
        drag_from_anywhere=True,
    )
    span.extents = old_extents

    def on_save(_: Event) -> None:
        new_pre = pd.Timedelta(seconds=pending_window[0])
        new_post = pd.Timedelta(seconds=pending_window[1])
        # Apply the edge that narrows the window before the one that widens it:
        # a per-field validator sees a larger interim ramp otherwise and can
        # reject a pair validate_time_window already approved.
        if new_pre >= iccs.window_pre:
            iccs.window_pre = new_pre
            iccs.window_post = new_post
        else:
            iccs.window_post = new_post
            iccs.window_pre = new_pre
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(ax_save, ax_cancel, on_save, on_cancel)

    if return_fig:
        return fig, ax, (span, b_save, b_cancel)
    plt.show()
    return None
