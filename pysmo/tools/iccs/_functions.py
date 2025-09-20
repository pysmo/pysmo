"""Functions for the ICCS class."""

from __future__ import annotations
from typing import TYPE_CHECKING, overload
from datetime import timedelta
from matplotlib.colors import PowerNorm
from matplotlib.cm import ScalarMappable
from matplotlib.widgets import Cursor, Button, SpanSelector
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

if TYPE_CHECKING:
    from ._iccs import ICCS
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from typing import Any, Literal
    from matplotlib.backend_bases import Event, MouseEvent

__all__ = [
    "plot_stack",
    "plot_seismograms",
    "update_all_picks",
    "update_pick",
    "update_timewindow",
    "update_min_ccnorm",
]

IMG_CMAP = mpl.colormaps["RdBu"]
CMAP = mpl.colormaps["cool"]


def update_all_picks(iccs: ICCS, pickdelta: timedelta) -> None:
    """Update [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] in all seismograms by the same amount.

    Parameters:
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


def _plot_common_stack(
    iccs: ICCS,
    padded: bool,
    all: bool,
    figsize: tuple[float, float] = (10, 5),
    constrained: bool = True,
) -> tuple[Figure, Axes]:
    """Returns a basic stack plot for use in other plots.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
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

    seismograms_prepared = iccs.seismograms_prepared
    stack = iccs.stack
    xmin, xmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    if padded:
        ax.axvspan(xmin, xmax, color="lightgreen", alpha=0.2, label="Time Window")
        ax.axvline(xmin, color="lightgreen", linewidth=0.5, alpha=0.7)
        ax.axvline(xmax, color="lightgreen", linewidth=0.5, alpha=0.7)
        seismograms_prepared = iccs.seismograms_for_plotting
        stack = iccs.stack_for_plotting
        xmin, xmax = (
            (iccs.window_pre - iccs.plot_padding).total_seconds(),
            (iccs.window_post + iccs.plot_padding).total_seconds(),
        )

    time = np.linspace(xmin, xmax, len(stack))
    ccnorms = [
        abs(c)
        for c, _ in zip(iccs.seismograms_ccnorm, iccs.seismograms)
        if _.select or all
    ]
    seismograms_to_plot = [
        s for s, _ in zip(seismograms_prepared, iccs.seismograms) if _.select or all
    ]
    norm = PowerNorm(vmin=min(ccnorms), vmax=max(ccnorms), gamma=2)

    for seismogram_to_plot, ccnorm in zip(seismograms_to_plot, ccnorms):
        color = CMAP(norm(ccnorm))
        ax.plot(time, seismogram_to_plot.data, linewidth=0.4, color=color)
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
        ScalarMappable(norm=norm, cmap=CMAP), ax=ax, label="|Correlation coefficient|"
    )
    return fig, ax


def _plot_common_image(
    iccs: ICCS,
    padded: bool,
    all: bool,
    figsize: tuple[float, float] = (10, 5),
    constrained: bool = True,
) -> tuple[Figure, Axes, np.ndarray]:
    """Returns a basic image plot for use in other plots.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        figsize: Figure size.
        constrained: If True, the figure is constrained to the plot area.

    Returns:
        Basic image plot for use in other plots.
    """

    seismogram_matrix = np.array(
        [
            p.data
            for _, p, s in sorted(
                zip(
                    iccs.seismograms_ccnorm,
                    (
                        iccs.seismograms_for_plotting
                        if padded
                        else iccs.seismograms_prepared
                    ),
                    iccs.seismograms,
                ),
                key=lambda t: np.max(t[0]),
                reverse=True,
            )
            if s.select or all
        ]
    )

    layout = None
    if constrained:
        layout = "constrained"

    fig, ax = plt.subplots(figsize=figsize, layout=layout)

    xmin, xmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    if padded:
        # ax.axvspan(xmin, xmax, color="lightgreen", alpha=0.2, label="Time Window")
        # ax.axvline(xmin, color="lightgreen", linewidth=0.5, alpha=0.7)
        # ax.axvline(xmax, color="lightgreen", linewidth=0.5, alpha=0.7)
        xmin, xmax = (
            (iccs.window_pre - iccs.plot_padding).total_seconds(),
            (iccs.window_post + iccs.plot_padding).total_seconds(),
        )

    ax.set_ylim((0, len(seismogram_matrix)))
    ax.set_yticks([])
    plt.xlabel("Time relative to pick [s]")
    plt.ylabel("Seismograms sorted by correlation coefficient")

    plt.imshow(
        seismogram_matrix,
        extent=(xmin, xmax, 0, len(seismogram_matrix)),
        vmin=-1,
        vmax=1,
        cmap=IMG_CMAP,
        aspect="auto",
        interpolation="none",
    )

    return fig, ax, seismogram_matrix


@overload
def plot_stack(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def plot_stack(
    iccs: ICCS, padded: bool = True, all: bool = False, *, return_fig: Literal[True]
) -> tuple[Figure, Axes]: ...


def plot_stack(
    iccs: ICCS, padded: bool = True, all: bool = False, return_fig: bool = False
) -> tuple[Figure, Axes] | None:
    """Plot the ICCS stack.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
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
        >>> plt.close()
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack_padded-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack_padded.png", transparent=True)
        >>>
        ```
        -->

        ![View the stack with padding](../../../examples/figures/iccs_view_stack_padded.png#only-light){ loading=lazy }
        ![View the stack with padding](../../../examples/figures/iccs_view_stack_padded-dark.png#only-dark){ loading=lazy }

        To view the stack exactly as it is used in the cross-correlations, set
        the `padded` argument to `False`:

        ```python
        >>> plot_stack(iccs, padded=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close()
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_stack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_stack(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_view_stack.png", transparent=True)
        >>>
        ```
        -->

        ![View the stack with padding](../../../examples/figures/iccs_view_stack.png#only-light){ loading=lazy }
        ![View the stack with padding](../../../examples/figures/iccs_view_stack-dark.png#only-dark){ loading=lazy }
    """

    fig, ax = _plot_common_stack(iccs, padded, all)
    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def plot_seismograms(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def plot_seismograms(
    iccs: ICCS, padded: bool = True, all: bool = False, *, return_fig: Literal[True]
) -> tuple[Figure, Axes]: ...


def plot_seismograms(
    iccs: ICCS, padded: bool = True, all: bool = False, return_fig: bool = False
) -> tuple[Figure, Axes] | None:
    """Plot the selected ICCS seismograms as an image.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the selected seismograms as an image if `return_fig` is `True`.

    Examples:
        The default plotting mode is to pad the seismgorams beyond the time
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
        >>> plt.close()
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_seismograms(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms_padded-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_seismograms(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms_padded.png", transparent=True)
        >>>
        ```
        -->

        ![View the seismograms with padding](../../../examples/figures/iccs_plot_seismograms_padded.png#only-light){ loading=lazy }
        ![View the seismograms with padding](../../../examples/figures/iccs_plot_seismograms_padded-dark.png#only-dark){ loading=lazy }

        To view the seismograms exactly as they are used in the
        cross-correlations, set the `padded` argument to `False`:

        ```python
        >>> plot_seismograms(iccs, padded=False)
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> plt.close()
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = plot_seismograms(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = plot_seismograms(iccs, padded=False, return_fig=True)
        ...     fig.savefig(savedir / "iccs_plot_seismograms.png", transparent=True)
        >>>
        ```
        -->

        ![View the seismograms with padding](../../../examples/figures/iccs_plot_seismograms.png#only-light){ loading=lazy }
        ![View the seismograms with padding](../../../examples/figures/iccs_plot_seismograms-dark.png#only-dark){ loading=lazy }
    """

    fig, ax, _ = _plot_common_image(iccs, padded, all)
    if return_fig:
        return fig, ax

    plt.show()
    return None


@overload
def update_pick(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def update_pick(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    use_seismogram_image: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def update_pick(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: bool = False,
) -> tuple[Figure, Axes] | None:
    """Manually pick [`t1`][pysmo.tools.iccs.ICCSSeismogram.t1] and apply it to all seismograms.

    This function launches an interactive figure to manually pick a new phase
    arrival, and then apply it to all seismograms.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_seismogram_image: Use the seismogram image instead of the stack
            (see [`view_stack`][pysmo.tools.iccs.view_stack]).
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
        >>> plt.close()
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

        ![Picking a new T1](../../../examples/figures/iccs_update_pick.png#only-light){ loading=lazy }
        ![Picking a new T1](../../../examples/figures/iccs_update_pick-dark.png#only-dark){ loading=lazy }
    """

    if use_seismogram_image:
        fig, ax, _ = _plot_common_image(
            iccs, padded, all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    else:
        fig, ax = _plot_common_stack(
            iccs, padded, all, figsize=(10, 6), constrained=False
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

    class SaveOrCancel:
        def save(self, _: Event) -> None:
            pickdelta = timedelta(seconds=pick_line.get_xdata(orig=True)[0])  # type: ignore
            plt.close()
            update_all_picks(iccs, pickdelta)

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

    _ = fig.canvas.mpl_connect("motion_notify_event", on_mouse_move)  # type: ignore

    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def update_timewindow(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def update_timewindow(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    use_seismogram_image: bool = False,
    *,
    return_fig: Literal[True],
) -> tuple[Figure, Axes]: ...


def update_timewindow(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    use_seismogram_image: bool = False,
    return_fig: bool = False,
) -> tuple[Figure, Axes] | None:
    """Pick new time window limits.

    This function launches an interactive figure to pick new values for
    [`window_pre`][pysmo.tools.iccs.ICCS.window_pre] and
    [`window_post`][pysmo.tools.iccs.ICCS.window_post].

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_seismogram_image: Use the seismogram image instead of the stack
            (see [`view_stack`][pysmo.tools.iccs.view_stack]).
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
        >>> plt.close()
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

        ![Picking a new time window](../../../examples/figures/iccs_update_timewindow.png#only-light){ loading=lazy }
        ![Picking a new time window](../../../examples/figures/iccs_update_timewindow-dark.png#only-dark){ loading=lazy }
    """

    if use_seismogram_image:
        fig, ax, _ = _plot_common_image(
            iccs, padded, all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    else:
        fig, ax = _plot_common_stack(
            iccs, padded, all, figsize=(10, 6), constrained=False
        )
        fig.subplots_adjust(bottom=0.2, left=0.09, right=1.05, top=0.93)

    ax.set_title("Pick a new time window.")

    # 'old_extents' is used to revert to the last valid extents
    old_extents = (iccs.window_pre.total_seconds(), iccs.window_post.total_seconds())

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

    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def update_min_ccnorm(
    iccs: ICCS,
    padded: bool = True,
    all: bool = False,
    return_fig: Literal[False] = False,
) -> None: ...


@overload
def update_min_ccnorm(
    iccs: ICCS, padded: bool = True, all: bool = False, *, return_fig: Literal[True]
) -> tuple[Figure, Axes]: ...


def update_min_ccnorm(
    iccs: ICCS, padded: bool = True, all: bool = False, return_fig: bool = False
) -> tuple[Figure, Axes] | None:
    """Interactively pick a new [`min_ccnorm`][pysmo.tools.iccs.ICCS.min_ccnorm].

    This function launches an interactive figure to manually pick a new
    [`min_ccnorm`][pysmo.tools.iccs.ICCS.min_ccnorm], which is used when
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm with
    `autoselect` set to `True`.

    Parameters:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        padded: If True, the plot is padded on both sides of the
            time window by the amount defined in
            [`ICCS.plot_padding`][pysmo.tools.iccs.ICCS.plot_padding].
        all: If `True`, all seismograms are shown in the plot instead of the
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
        >>> plt.close()
        >>> if savedir:
        ...     plt.style.use("dark_background")
        ...     fig, _ = update_min_ccnorm(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_min_ccnorm-dark.png", transparent=True)
        ...
        ...     plt.style.use("default")
        ...     fig, _ = update_min_ccnorm(iccs, return_fig=True)
        ...     fig.savefig(savedir / "iccs_update_min_ccnorm.png", transparent=True)
        >>>
        ```
        -->

        ![Picking a new time window in stack](../../../examples/figures/iccs_update_min_ccnorm.png#only-light){ loading=lazy }
        ![Picking a new time window in stack](../../../examples/figures/iccs_update_min_ccnorm-dark.png#only-dark){ loading=lazy }
    """

    fig, ax, selected_seismogram_matrix = _plot_common_image(
        iccs, padded, all, figsize=(10, 6), constrained=False
    )
    fig.subplots_adjust(bottom=0.2, left=0.05, right=0.95, top=0.93)
    ax.set_title("Pick a new minimal cross-correlation coefficient.")

    current_ccnorms = sorted(
        i for i, _ in zip(iccs.seismograms_ccnorm, iccs.seismograms) if _.select or all
    )
    start_index = int(np.searchsorted(current_ccnorms, iccs.min_ccnorm))
    pick_line = ax.axhline(start_index, color="g", linewidth=2)
    pick_line_cursor = ax.axhline(start_index, color="g", linewidth=2, linestyle="--")

    cursor = Cursor(  # noqa: F841
        ax,
        useblit=True,
        vertOn=False,
        horizOn=False,
    )

    def snap_pickline(ydata: float) -> int:
        if ydata < 1:
            return 1
        if ydata > len(selected_seismogram_matrix) - 1:
            return len(selected_seismogram_matrix) - 1
        return round(ydata)

    def onclick(event: MouseEvent) -> Any:
        if event.inaxes is ax and event.ydata is not None:
            ydata = snap_pickline(event.ydata)
            pick_line.set_ydata((ydata, ydata))
            pick_line.set_visible(True)
            fig.canvas.draw()
            fig.canvas.flush_events()
            index = int(pick_line.get_ydata(orig=True)[0])  # type: ignore
            new_ccnorm = np.mean(current_ccnorms[index - 1 : index + 1])
            ax.set_title(f"Click save to set min_ccnorm to {new_ccnorm:.4f}")
            fig.canvas.draw_idle()

    def on_mouse_move(event: MouseEvent) -> Any:
        if event.inaxes is ax and event.ydata is not None:
            pick_line_cursor.set_visible(True)
            ydata = snap_pickline(event.ydata)
            pick_line_cursor.set_ydata((ydata, ydata))
            fig.canvas.draw_idle()
        else:
            pick_line_cursor.set_visible(False)
            fig.canvas.draw_idle()

    class IndexTracker:
        def __init__(self, ax: Axes) -> None:
            self.index = ax.get_ylim()[1]
            self.max_index = ax.get_ylim()[1]
            self.ax = ax
            self.update()

        def on_scroll(self, event: MouseEvent) -> None:
            if event.inaxes is ax:
                increment = (
                    np.ceil(self.index / 10)
                    if event.button == "up"
                    else -np.ceil(self.index / 10)
                )
                self.index = max(1, min(self.max_index, self.index + increment))
                self.update()

        def update(self) -> None:
            self.ax.set_ylim(0, self.index)
            fig.canvas.draw_idle()

    class SaveOrCancel:
        nonlocal current_ccnorms

        def save(self, _: Event) -> None:
            index = int(pick_line.get_ydata(orig=True)[0])  # type: ignore

            if index:
                iccs.min_ccnorm = np.mean(current_ccnorms[index - 1 : index + 1])
                iccs._clear_caches()
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
    tracker = IndexTracker(ax)

    _ = fig.canvas.mpl_connect("scroll_event", tracker.on_scroll)  # type: ignore
    _ = fig.canvas.mpl_connect("button_press_event", onclick)  # type: ignore
    _ = fig.canvas.mpl_connect("motion_notify_event", on_mouse_move)  # type: ignore

    if return_fig:
        return fig, ax
    plt.show()
    return None
