"""Extra plotting functions for the ICCS module.

These functions provide additional plotting capabilities for the ICCS module.
They are generally not meant to be consumed directly.
Instead, use the higher-level plotting functions (e.g., `plot_stack`, `update_pick`)
available directly from the `pysmo.tools.iccs` namespace, which provide a more
integrated and user-friendly experience.

This module exposes lower-level drawing primitives (`draw_common_stack`,
`draw_common_image`) for advanced users who wish to customize their plotting
workflows.
"""

import numpy as np
import matplotlib.pyplot as plt
from ._iccs import ICCS
from ._defaults import IccsDefaults
from collections.abc import Callable
from typing import overload, Literal
from pandas import Timedelta
from matplotlib.colors import PowerNorm
from matplotlib.cm import ScalarMappable
from matplotlib.widgets import Cursor, Button, SpanSelector
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent

__all__ = [
    "plot_seismograms",
    "plot_stack",
    "update_min_ccnorm",
    "update_pick",
    "update_timewindow",
    "draw_common_stack",
    "draw_common_image",
]


def _make_mask(iccs: ICCS, show_all: bool) -> list[bool]:
    """Return a list of booleans for selecting the data to use in the plots.

    Args:
        iccs: Instance of the ICCS class.
        show_all: If `True`, create mask for all seismograms instead of selected
            ones only (effectively returns a list of True for all seismograms).

    Returns:
        List of booleans for selecting the data to use in the plots.
    """

    if show_all:
        return [True] * len(iccs.seismograms)

    return [s.select for s in iccs.seismograms]


def _get_taper_ramp_in_seconds(iccs: ICCS) -> float:
    """Return the taper ramp width in seconds.

    If `ramp_width` is a Timedelta it is converted directly; if it is a
    float it is treated as a fraction of the total time window duration.
    """
    if isinstance(iccs.ramp_width, Timedelta):
        return iccs.ramp_width.total_seconds()
    return iccs.ramp_width * (iccs.window_post - iccs.window_pre).total_seconds()


def _add_save_cancel_buttons(
    fig: Figure,
    on_save: Callable[[Event], None],
    on_cancel: Callable[[Event], None],
) -> tuple[Button, Button]:
    """Add Save and Cancel buttons to an interactive figure.

    Returns:
        Tuple of (save_button, cancel_button). Must be stored to prevent garbage collection.
    """
    ax_save = fig.add_axes((0.7, 0.05, 0.1, 0.075))
    ax_cancel = fig.add_axes((0.81, 0.05, 0.1, 0.075))
    b_save = Button(ax_save, "Save", color="darkgreen", hovercolor="green")
    b_save.on_clicked(on_save)
    b_cancel = Button(ax_cancel, "Cancel", color="darkred", hovercolor="red")
    b_cancel.on_clicked(on_cancel)

    return b_save, b_cancel


class _ScrollIndexTracker:
    """Helper class to track scrolling for the min_ccnorm picker."""

    def __init__(self, ax: Axes, fig: Figure) -> None:
        self.scroll_index = ax.get_ylim()[1]
        self.max_scroll_index = ax.get_ylim()[1]
        self.ax = ax
        self.fig = fig
        self.update()

    def on_scroll(self, event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if event.inaxes is self.ax:
            increment = (
                np.ceil(self.scroll_index / 10)
                if event.button == "up"
                else -np.ceil(self.scroll_index / 10)
            )
            self.scroll_index = max(
                1, min(self.max_scroll_index, self.scroll_index + increment)
            )
            self.update()

    def update(self) -> None:
        self.ax.set_ylim(0, self.scroll_index)
        self.fig.canvas.draw_idle()


# ==============================================================================
# PURE DRAWING & LOGIC HELPERS (REUSABLE BY QT)
# ==============================================================================


def draw_common_stack(ax: Axes, iccs: ICCS, context: bool, show_all: bool) -> None:
    """Returns a basic stack plot for use in other plots.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
    """

    seismograms = iccs.context_seismograms if context else iccs.cc_seismograms
    stack = iccs.context_stack if context else iccs.stack

    tmin, tmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    ax.axvspan(tmin, tmax, color="lightgreen", alpha=0.2, label="Time Window")
    ax.axvline(tmin, color="lightgreen", linewidth=0.5, alpha=0.7)
    ax.axvline(tmax, color="lightgreen", linewidth=0.5, alpha=0.7)

    if context:
        tmin -= iccs.context_width.total_seconds()
        tmax += iccs.context_width.total_seconds()
    elif (taper_ramp_in_seconds := _get_taper_ramp_in_seconds(iccs)) > 0:
        tmin -= taper_ramp_in_seconds
        tmax += taper_ramp_in_seconds

    time = np.linspace(tmin, tmax, len(stack.data))

    mask = _make_mask(iccs, show_all)
    ccnorms = np.abs(np.compress(mask, iccs.ccnorms))
    seismogram_data = [s.data for s, m in zip(seismograms, mask) if m]

    norm = PowerNorm(vmin=np.min(ccnorms), vmax=np.max(ccnorms), gamma=2)
    colors = IccsDefaults.stack_cmap(norm(ccnorms))

    for data, color in zip(seismogram_data, colors):
        ax.plot(time, data, linewidth=0.4, color=color)
    ax.plot(
        time,
        stack.data,
        color=ax.spines["bottom"].get_edgecolor(),
        linewidth=2,
        label="Stack",
    )
    ax.set_ylabel("Normalised amplitude")
    ax.set_xlabel("Time relative to pick [s]")
    ax.set_xlim(tmin, tmax)
    ax.legend(loc="upper left")

    fig = ax.get_figure()
    if fig:
        fig.colorbar(
            ScalarMappable(norm=norm, cmap=IccsDefaults.stack_cmap),
            ax=ax,
            label="|Correlation coefficient|",
        )


def draw_common_image(
    ax: Axes, iccs: ICCS, context: bool, show_all: bool
) -> np.ndarray:
    """Returns a basic image plot for use in other plots.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.

    Returns:
        Sorted seismogram matrix used for the plot.
    """

    seismograms = iccs.context_seismograms if context else iccs.cc_seismograms
    mask = _make_mask(iccs, show_all)
    ccnorms = np.abs(np.compress(mask, iccs.ccnorms))
    seismogram_matrix = np.array(
        [s.data for s, selected in zip(seismograms, mask) if selected]
    )

    seismogram_matrix = seismogram_matrix[np.argsort(ccnorms)[::-1]]

    tmin, tmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    if context:
        tmin -= iccs.context_width.total_seconds()
        tmax += iccs.context_width.total_seconds()
    elif (taper_ramp_in_seconds := _get_taper_ramp_in_seconds(iccs)) > 0:
        tmin -= taper_ramp_in_seconds
        tmax += taper_ramp_in_seconds

    ax.set_ylim((0, len(seismogram_matrix)))
    ax.set_yticks([])
    ax.set_xlabel("Time relative to pick [s]")
    ax.set_ylabel("Seismograms sorted by correlation coefficient")
    ax.imshow(
        seismogram_matrix,
        extent=(tmin, tmax, 0, len(seismogram_matrix)),
        vmin=-1,
        vmax=1,
        cmap=IccsDefaults.img_cmap,
        aspect="auto",
        interpolation="none",
    )

    return seismogram_matrix


def _setup_phase_picker(
    ax: Axes, iccs: ICCS, on_valid_pick: Callable[[float], None]
) -> tuple[Cursor, Line2D]:
    """Configures a Cursor and Pick Line with validation logic."""
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
            and iccs.validate_pick(Timedelta(seconds=event.xdata))
        ):
            pick_line.set_xdata(np.array((event.xdata, event.xdata)))
            on_valid_pick(event.xdata)
            if ax.figure:
                ax.figure.canvas.draw()
                ax.figure.canvas.flush_events()

    def on_mouse_move(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if event.inaxes == ax and event.xdata is not None:
            is_valid = iccs.validate_pick(Timedelta(seconds=event.xdata))
            cursor.linev.set_color("g" if is_valid else "r")

    if isinstance(ax.figure, Figure):
        ax.figure.canvas.mpl_connect("button_press_event", onclick)
        ax.figure.canvas.mpl_connect("motion_notify_event", on_mouse_move)

    return cursor, pick_line


def _setup_timewindow_picker(
    ax: Axes, iccs: ICCS, on_valid_selection: Callable[[float, float], None]
) -> SpanSelector:
    """Configures a SpanSelector with validation logic."""
    old_extents = (iccs.window_pre.total_seconds(), iccs.window_post.total_seconds())

    def onselect(xmin: float, xmax: float) -> None:
        nonlocal old_extents
        if iccs.validate_time_window(Timedelta(seconds=xmin), Timedelta(seconds=xmax)):
            old_extents = xmin, xmax
            on_valid_selection(xmin, xmax)
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
        props=dict(alpha=0.5, facecolor="tab:blue"),
        interactive=True,
        drag_from_anywhere=True,
    )
    span.extents = old_extents
    return span


def _setup_ccnorm_picker(
    ax: Axes,
    iccs: ICCS,
    show_all: bool,
    max_index: int,
    on_valid_pick: Callable[[float], None],
) -> tuple[Cursor, Line2D, _ScrollIndexTracker]:
    """Configures a Cursor and Pick Line with snapping logic for ccnorm selection."""
    current_ccnorms = sorted(
        i for i, s in zip(iccs.ccnorms, iccs.seismograms) if s.select or show_all
    )

    start_index = int(np.searchsorted(current_ccnorms, iccs.min_ccnorm))

    pick_line = ax.axhline(start_index, color="g", linewidth=2)
    pick_line_cursor = ax.axhline(start_index, color="g", linewidth=2, linestyle="--")

    def snap_ydata(ydata: float) -> int:
        return max(0, round(min(ydata, max_index)))

    def calc_ccnorm(line: Line2D) -> float:
        index = round(line.get_ydata()[0], 0)  # type: ignore
        if index == 0:
            return IccsDefaults.index_zero_multiplier * current_ccnorms[0]
        return float(np.mean(current_ccnorms[index - 1 : index + 1]))

    def onclick(event: Event) -> None:
        if not isinstance(event, MouseEvent):
            return
        if event.inaxes is ax and event.ydata is not None:
            ydata = snap_ydata(event.ydata)
            pick_line.set_ydata((ydata, ydata))
            pick_line.set_visible(True)
            on_valid_pick(calc_ccnorm(pick_line))
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

    return cursor, pick_line, tracker


# ==============================================================================
# CLI ADAPTERS (WINDOW MANAGERS)
# ==============================================================================


@overload
def plot_stack(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes]: ...


@overload
def plot_stack(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def plot_stack(
    iccs: ICCS, context: bool = True, show_all: bool = False, return_fig: bool = True
) -> tuple[Figure, Axes] | None:
    """Plot the ICCS stack.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the stack with the seismograms if `return_fig` is `True`.

    Examples:
        The default plotting mode is to pad the stack beyond the time window
        used for the cross-correlations (highlighted in light green). This is
        useful particularly useful for narrow time windows. Note that because
        of the padding, the displayed stack isn't exactly what is used for the
        cross-correlations.

        ```python
        >>> from pysmo.tools.iccs import ICCS, plot_stack
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax = plot_stack(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        ![View the stack with context](../../../images/tools/iccs/iccs_view_stack_context.png#only-light){ loading=lazy }
        ![View the stack with context](../../../images/iccs/iccs_view_stack_context-dark.png#only-dark){ loading=lazy }

        To view the stack exactly as it is used in the cross-correlations, set
        the `context` argument to `False`:

        ```python
        >>> fig, ax = plot_stack(iccs, context=False)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        ![View the stack with taper](../../../images/tools/iccs/iccs_view_stack.png#only-light){ loading=lazy }
        ![View the stack with taper](../../../images/tools/iccs/iccs_view_stack-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    draw_common_stack(ax, iccs, context, show_all)
    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def plot_seismograms(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes]: ...


@overload
def plot_seismograms(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def plot_seismograms(
    iccs: ICCS, context: bool = True, show_all: bool = False, return_fig: bool = True
) -> tuple[Figure, Axes] | None:
    """Plot the selected ICCS seismograms as an image.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the selected seismograms as an image if `return_fig` is `True`.

    Examples:
        The default plotting mode is to pad the seismograms beyond the time
        window used for the cross-correlations. This is particularly useful
        for narrow time windows.

        ```python
        >>> from pysmo.tools.iccs import ICCS, plot_seismograms
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax = plot_seismograms(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms_context.png#only-light){ loading=lazy }
        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms_context-dark.png#only-dark){ loading=lazy }

        To view the seismograms exactly as they are used in the
        cross-correlations, set the `context` argument to `False`:

        ```python
        >>> fig, ax = plot_seismograms(iccs, context=False)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms.png#only-light){ loading=lazy }
        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    draw_common_image(ax, iccs, context, show_all)
    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def update_pick(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes, tuple[Cursor, Line2D, Button, Button]]: ...


@overload
def update_pick(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_pick(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: bool = True,
) -> tuple[Figure, Axes, tuple[Cursor, Line2D, Button, Button]] | None:
    """Manually pick [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] and apply it to all seismograms.

    This function launches an interactive figure to manually pick a new phase
    arrival, and then apply it to all seismograms.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_seismogram_image: Use the
            [seismogram image][pysmo.tools.iccs.plot_seismograms]
            instead of the [stack][pysmo.tools.iccs.plot_stack]).
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

        ![Picking a new T1](../../../images/tools/iccs/iccs_update_pick.png#only-light){ loading=lazy }
        ![Picking a new T1](../../../images/tools/iccs/iccs_update_pick-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    if use_seismogram_image:
        draw_common_image(ax, iccs, context, show_all)
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    else:
        draw_common_stack(ax, iccs, context, show_all)
        fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.93)

    ax.set_title("Update t1 for all seismograms.")
    pending_pick = [0.0]

    def handle_valid_pick(xdata: float) -> None:
        pending_pick[0] = xdata
        ax.set_title(f"Click save to adjust t1 by {xdata:.3f} seconds.")

    cursor, pick_line = _setup_phase_picker(ax, iccs, handle_valid_pick)

    def on_save(_: Event) -> None:
        iccs.update_all_picks(Timedelta(seconds=pending_pick[0]))
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(fig, on_save, on_cancel)

    if return_fig:
        return fig, ax, (cursor, pick_line, b_save, b_cancel)
    plt.show()
    return None


@overload
def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes, tuple[SpanSelector, Button, Button]]: ...


@overload
def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: bool = True,
) -> tuple[Figure, Axes, tuple[SpanSelector, Button, Button]] | None:
    """Pick new time window limits.

    This function launches an interactive figure to pick new values for
    [`window_pre`][pysmo.tools.iccs.ICCS.window_pre] and
    [`window_post`][pysmo.tools.iccs.ICCS.window_post].

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_seismogram_image: Use the
            [seismogram image][pysmo.tools.iccs.plot_seismograms]
            instead of the [stack][pysmo.tools.iccs.plot_stack]).
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the stack with the picker if `return_fig` is `True`.

    Info:
        The new time window may not be chosen such that the pick lies
        outside the the window. The picker will therefore automatically correct
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

        ![Picking a new time window](../../../images/tools/iccs/iccs_update_timewindow.png#only-light){ loading=lazy }
        ![Picking a new time window](../../../images/tools/iccs/iccs_update_timewindow-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    if use_seismogram_image:
        draw_common_image(ax, iccs, context, show_all)
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    else:
        draw_common_stack(ax, iccs, context, show_all)
        fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.93)

    ax.set_title("Pick a new time window.")
    pending_window = [iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()]

    def handle_valid_selection(xmin: float, xmax: float) -> None:
        pending_window[0], pending_window[1] = xmin, xmax
        ax.set_title(f"Click save to set window at {xmin:.3f} to {xmax:.3f} seconds.")

    span = _setup_timewindow_picker(ax, iccs, handle_valid_selection)

    def on_save(_: Event) -> None:
        iccs.window_pre = Timedelta(seconds=pending_window[0])
        iccs.window_post = Timedelta(seconds=pending_window[1])
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(fig, on_save, on_cancel)

    if return_fig:
        return fig, ax, (span, b_save, b_cancel)
    plt.show()
    return None


@overload
def update_min_ccnorm(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[
    Figure, Axes, tuple[Cursor, Line2D, Button, Button, _ScrollIndexTracker]
]: ...


@overload
def update_min_ccnorm(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_min_ccnorm(
    iccs: ICCS, context: bool = True, show_all: bool = False, return_fig: bool = True
) -> (
    tuple[
        Figure,
        Axes,
        tuple[Cursor, Line2D, Button, Button, _ScrollIndexTracker],
    ]
    | None
):
    """Interactively pick a new [`min_ccnorm`][pysmo.tools.iccs.ICCS.min_ccnorm].

    This function launches an interactive figure to manually pick a new
    [`min_ccnorm`][pysmo.tools.iccs.ICCS.min_ccnorm], which is used when
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm with
    `autoselect` set to `True`.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure with the selector widgets if `return_fig` is `True`.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_min_ccnorm
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs()
        >>> fig, ax, widgets = update_min_ccnorm(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        ![Picking a new time window in stack](../../../images/tools/iccs/iccs_update_min_ccnorm.png#only-light){ loading=lazy }
        ![Picking a new time window in stack](../../../images/tools/iccs/iccs_update_min_ccnorm-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    matrix = draw_common_image(ax, iccs, context, show_all)
    fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)

    ax.set_title("Pick a new minimal cross-correlation coefficient.")
    pending_val = [iccs.min_ccnorm]

    def handle_valid_pick(new_val: float) -> None:
        pending_val[0] = new_val
        ax.set_title(f"Click save to set min_ccnorm to {new_val:.4f}")

    cursor, pick_line, tracker = _setup_ccnorm_picker(
        ax, iccs, show_all, len(matrix) - 1, handle_valid_pick
    )

    def on_save(_: Event) -> None:
        iccs.min_ccnorm = pending_val[0]
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(fig, on_save, on_cancel)

    if return_fig:
        return fig, ax, (cursor, pick_line, b_save, b_cancel, tracker)
    plt.show()
    return None
