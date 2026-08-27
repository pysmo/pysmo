"""Extra plotting functions for the ICCS module.

Most of this module's contents are internal helpers for the higher-level
plotting functions (e.g. `plot_stack`, `update_pick`) exposed from the
`pysmo.tools.iccs` namespace, and are not meant to be used directly. The
exceptions are `draw_common_stack` and `draw_common_matrix_image`, lower-level
drawing primitives exposed for users who wish to customise their own plotting
workflows.
"""

from collections import OrderedDict
from collections.abc import Callable
from typing import Literal, overload

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent, TimerBase
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.colors import PowerNorm
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.widgets import (
    Button,
    CheckButtons,
    Cursor,
    RadioButtons,
    Slider,
    SpanSelector,
)

from pysmo.tools.signal import causal_band

from ._defaults import IccsDefaults
from ._iccs import ICCS

__all__ = [
    "plot_matrix_image",
    "plot_stack",
    "update_bandpass",
    "update_min_cc",
    "update_pick",
    "update_timewindow",
    "draw_common_stack",
    "draw_common_matrix_image",
]


def _make_mask(iccs: ICCS, all_seismograms: bool) -> list[bool]:
    """Return a list of booleans for selecting the data to use in the plots.

    Args:
        iccs: Instance of the ICCS class.
        all_seismograms: If `True`, create mask for all seismograms instead of selected
            ones only (effectively returns a list of True for all seismograms).

    Returns:
        List of booleans for selecting the data to use in the plots.
    """

    if all_seismograms:
        return [True] * len(iccs.seismograms)

    return [s.select for s in iccs.seismograms]


def _variant_suffix(apply: bool, causal: bool) -> str:
    """Return a label suffix identifying the causal/zero-phase filter variant.

    Only shown when `apply` is `True` — when it's `False`, causal and
    zero-phase preparation are identical, so labelling one as "(causal)"
    would be misleading.

    Takes `apply` explicitly rather than reading `ICCS.bandpass_apply`
    directly: `update_bandpass`'s live preview only writes
    `iccs.bandpass_apply` on a cache miss (see `_update_matrix`/
    `_update_stack`), so it can lag behind the widget's actual current
    state on a cache hit — callers there must pass the freshly-read
    checkbox state instead of the (possibly stale) `iccs` attribute.
    """
    if not apply:
        return ""
    return " (causal)" if causal else " (zero-phase)"


def _apply_bandpass_params(
    iccs: ICCS, apply: bool, fmin: float, fmax: float, corners: int
) -> bool:
    """Apply new bandpass_apply/bandpass_fmin/bandpass_fmax/corners without spurious rejections.

    ICCS's per-field validators check each new value against the *other*
    fields' current values, so setting bandpass_fmin, bandpass_fmax, and
    corners one at a time in a fixed order can spuriously reject a
    combination that's valid once all three are set together (e.g. a step
    checked against a stale, narrower band left over from a previous
    update).

    Avoided by validating the full target via
    [`causal_band`][pysmo.tools.signal.causal_band] first, then writing
    fields moving in the *permissive* direction (`bandpass_fmin` down,
    `bandpass_fmax` up, `corners` up) before the *restrictive* ones — a
    permissive write can only make an already-valid combination more valid,
    and by the time a restrictive field is written the others are already
    at their validated target, so it succeeds too.

    Returns:
        `True` if the target combination was valid and applied (cache
        cleared). `False` if invalid — `iccs` is left unchanged.
    """
    if fmin >= fmax:
        return False
    try:
        causal_band(fmin, fmax, corners)
    except ValueError:
        return False

    iccs.bandpass_apply = apply

    fields = [
        ("bandpass_fmin", fmin, fmin <= iccs.bandpass_fmin),
        ("bandpass_fmax", fmax, fmax >= iccs.bandpass_fmax),
        ("corners", corners, corners >= iccs.corners),
    ]
    for name, value, permissive in sorted(fields, key=lambda f: not f[2]):
        setattr(iccs, name, value)

    return True


def _left_margin(use_matrix_image: bool) -> float:
    """Return the main axes' left margin for the given rendering mode.

    The matrix image has no numeric y-tick labels (`ax.set_yticks([])` in
    `_draw_matrix_image_initial`), so it needs less left margin than the
    stack plot, which does. Centralised here rather than repeated as a
    magic number at every `fig.subplots_adjust` call site.
    """
    return 0.05 if use_matrix_image else 0.09


def _draw_stack_or_matrix(
    ax: Axes,
    iccs: ICCS,
    context: bool,
    all_seismograms: bool,
    causal: bool,
    use_matrix_image: bool,
) -> None:
    """Draw the stack or matrix-image plot.

    For dialogs that don't need the returned artist references back (i.e.
    no live-updating preview — see `update_bandpass` for the one dialog
    that does and can't use this).
    """
    if use_matrix_image:
        draw_common_matrix_image(ax, iccs, context, all_seismograms, causal)
    else:
        draw_common_stack(ax, iccs, context, all_seismograms, causal)


def _widget_gridspec(
    fig: Figure,
    height_ratios: list[float],
    top: float,
    bottom: float,
    hspace: float = 0.8,
) -> GridSpec:
    """Build a GridSpec for the widget area below a dialog's main plot axes.

    Each entry in `height_ratios` becomes its own row (as *relative* weights
    within the `[bottom, top]` span, matplotlib's normal `GridSpec` meaning —
    not absolute fractions), stacked top-to-bottom — the last entry is
    conventionally the Save/Cancel buttons row. Rows are separate GridSpec
    cells, so widgets placed in different rows can never visually overlap
    (unlike hand-placed `fig.add_axes` rectangles, which have no such
    guarantee), regardless of how many rows a given dialog needs. Twelve
    columns give enough resolution to place narrower widgets (e.g. Save/
    Cancel side by side) within a row without needing a different `ncols`
    per dialog.
    """
    return fig.add_gridspec(
        nrows=len(height_ratios),
        ncols=12,
        height_ratios=height_ratios,
        hspace=hspace,
        left=0.1,
        right=0.95,
        top=top,
        bottom=bottom,
    )


def _add_save_cancel_buttons(
    ax_save: Axes,
    ax_cancel: Axes,
    on_save: Callable[[Event], None],
    on_cancel: Callable[[Event], None],
) -> tuple[Button, Button]:
    """Add Save and Cancel buttons to the given axes.

    Returns:
        Tuple of (save_button, cancel_button). Must be stored to prevent garbage collection.
    """
    b_save = Button(ax_save, "Save", color="darkgreen", hovercolor="green")
    b_save.on_clicked(on_save)
    b_cancel = Button(ax_cancel, "Cancel", color="darkred", hovercolor="red")
    b_cancel.on_clicked(on_cancel)

    return b_save, b_cancel


class _ScrollIndexTracker:
    """Helper class to track scrolling for the min_cc picker."""

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
# PURE DRAWING & LOGIC HELPERS
# ==============================================================================


def _draw_stack_initial(
    ax: Axes, iccs: ICCS, context: bool, all_seismograms: bool, causal: bool = False
) -> tuple[list[Line2D], Line2D, ScalarMappable, Colorbar]:
    """Draw the stack plot and return artist references for live updates.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.

    Returns:
        Tuple of (seis_lines, stack_line, scalar_mappable, colorbar).
    """

    if context:
        seismograms = (
            iccs.context_seismograms_causal if causal else iccs.context_seismograms
        )
        stack = iccs.context_stack_causal if causal else iccs.context_stack
    else:
        seismograms = iccs.cc_seismograms_causal if causal else iccs.cc_seismograms
        stack = iccs.stack_causal if causal else iccs.stack

    tmin, tmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    ax.axvspan(tmin, tmax, color="lightgreen", alpha=0.2, label="Time Window")
    ax.axvline(tmin, color="lightgreen", linewidth=0.5, alpha=0.7)
    ax.axvline(tmax, color="lightgreen", linewidth=0.5, alpha=0.7)

    if context:
        tmin -= iccs.context_width.total_seconds()
        tmax += iccs.context_width.total_seconds()
    elif (taper_ramp_in_seconds := iccs.ramp_width_timedelta.total_seconds()) > 0:
        tmin -= taper_ramp_in_seconds
        tmax += taper_ramp_in_seconds

    time = np.linspace(tmin, tmax, len(stack.data))

    mask = _make_mask(iccs, all_seismograms)
    ccs = np.abs(np.compress(mask, iccs.ccs))
    seismogram_data = [s.data for s, m in zip(seismograms, mask) if m]

    norm = PowerNorm(vmin=np.min(ccs), vmax=np.max(ccs), gamma=2)
    colors = IccsDefaults.stack_cmap(norm(ccs))

    seis_lines = [
        ax.plot(time, data, linewidth=0.4, color=color)[0]
        for data, color in zip(seismogram_data, colors)
    ]
    (stack_line,) = ax.plot(
        time,
        stack.data,
        color=ax.spines["bottom"].get_edgecolor(),
        linewidth=2,
        label="Stack",
    )
    ax.set_ylabel(f"Normalised amplitude{_variant_suffix(iccs.bandpass_apply, causal)}")
    ax.set_xlabel("Time relative to pick [s]")
    ax.set_xlim(tmin, tmax)
    ax.legend(loc="upper left")

    fig = ax.get_figure()
    assert fig is not None
    scalar_mappable = ScalarMappable(norm=norm, cmap=IccsDefaults.stack_cmap)
    # Explicit fraction/pad reserve a fixed width for the colorbar regardless
    # of the caller's `right` margin, so callers can use the same `right`
    # for both the stack and matrix-image branches instead of needing to
    # separately compensate for the colorbar's shrink each time.
    colorbar = fig.colorbar(
        scalar_mappable,
        ax=ax,
        # ccs is always zero-phase-based, regardless of the preview toggle.
        label=f"|Correlation coefficient|{_variant_suffix(iccs.bandpass_apply, False)}",
        fraction=0.05,
        pad=0.02,
    )

    return seis_lines, stack_line, scalar_mappable, colorbar


def draw_common_stack(
    ax: Axes, iccs: ICCS, context: bool, all_seismograms: bool, causal: bool = False
) -> None:
    """Return a basic stack plot for use in other plots.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.
    """
    _draw_stack_initial(ax, iccs, context, all_seismograms, causal)


def _draw_matrix_image_initial(
    ax: Axes, iccs: ICCS, context: bool, all_seismograms: bool, causal: bool = False
) -> tuple[AxesImage, np.ndarray]:
    """Draw the matrix image plot and return artist references for live updates.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.

    Returns:
        Tuple of (axes_image, seismogram_matrix).
    """

    if context:
        seismograms = (
            iccs.context_seismograms_causal if causal else iccs.context_seismograms
        )
    else:
        seismograms = iccs.cc_seismograms_causal if causal else iccs.cc_seismograms
    mask = _make_mask(iccs, all_seismograms)
    ccs = np.abs(np.compress(mask, iccs.ccs))
    seismogram_matrix = np.array(
        [s.data for s, selected in zip(seismograms, mask) if selected]
    )

    seismogram_matrix = seismogram_matrix[np.argsort(ccs)[::-1]]

    tmin, tmax = iccs.window_pre.total_seconds(), iccs.window_post.total_seconds()

    ax.axvline(tmin, color="lightgreen", linewidth=0.5, alpha=0.7)
    ax.axvline(tmax, color="lightgreen", linewidth=0.5, alpha=0.7)

    if context:
        tmin -= iccs.context_width.total_seconds()
        tmax += iccs.context_width.total_seconds()
    elif (taper_ramp_in_seconds := iccs.ramp_width_timedelta.total_seconds()) > 0:
        tmin -= taper_ramp_in_seconds
        tmax += taper_ramp_in_seconds

    ax.set_ylim((0, len(seismogram_matrix)))
    ax.set_yticks([])
    ax.set_xlabel(
        f"Time relative to pick [s]{_variant_suffix(iccs.bandpass_apply, causal)}"
    )
    # Row order comes from ccs, which is always zero-phase-based.
    ax.set_ylabel(
        "Seismograms sorted by correlation coefficient"
        f"{_variant_suffix(iccs.bandpass_apply, False)}"
    )
    axes_image = ax.imshow(
        seismogram_matrix,
        extent=(tmin, tmax, 0, len(seismogram_matrix)),
        vmin=-1,
        vmax=1,
        cmap=IccsDefaults.img_cmap,
        aspect="auto",
        interpolation="none",
    )

    return axes_image, seismogram_matrix


def draw_common_matrix_image(
    ax: Axes, iccs: ICCS, context: bool, all_seismograms: bool, causal: bool = False
) -> np.ndarray:
    """Return a basic matrix image plot for use in other plots.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.

    Returns:
        Sorted seismogram matrix used for the plot.
    """
    _, seismogram_matrix = _draw_matrix_image_initial(
        ax, iccs, context, all_seismograms, causal
    )
    return seismogram_matrix


# ==============================================================================
# CLI ADAPTERS (WINDOW MANAGERS)
# ==============================================================================


@overload
def plot_stack(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes]: ...


@overload
def plot_stack(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def plot_stack(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    return_fig: bool = True,
) -> tuple[Figure, Axes] | None:
    """Plot the ICCS stack.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the stack with the seismograms if `return_fig` is `True`.

    Examples:
        The default plotting mode is to pad the stack beyond the time window
        used for the cross-correlations (highlighted in light green). This is
        particularly useful for narrow time windows. Note that because of the
        padding, the displayed stack isn't exactly what is used for the
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

        <!-- invisible-code-block: python
        ```
        >>> import matplotlib.pyplot as plt
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_context_stack.png", transparent=True)
        ...     plt.style.use("dark_background")
        ...     fig, ax = plot_stack(iccs)
        ...     fig.savefig(savedir / "iccs_context_stack-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![View the context stack](../../../images/sybil/iccs_context_stack.png#only-light){ loading=lazy }
        ![View the context stack](../../../images/sybil/iccs_context_stack-dark.png#only-dark){ loading=lazy }

        To view the stack exactly as it is used in the cross-correlations, set
        the `context` argument to `False`:

        ```python
        >>> fig, ax = plot_stack(iccs, context=False)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_cc_stack.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax = plot_stack(iccs, context=False)
        ...     fig.savefig(savedir / "iccs_cc_stack-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![View the cc stack](../../../images/sybil/iccs_cc_stack.png#only-light){ loading=lazy }
        ![View the cc stack](../../../images/sybil/iccs_cc_stack-dark.png#only-dark){ loading=lazy }

        To view the causally-filtered variant used by picking-oriented tools
        (avoiding the acausal precursor smearing a zero-phase filter
        introduces before the true onset), set `causal` to `True`:

        ```python
        >>> fig, ax = plot_stack(iccs, context=False, causal=True)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```
    """
    fig, ax = plt.subplots(figsize=(10, 5.4))
    fig.subplots_adjust(bottom=0.12, left=0.09, right=0.95, top=0.93)
    draw_common_stack(ax, iccs, context, all_seismograms, causal)
    if return_fig:
        return fig, ax
    plt.show()
    return None


@overload
def plot_matrix_image(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[Figure, Axes]: ...


@overload
def plot_matrix_image(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def plot_matrix_image(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    causal: bool = False,
    return_fig: bool = True,
) -> tuple[Figure, Axes] | None:
    """Plot the selected ICCS seismograms as a matrix image.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure of the selected seismograms as a matrix image if `return_fig` is `True`.

    Examples:
        The default plotting mode is to pad the seismograms beyond the time
        window used for the cross-correlations. This is particularly useful
        for narrow time windows.

        ```python
        >>> from pysmo.tools.iccs import ICCS, plot_matrix_image
        >>> iccs = ICCS(iccs_seismograms)
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax = plot_matrix_image(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_context_image.png", transparent=True)
        ...     plt.style.use("dark_background")
        ...     fig, ax = plot_matrix_image(iccs)
        ...     fig.savefig(savedir / "iccs_context_image-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Matrix image of context seismograms](../../../images/sybil/iccs_context_image.png#only-light){ loading=lazy }
        ![Matrix image of context seismograms](../../../images/sybil/iccs_context_image-dark.png#only-dark){ loading=lazy }

        To view the matrix image composed of seismograms as used in the
        cross-correlations, set the `context` argument to `False`:

        ```python
        >>> fig, ax = plot_matrix_image(iccs, context=False)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_cc_image.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax = plot_matrix_image(iccs, context=False)
        ...     fig.savefig(savedir / "iccs_cc_image-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![View the matrix image of cc seismograms](../../../images/sybil/iccs_cc_image.png#only-light){ loading=lazy }
        ![View the matrix image of cc seismograms](../../../images/sybil/iccs_cc_image-dark.png#only-dark){ loading=lazy }

        To view the causally-filtered variant used by picking-oriented tools
        (avoiding the acausal precursor smearing a zero-phase filter
        introduces before the true onset), set `causal` to `True`:

        ```python
        >>> fig, ax = plot_matrix_image(iccs, context=False, causal=True)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```
    """
    fig, ax = plt.subplots(figsize=(10, 5.4))
    fig.subplots_adjust(bottom=0.12, left=0.05, right=0.95, top=0.93)
    draw_common_matrix_image(ax, iccs, context, all_seismograms, causal)
    if return_fig:
        return fig, ax
    plt.show()
    return None


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
    """Manually pick [`t1`][pysmo.tools.iccs.IccsSeismogram.t1] and apply it to all seismograms.

    This function launches an interactive figure to manually pick a new phase
    arrival, and then apply it to all seismograms.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
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

        ![Picking a new T1](../../../images/sybil/iccs_update_pick.png#only-light){ loading=lazy }
        ![Picking a new T1](../../../images/sybil/iccs_update_pick-dark.png#only-dark){ loading=lazy }
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    _draw_stack_or_matrix(ax, iccs, context, all_seismograms, causal, use_matrix_image)
    fig.subplots_adjust(
        bottom=0.2, left=_left_margin(use_matrix_image), right=0.95, top=0.93
    )

    gs_widgets = _widget_gridspec(fig, height_ratios=[1], top=0.125, bottom=0.05)
    ax_save = fig.add_subplot(gs_widgets[0, 8:10])
    ax_cancel = fig.add_subplot(gs_widgets[0, 10:12])

    ax.set_title("Update t1 for all seismograms.")
    pending_pick = [0.0]

    def handle_valid_pick(xdata: float) -> None:
        pending_pick[0] = xdata
        ax.set_title(f"Click save to adjust t1 by {xdata:.3f} seconds.")

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
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
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

        ![Picking a new time window](../../../images/sybil/iccs_update_timewindow.png#only-light){ loading=lazy }
        ![Picking a new time window](../../../images/sybil/iccs_update_timewindow-dark.png#only-dark){ loading=lazy }
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
        props=dict(alpha=0.5, facecolor="tab:blue"),
        interactive=True,
        drag_from_anywhere=True,
    )
    span.extents = old_extents

    def on_save(_: Event) -> None:
        iccs.window_pre = pd.Timedelta(seconds=pending_window[0])
        iccs.window_post = pd.Timedelta(seconds=pending_window[1])
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
    """Interactively pick a new [`min_cc`][pysmo.tools.iccs.ICCS.min_cc].

    This function launches an interactive figure to manually pick a new
    [`min_cc`][pysmo.tools.iccs.ICCS.min_cc], which is used when
    [running][pysmo.tools.iccs.ICCS.__call__] the ICCS algorithm with
    `autoselect` set to `True`.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used. This is the
              default for this function — it sorts/thresholds by correlation
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

        ![Picking a new min_cc in matrix image](../../../images/sybil/iccs_update_min_cc.png#only-light){ loading=lazy }
        ![Picking a new min_cc in matrix image](../../../images/sybil/iccs_update_min_cc-dark.png#only-dark){ loading=lazy }
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

    current_ccs = sorted(
        i for i, s in zip(iccs.ccs, iccs.seismograms) if s.select or all_seismograms
    )
    start_index = int(np.searchsorted(current_ccs, iccs.min_cc))
    max_index = len(matrix) - 1

    pick_line = ax.axhline(start_index, color="g", linewidth=2)
    pick_line_cursor = ax.axhline(start_index, color="g", linewidth=2, linestyle="--")

    def snap_ydata(ydata: float) -> int:
        return max(0, round(min(ydata, max_index)))

    def calc_cc(line: Line2D) -> float:
        index = round(line.get_ydata()[0], 0)  # type: ignore
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


@overload
def update_bandpass(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[
    Figure,
    Axes,
    tuple[CheckButtons, Slider, Slider, Slider, RadioButtons, Button, Button],
]: ...


@overload
def update_bandpass(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_bandpass(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    return_fig: bool = True,
) -> (
    tuple[
        Figure,
        Axes,
        tuple[CheckButtons, Slider, Slider, Slider, RadioButtons, Button, Button],
    ]
    | None
):
    """Interactively update the bandpass filter parameters.

    This function launches an interactive figure to adjust
    [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply],
    [`bandpass_fmin`][pysmo.tools.iccs.ICCS.bandpass_fmin],
    [`bandpass_fmax`][pysmo.tools.iccs.ICCS.bandpass_fmax], and
    [`corners`][pysmo.tools.iccs.ICCS.corners] with a live preview. A radio
    button toggles the preview between the causal and zero-phase variants —
    this is UI-only, not a saved parameter, since both renderings are
    relevant while tuning rather than there being a default to pick.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: [`context_seismograms`][pysmo.tools.iccs.ICCS.context_seismograms] are used.
            - `False`: [`cc_seismograms`][pysmo.tools.iccs.ICCS.cc_seismograms] are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_matrix_image: Use the
            [matrix image][pysmo.tools.iccs.plot_matrix_image]
            instead of the [stack][pysmo.tools.iccs.plot_stack].
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure with the filter widgets if `return_fig` is `True`.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_bandpass
        >>> iccs = ICCS(iccs_seismograms)
        >>> iccs.bandpass_apply = True  # start with bandpass applied
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax, widgets = update_bandpass(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_update_bandpass.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax, widgets = update_bandpass(iccs)
        ...     fig.savefig(savedir / "iccs_update_bandpass-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Updating bandpass filter parameters](../../../images/sybil/iccs_update_bandpass.png#only-light){ loading=lazy }
        ![Updating bandpass filter parameters](../../../images/sybil/iccs_update_bandpass-dark.png#only-dark){ loading=lazy }
    """
    _orig_apply = iccs.bandpass_apply
    _orig_fmin = iccs.bandpass_fmin
    _orig_fmax = iccs.bandpass_fmax
    _orig_corners = iccs.corners

    _BANDPASS_CACHE_SIZE = 8

    def _quantise_freq(f: float, sig_figs: int = 4) -> float:
        """Round *f* to *sig_figs* significant figures for use as a cache key."""
        if f <= 0:
            return f
        magnitude = 10 ** (sig_figs - 1 - int(np.floor(np.log10(f))))
        return round(f * magnitude) / magnitude

    nyquist = 0.5 / iccs.max_delta.total_seconds()
    _freq_eps = nyquist * 1e-4  # open-bound approximation matching bandpass constraints
    _log_min = np.log(_freq_eps)
    # Use a slightly tighter upper bound near Nyquist to keep inter-slider
    # constraints safely within the global slider range.
    _log_max = np.log(nyquist - 2 * _freq_eps)

    fig, ax = plt.subplots(figsize=(10, 7.7))

    _debounce_timer: list[TimerBase | None] = [None]
    _updating: list[bool] = [False]
    update_fn: Callable[[], None]

    def _current_causal() -> bool:
        return radio.value_selected == "Causal"

    bottom_margin = 0.38 if use_matrix_image else 0.35

    if use_matrix_image:
        axes_image, _ = _draw_matrix_image_initial(
            ax, iccs, context, all_seismograms, False
        )
        fig.subplots_adjust(
            bottom=bottom_margin, left=_left_margin(True), right=0.95, top=0.93
        )
        _matrix_cache: OrderedDict[tuple[bool, float, float, bool, int], np.ndarray] = (
            OrderedDict()
        )

        def _update_matrix() -> None:
            apply = check.get_status()[0]
            fmin = max(_quantise_freq(float(np.exp(slider_fmin.val))), _freq_eps)
            fmax = min(
                _quantise_freq(float(np.exp(slider_fmax.val))), nyquist - _freq_eps
            )
            if fmin >= fmax:
                return
            causal = _current_causal()
            corners = int(slider_corners.val)
            key = (apply, fmin, fmax, causal, corners)
            if key not in _matrix_cache:
                if len(_matrix_cache) >= _BANDPASS_CACHE_SIZE:
                    _matrix_cache.popitem(last=False)
                if not _apply_bandpass_params(iccs, apply, fmin, fmax, corners):
                    return
                if context:
                    seismograms = (
                        iccs.context_seismograms_causal
                        if causal
                        else iccs.context_seismograms
                    )
                else:
                    seismograms = (
                        iccs.cc_seismograms_causal if causal else iccs.cc_seismograms
                    )
                mask = _make_mask(iccs, all_seismograms)
                ccs = np.abs(np.compress(mask, iccs.ccs))
                matrix = np.array([s.data for s, m in zip(seismograms, mask) if m])
                _matrix_cache[key] = matrix[np.argsort(ccs)[::-1]]
            else:
                _matrix_cache.move_to_end(key)
            axes_image.set_data(_matrix_cache[key])
            ax.set_xlabel(f"Time relative to pick [s]{_variant_suffix(apply, causal)}")
            ax.set_ylabel(
                "Seismograms sorted by correlation coefficient"
                f"{_variant_suffix(apply, False)}"
            )
            fig.canvas.draw_idle()

        update_fn = _update_matrix
    else:
        seis_lines, stack_line, scalar_mappable, colorbar = _draw_stack_initial(
            ax, iccs, context, all_seismograms, False
        )
        fig.subplots_adjust(
            bottom=bottom_margin, left=_left_margin(False), right=0.95, top=0.93
        )
        _stack_cache: OrderedDict[
            tuple[bool, float, float, bool, int],
            tuple[list[np.ndarray], np.ndarray, np.ndarray],
        ] = OrderedDict()

        def _update_stack() -> None:
            apply = check.get_status()[0]
            fmin = max(_quantise_freq(float(np.exp(slider_fmin.val))), _freq_eps)
            fmax = min(
                _quantise_freq(float(np.exp(slider_fmax.val))), nyquist - _freq_eps
            )
            if fmin >= fmax:
                return
            causal = _current_causal()
            corners = int(slider_corners.val)
            key = (apply, fmin, fmax, causal, corners)
            if key not in _stack_cache:
                if len(_stack_cache) >= _BANDPASS_CACHE_SIZE:
                    _stack_cache.popitem(last=False)
                if not _apply_bandpass_params(iccs, apply, fmin, fmax, corners):
                    return
                if context:
                    seismograms = (
                        iccs.context_seismograms_causal
                        if causal
                        else iccs.context_seismograms
                    )
                    stack = iccs.context_stack_causal if causal else iccs.context_stack
                else:
                    seismograms = (
                        iccs.cc_seismograms_causal if causal else iccs.cc_seismograms
                    )
                    stack = iccs.stack_causal if causal else iccs.stack
                mask = _make_mask(iccs, all_seismograms)
                ccs = np.abs(np.compress(mask, iccs.ccs))
                seis_data = [s.data.copy() for s, m in zip(seismograms, mask) if m]
                _stack_cache[key] = (seis_data, stack.data.copy(), ccs)
            else:
                _stack_cache.move_to_end(key)
            seis_data, stack_data, ccs = _stack_cache[key]
            new_norm = PowerNorm(vmin=np.min(ccs), vmax=np.max(ccs), gamma=2)
            new_colors = IccsDefaults.stack_cmap(new_norm(ccs))
            for line, data, color in zip(seis_lines, seis_data, new_colors):
                line.set_ydata(data)
                line.set_color(color)
            stack_line.set_ydata(stack_data)
            scalar_mappable.set_norm(new_norm)
            colorbar.update_normal(scalar_mappable)
            colorbar.set_label(
                f"|Correlation coefficient|{_variant_suffix(apply, False)}"
            )
            ax.set_ylabel(f"Normalised amplitude{_variant_suffix(apply, causal)}")
            fig.canvas.draw_idle()

        update_fn = _update_stack

    ax.set_title("Update bandpass filter parameters.")

    gs_widgets = _widget_gridspec(
        fig, height_ratios=[1, 1, 1, 1.8], top=bottom_margin - 0.07, bottom=0.02
    )
    ax_fmin = fig.add_subplot(gs_widgets[0, 1:11])
    ax_fmax = fig.add_subplot(gs_widgets[1, 1:11])
    ax_corners = fig.add_subplot(gs_widgets[2, 1:11])
    ax_check = fig.add_subplot(gs_widgets[3, 1:4])
    ax_radio = fig.add_subplot(gs_widgets[3, 4:8])
    ax_save = fig.add_subplot(gs_widgets[3, 8:10])
    ax_cancel = fig.add_subplot(gs_widgets[3, 10:12])

    # Align left edges with the main plot's y-axis, not the grid's column 1.
    check_pos = ax_check.get_position()
    shift = _left_margin(use_matrix_image) - check_pos.x0
    ax_check.set_position(check_pos.translated(shift, 0))
    radio_pos = ax_radio.get_position()
    ax_radio.set_position(radio_pos.translated(shift, 0))

    _fg = plt.rcParams.get("text.color", "black")
    ax_check.set_frame_on(True)
    for spine in ax_check.spines.values():
        spine.set_edgecolor(_fg)
    check = CheckButtons(
        ax_check,
        ["Apply bandpass"],
        [iccs.bandpass_apply],
        label_props={"color": [_fg], "fontsize": [11]},
        frame_props={"edgecolor": _fg, "s": 200},
        check_props={"color": _fg, "s": 200},
    )
    ax_radio.set_frame_on(True)
    ax_radio.set_xticks([])
    ax_radio.set_yticks([])
    for spine in ax_radio.spines.values():
        spine.set_edgecolor(_fg)
    ax_radio.text(
        0.5,
        0.85,
        "Preview as (not saved)",
        ha="center",
        va="top",
        fontsize=9,
        color=_fg,
        transform=ax_radio.transAxes,
    )
    # Give RadioButtons its own axes covering only the box's lower portion,
    # so it doesn't centre itself over the label above. fig.add_axes, not
    # ax_radio.inset_axes: an inset axes' locator recomputes its position
    # from the parent on every redraw, discarding set_position() below.
    radio_box_pos = ax_radio.get_position()
    ax_radio_toggles = fig.add_axes(
        (
            radio_box_pos.x0,
            radio_box_pos.y0,
            radio_box_pos.width,
            radio_box_pos.height * 0.55,
        )
    )
    ax_radio_toggles.set_frame_on(False)
    radio = RadioButtons(
        ax_radio_toggles,
        ["Zero-phase", "Causal"],
        active=0,
        layout="horizontal",
        label_props={"color": [_fg, _fg], "fontsize": [11, 11]},
    )
    # RadioButtons has no option to centre the group — measure how much
    # width it actually used, once rendered, and shift to centre it.
    fig.canvas.draw()
    content_right = radio.labels[-1].get_window_extent().x1
    toggles_bbox = ax_radio_toggles.get_window_extent()
    content_fraction = (content_right - toggles_bbox.x0) / toggles_bbox.width
    toggles_pos = ax_radio_toggles.get_position()
    offset = (1 - content_fraction) / 2 * toggles_pos.width
    ax_radio_toggles.set_position(toggles_pos.translated(offset, 0))
    slider_fmin = Slider(
        ax_fmin, "fmin [Hz]", _log_min, _log_max, valinit=np.log(iccs.bandpass_fmin)
    )
    slider_fmax = Slider(
        ax_fmax, "fmax [Hz]", _log_min, _log_max, valinit=np.log(iccs.bandpass_fmax)
    )
    slider_corners = Slider(
        ax_corners,
        "corners",
        valmin=1,
        valmax=max(8, iccs.corners),
        valinit=iccs.corners,
        valstep=1,
    )
    # Show Hz values rather than the internal log values
    slider_fmin.valtext.set_text(f"{iccs.bandpass_fmin:.3f}")
    slider_fmax.valtext.set_text(f"{iccs.bandpass_fmax:.3f}")
    # Set initial inter-slider bounds
    slider_fmax.valmin = np.log(iccs.bandpass_fmin + _freq_eps)
    slider_fmin.valmax = np.log(iccs.bandpass_fmax - _freq_eps)

    if not iccs.bandpass_apply:
        slider_fmin.set_active(False)
        slider_fmax.set_active(False)
        slider_corners.set_active(False)

    def _schedule_update() -> None:
        if _debounce_timer[0] is not None:
            _debounce_timer[0].stop()
        timer = fig.canvas.new_timer(interval=150)
        timer.single_shot = True
        timer.add_callback(update_fn)
        _debounce_timer[0] = timer
        timer.start()

    def _on_fmin_change(_: float) -> None:
        if _updating[0]:
            return
        _updating[0] = True
        fmin = float(np.exp(slider_fmin.val))
        slider_fmax.valmin = np.log(fmin + _freq_eps)
        if float(slider_fmax.val) <= np.log(fmin + _freq_eps):
            slider_fmax.set_val(np.log(fmin + _freq_eps))
        _updating[0] = False
        slider_fmin.valtext.set_text(f"{fmin:.3f}")
        slider_fmax.valtext.set_text(f"{np.exp(slider_fmax.val):.3f}")
        _schedule_update()

    def _on_fmax_change(_: float) -> None:
        if _updating[0]:
            return
        _updating[0] = True
        fmax = float(np.exp(slider_fmax.val))
        slider_fmin.valmax = np.log(fmax - _freq_eps)
        if float(slider_fmin.val) >= np.log(fmax - _freq_eps):
            slider_fmin.set_val(np.log(fmax - _freq_eps))
        _updating[0] = False
        slider_fmin.valtext.set_text(f"{np.exp(slider_fmin.val):.3f}")
        slider_fmax.valtext.set_text(f"{fmax:.3f}")
        _schedule_update()

    def _on_corners_change(_: float) -> None:
        _schedule_update()

    def _on_check(_label: str | None) -> None:
        apply = check.get_status()[0]
        slider_fmin.set_active(apply)
        slider_fmax.set_active(apply)
        slider_corners.set_active(apply)
        _schedule_update()

    def _on_radio_change(_label: str | None) -> None:
        _schedule_update()

    slider_fmin.on_changed(_on_fmin_change)
    slider_fmax.on_changed(_on_fmax_change)
    slider_corners.on_changed(_on_corners_change)
    check.on_clicked(_on_check)
    radio.on_clicked(_on_radio_change)

    def on_save(_: Event) -> None:
        if _debounce_timer[0] is not None:
            _debounce_timer[0].stop()
        fmin = float(np.exp(slider_fmin.val))
        fmax = float(np.exp(slider_fmax.val))
        corners = int(slider_corners.val)
        apply = check.get_status()[0]
        if not _apply_bandpass_params(iccs, apply, fmin, fmax, corners):
            return
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if _debounce_timer[0] is not None:
            _debounce_timer[0].stop()
        # Restore via _apply_bandpass_params, not direct field assignment:
        # the live preview only writes iccs's bandpass_*/corners fields on a
        # cache miss, so they can be an arbitrary previously-visited slider
        # combination at this point, and restoring the original values in a
        # fixed order can spuriously fail the same way a fixed-order update
        # can (see _apply_bandpass_params's docstring).
        _apply_bandpass_params(iccs, _orig_apply, _orig_fmin, _orig_fmax, _orig_corners)
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(ax_save, ax_cancel, on_save, on_cancel)

    if return_fig:
        return (
            fig,
            ax,
            (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
        )
    plt.show()
    return None
