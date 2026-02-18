"""Functions for the ICCS class."""

from ._iccs import ICCS
from ._defaults import ICCS_DEFAULTS
from pysmo.tools.utils import to_seconds
from collections.abc import Callable
from typing import overload, Any, Literal
from datetime import timedelta
from matplotlib.colors import PowerNorm
from matplotlib.cm import ScalarMappable
from matplotlib.widgets import Cursor, Button, SpanSelector
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
import numpy as np
import matplotlib.pyplot as plt

__all__ = [
    "plot_stack",
    "plot_seismograms",
    "update_all_picks",
    "update_pick",
    "update_timewindow",
    "update_min_ccnorm",
]


def update_all_picks(iccs: ICCS, pickdelta: timedelta) -> None:
    """Update [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] in all seismograms by the same amount.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        pickdelta: delta applied to all picks.

    Raises:
        ValueError: If the new t1 is outside the valid range.
    """

    if not iccs.validate_pick(pickdelta):
        raise ValueError(
            "New t1 is outside the valid range. Consider reducing the time window."
        )

    for seismogram in iccs.seismograms:
        current_pick = seismogram.t1 or seismogram.t0
        seismogram.t1 = current_pick + pickdelta
    iccs._clear_caches()  # seismograms and stack need to be refreshed


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

    If `ramp_width` is a timedelta64 it is converted directly; if it is a
    float it is treated as a fraction of the total time window duration.
    """
    if isinstance(iccs.ramp_width, (timedelta, np.timedelta64)):
        return to_seconds(iccs.ramp_width)
    return iccs.ramp_width * to_seconds(iccs.window_post - iccs.window_pre)


def _add_save_cancel_buttons(fig: Figure, on_save: Callable[[Event], None]) -> None:
    """Add Save and Cancel buttons to an interactive figure."""

    def on_cancel(_: Event) -> None:
        plt.close()

    ax_save = fig.add_axes((0.7, 0.05, 0.1, 0.075))
    ax_cancel = fig.add_axes((0.81, 0.05, 0.1, 0.075))
    b_save = Button(ax_save, "Save", color="darkgreen", hovercolor="green")
    b_save.on_clicked(on_save)
    b_cancel = Button(ax_cancel, "Cancel", color="darkred", hovercolor="red")
    b_cancel.on_clicked(on_cancel)


def _plot_common_stack(
    iccs: ICCS,
    context: bool,
    show_all: bool,
    figsize: tuple[float, float] = (10, 5),
    constrained: bool = True,
) -> tuple[Figure, Axes]:
    """Returns a basic stack plot for use in other plots.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        figsize: Figure size.
        constrained: If True, the figure is constrained to the plot area.

    Returns:
        Basic stack plot for use in other plots.
    """

    layout = None
    if constrained:
        layout = "constrained"
    fig, ax = plt.subplots(figsize=figsize, layout=layout)

    seismograms = iccs.context_seismograms if context else iccs.cc_seismograms
    stack = iccs.context_stack if context else iccs.stack

    tmin, tmax = to_seconds(iccs.window_pre), to_seconds(iccs.window_post)

    ax.axvspan(tmin, tmax, color="lightgreen", alpha=0.2, label="Time Window")
    ax.axvline(tmin, color="lightgreen", linewidth=0.5, alpha=0.7)
    ax.axvline(tmax, color="lightgreen", linewidth=0.5, alpha=0.7)

    if context:
        tmin -= to_seconds(iccs.context_width)
        tmax += to_seconds(iccs.context_width)
    elif (taper_ramp_in_seconds := _get_taper_ramp_in_seconds(iccs)) > 0:
        tmin -= taper_ramp_in_seconds
        tmax += taper_ramp_in_seconds

    time = np.linspace(tmin, tmax, len(stack))

    mask = _make_mask(iccs, show_all)
    ccnorms = np.abs(np.compress(mask, iccs.ccnorms))
    seismogram_data = [s.data for s, m in zip(seismograms, mask) if m]

    norm = PowerNorm(vmin=np.min(ccnorms), vmax=np.max(ccnorms), gamma=2)
    colors = ICCS_DEFAULTS.stack_cmap(norm(ccnorms))

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
    fig.colorbar(
        ScalarMappable(norm=norm, cmap=ICCS_DEFAULTS.stack_cmap),
        ax=ax,
        label="|Correlation coefficient|",
    )
    return fig, ax


def _plot_common_image(
    iccs: ICCS,
    context: bool,
    show_all: bool,
    figsize: tuple[float, float] = (10, 5),
    constrained: bool = True,
) -> tuple[Figure, Axes, np.ndarray]:
    """Returns a basic image plot for use in other plots.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        show_all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        figsize: Figure size.
        constrained: If True, the figure is constrained to the plot area.

    Returns:
        Basic image plot for use in other plots.
    """

    # Assemble matrix
    seismograms = iccs.context_seismograms if context else iccs.cc_seismograms
    mask = _make_mask(iccs, show_all)
    ccnorms = np.abs(np.compress(mask, iccs.ccnorms))
    seismogram_matrix = np.array(
        [s.data for s, selected in zip(seismograms, mask) if selected]
    )

    # Sort and reverse the rows
    seismogram_matrix = seismogram_matrix[np.argsort(ccnorms)[::-1]]

    tmin, tmax = to_seconds(iccs.window_pre), to_seconds(iccs.window_post)

    if context:
        tmin -= to_seconds(iccs.context_width)
        tmax += to_seconds(iccs.context_width)
    elif (taper_ramp_in_seconds := _get_taper_ramp_in_seconds(iccs)) > 0:
        tmin -= taper_ramp_in_seconds
        tmax += taper_ramp_in_seconds

    fig, ax = plt.subplots(
        figsize=figsize, layout="constrained" if constrained else None
    )

    ax.set_ylim((0, len(seismogram_matrix)))
    ax.set_yticks([])
    ax.set_xlabel("Time relative to pick [s]")
    ax.set_ylabel("Seismograms sorted by correlation coefficient")
    ax.imshow(
        seismogram_matrix,
        extent=(tmin, tmax, 0, len(seismogram_matrix)),
        vmin=-1,
        vmax=1,
        cmap=ICCS_DEFAULTS.img_cmap,
        aspect="auto",
        interpolation="none",
    )

    return fig, ax, seismogram_matrix


@overload
def plot_stack(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def plot_stack(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def plot_stack(
    iccs: ICCS, context: bool = True, show_all: bool = False, return_fig: bool = False
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
        >>> plot_stack(iccs)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack_context-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack_context.png", transparent=True)
        >>>
        ```
        -->

        ![View the stack with context](../../../images/tools/iccs/iccs_view_stack_context.png#only-light){ loading=lazy }
        ![View the stack with context](../../../images/tools/iccs/iccs_view_stack_context-dark.png#only-dark){ loading=lazy }

        To view the stack exactly as it is used in the cross-correlations, set
        the `context` argument to `False`:

        ```python
        >>> plot_stack(iccs, context=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack.png", transparent=True)
        >>>
        ```
        -->

        ![View the stack with taper](../../../images/tools/iccs/iccs_view_stack.png#only-light){ loading=lazy }
        ![View the stack with taper](../../../images/tools/iccs/iccs_view_stack-dark.png#only-dark){ loading=lazy }
    """

    fig, ax = _plot_common_stack(iccs, context, show_all)
    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def plot_seismograms(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def plot_seismograms(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def plot_seismograms(
    iccs: ICCS, context: bool = True, show_all: bool = False, return_fig: bool = False
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
        >>> plot_seismograms(iccs)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_seismograms(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms_context-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_seismograms(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms_context.png", transparent=True)
        >>>
        ```
        -->

        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms_context.png#only-light){ loading=lazy }
        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms_context-dark.png#only-dark){ loading=lazy }

        To view the seismograms exactly as they are used in the
        cross-correlations, set the `context` argument to `False`:

        ```python
        >>> plot_seismograms(iccs, context=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_seismograms(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_seismograms(iccs, context=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms.png", transparent=True)
        >>>
        ```
        -->

        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms.png#only-light){ loading=lazy }
        ![View the seismograms with context](../../../images/tools/iccs/iccs_plot_seismograms-dark.png#only-dark){ loading=lazy }
    """

    fig, ax, _ = _plot_common_image(iccs, context, show_all)
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
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def update_pick(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def update_pick(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: bool = False,
) -> tuple[Figure, Axes] | None:
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
        >>> update_pick(iccs)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = update_pick(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_pick-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = update_pick(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_pick.png", transparent=True)
        >>>
        ```
        -->

        ![Picking a new T1](../../../images/tools/iccs/iccs_update_pick.png#only-light){ loading=lazy }
        ![Picking a new T1](../../../images/tools/iccs/iccs_update_pick-dark.png#only-dark){ loading=lazy }
    """

    if use_seismogram_image:
        fig, ax, _ = _plot_common_image(
            iccs, context, show_all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    else:
        fig, ax = _plot_common_stack(
            iccs, context, show_all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.93)

    ax.set_title("Update t1 for all seismograms.")

    pick_line = ax.axvline(0, color="g", linewidth=2)

    cursor = Cursor(  # noqa: F841
        ax, useblit=True, color="g", linewidth=2, horizOn=False, linestyle="--"
    )

    def onclick(event: MouseEvent) -> Any:
        if (
            event.inaxes is ax
            and event.xdata is not None
            and iccs.validate_pick(timedelta(seconds=event.xdata))
        ):
            pick_line.set_xdata(np.array((event.xdata, event.xdata)))
            ax.set_title(f"Click save to adjust t1 by {event.xdata:.3f} seconds.")
            fig.canvas.draw()
            fig.canvas.flush_events()

    def on_mouse_move(event: MouseEvent) -> Any:
        if event.inaxes == ax and event.xdata is not None:
            if iccs.validate_pick(timedelta(seconds=event.xdata)):
                cursor.linev.set_color("g")
            else:
                cursor.linev.set_color("r")

    def on_save(_: Event) -> None:
        pickdelta = timedelta(seconds=pick_line.get_xdata(orig=True)[0])  # type: ignore
        plt.close()
        update_all_picks(iccs, pickdelta)

    _add_save_cancel_buttons(fig, on_save)

    fig.canvas.mpl_connect("button_press_event", onclick)  # type: ignore
    fig.canvas.mpl_connect("motion_notify_event", on_mouse_move)  # type: ignore

    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def update_timewindow(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: bool = False,
) -> tuple[Figure, Axes] | None:
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
        >>> update_timewindow(iccs)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = update_timewindow(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_timewindow-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = update_timewindow(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_timewindow.png", transparent=True)
        >>>
        ```
        -->

        ![Picking a new time window](../../../images/tools/iccs/iccs_update_timewindow.png#only-light){ loading=lazy }
        ![Picking a new time window](../../../images/tools/iccs/iccs_update_timewindow-dark.png#only-dark){ loading=lazy }
    """

    if use_seismogram_image:
        fig, ax, _ = _plot_common_image(
            iccs, context, show_all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    else:
        fig, ax = _plot_common_stack(
            iccs, context, show_all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.93)

    ax.set_title("Pick a new time window.")

    # 'old_extents' is used to revert to the last valid extents
    old_extents = (to_seconds(iccs.window_pre), to_seconds(iccs.window_post))

    def onselect(xmin: float, xmax: float) -> None:
        nonlocal old_extents
        if iccs.validate_time_window(timedelta(seconds=xmin), timedelta(seconds=xmax)):
            ax.set_title(
                f"Click save to set window at {xmin:.3f} to {xmax:.3f} seconds."
            )
            old_extents = xmin, xmax
            fig.canvas.draw()
            return
        span.extents = old_extents

    span = SpanSelector(
        ax,
        onselect,
        "horizontal",
        useblit=True,
        props=dict(alpha=0.5, facecolor="tab:blue"),
        interactive=True,
        drag_from_anywhere=True,
    )

    # Set the initial extents to the existing time window
    span.extents = old_extents

    def on_save(_: Event) -> None:
        iccs.window_pre = timedelta(seconds=span.extents[0])
        iccs.window_post = timedelta(seconds=span.extents[1])
        plt.close()

    _add_save_cancel_buttons(fig, on_save)

    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def update_min_ccnorm(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def update_min_ccnorm(
    iccs: ICCS,
    context: bool = True,
    show_all: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def update_min_ccnorm(
    iccs: ICCS, context: bool = True, show_all: bool = False, return_fig: bool = False
) -> tuple[Figure, Axes] | None:
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
        Figure with the selector if `return_fig` is `True`.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_min_ccnorm
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs()
        >>> update_min_ccnorm(iccs)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close("all")
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = update_min_ccnorm(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_min_ccnorm-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = update_min_ccnorm(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_min_ccnorm.png", transparent=True)
        ...     plt.close()
        >>>
        ```
        -->

        ![Picking a new time window in stack](../../../images/tools/iccs/iccs_update_min_ccnorm.png#only-light){ loading=lazy }
        ![Picking a new time window in stack](../../../images/tools/iccs/iccs_update_min_ccnorm-dark.png#only-dark){ loading=lazy }
    """

    # If the lowest index is chosen in the gui, set the new min_ccnorm to
    # the lowest value of all seismograms multiplied by a multiplier
    _INDEX_ZERO_MULTIPLIER = 0.9

    current_ccnorms = sorted(
        i for i, s in zip(iccs.ccnorms, iccs.seismograms) if s.select or show_all
    )

    fig, ax, selected_seismogram_matrix = _plot_common_image(
        iccs, context, show_all, figsize=(10, 6), constrained=False
    )
    fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    ax.set_title("Pick a new minimal cross-correlation coefficient.")

    start_index = int(np.searchsorted(current_ccnorms, iccs.min_ccnorm))
    max_index = len(selected_seismogram_matrix) - 1

    pick_line = ax.axhline(start_index, color="g", linewidth=2)
    pick_line_cursor = ax.axhline(start_index, color="g", linewidth=2, linestyle="--")

    def snap_ydata(ydata: float) -> int:
        return max(0, round(min(ydata, max_index)))

    def calc_ccnorm(pick_line: Line2D) -> float | np.floating:
        # NOTE: the pick_line ydata should already be a round number, but
        # mypy complains without it.
        index = round(pick_line.get_ydata()[0], 0)  # type: ignore
        if index == 0:
            return _INDEX_ZERO_MULTIPLIER * current_ccnorms[0]
        return np.mean(current_ccnorms[index - 1 : index + 1])

    def onclick(event: MouseEvent) -> Any:
        if event.inaxes is ax and event.ydata is not None:
            ydata = snap_ydata(event.ydata)
            pick_line.set_ydata((ydata, ydata))
            pick_line.set_visible(True)
            fig.canvas.draw()
            fig.canvas.flush_events()
            ax.set_title(
                f"Click save to set min_ccnorm to {calc_ccnorm(pick_line):.4f}"
            )
            fig.canvas.draw_idle()

    def on_mouse_move(event: MouseEvent) -> Any:
        if event.inaxes is ax and event.ydata is not None:
            ydata = snap_ydata(event.ydata)
            pick_line_cursor.set_ydata((ydata, ydata))
            pick_line_cursor.set_visible(True)
            fig.canvas.draw_idle()
        else:
            pick_line_cursor.set_visible(False)
            fig.canvas.draw_idle()

    class ScrollIndexTracker:
        def __init__(self, ax: Axes) -> None:
            self.scroll_index = ax.get_ylim()[1]
            self.max_scroll_index = ax.get_ylim()[1]
            self.ax = ax
            self.update()

        def on_scroll(self, event: MouseEvent) -> None:
            if event.inaxes is ax:
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
            fig.canvas.draw_idle()

    def on_save(_: Event) -> None:
        iccs.min_ccnorm = calc_ccnorm(pick_line)
        iccs._clear_caches()
        plt.close()

    Cursor(ax, useblit=True, vertOn=False, horizOn=False)
    _add_save_cancel_buttons(fig, on_save)
    tracker = ScrollIndexTracker(ax)

    fig.canvas.mpl_connect("scroll_event", tracker.on_scroll)  # type: ignore
    fig.canvas.mpl_connect("button_press_event", onclick)  # type: ignore
    fig.canvas.mpl_connect("motion_notify_event", on_mouse_move)  # type: ignore

    if return_fig:
        return fig, ax
    plt.show()
    return None
