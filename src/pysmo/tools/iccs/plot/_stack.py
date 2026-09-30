"""Stack plot."""

from typing import Literal, overload

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colorbar import Colorbar
from matplotlib.colors import PowerNorm
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from .._defaults import IccsDefaults
from .._iccs import ICCS
from ._common import _make_mask, _variant_suffix


def _draw_stack_initial(
    ax: Axes, iccs: ICCS, context: bool, all_seismograms: bool, causal: bool = False
) -> tuple[list[Line2D], Line2D, ScalarMappable, Colorbar]:
    """Draw the stack plot and return artist references for live updates.

    Args:
        ax: Axes to plot on.
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: `context_seismograms` are used.
            - `False`: `cc_seismograms` are used.
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
            - `True`: `context_seismograms` are used.
            - `False`: `cc_seismograms` are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        causal: Determines the filter phase behaviour:
            - `True`: causally-filtered (single-pass) seismograms are used.
            - `False`: zero-phase filtered seismograms are used.
    """
    _draw_stack_initial(ax, iccs, context, all_seismograms, causal)


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
            - `True`: `context_seismograms` are used.
            - `False`: `cc_seismograms` are used.
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

        ![The ICCS stack padded beyond the cross-correlation window, which is highlighted in green.](../../../images/sybil/iccs_context_stack.png#only-light){ loading=lazy }
        ![The ICCS stack padded beyond the cross-correlation window, which is highlighted in green.](../../../images/sybil/iccs_context_stack-dark.png#only-dark){ loading=lazy }

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

        ![The ICCS stack restricted to the exact window used for the cross-correlations.](../../../images/sybil/iccs_cc_stack.png#only-light){ loading=lazy }
        ![The ICCS stack restricted to the exact window used for the cross-correlations.](../../../images/sybil/iccs_cc_stack-dark.png#only-dark){ loading=lazy }

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
