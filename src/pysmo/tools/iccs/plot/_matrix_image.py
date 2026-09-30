"""Matrix image plot."""

from typing import Literal, overload

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.image import AxesImage

from .._defaults import IccsDefaults
from .._iccs import ICCS
from ._common import _make_mask, _variant_suffix


def _draw_matrix_image_initial(
    ax: Axes, iccs: ICCS, context: bool, all_seismograms: bool, causal: bool = False
) -> tuple[AxesImage, npt.NDArray[np.floating]]:
    """Draw the matrix image plot and return artist references for live updates.

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
        + f"{_variant_suffix(iccs.bandpass_apply, False)}"
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
) -> npt.NDArray[np.floating]:
    """Return a basic matrix image plot for use in other plots.

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
        Sorted seismogram matrix used for the plot.
    """
    _, seismogram_matrix = _draw_matrix_image_initial(
        ax, iccs, context, all_seismograms, causal
    )
    return seismogram_matrix


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
        >>> import matplotlib.pyplot as plt
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_context_image.png", transparent=True)
        ...     plt.style.use("dark_background")
        ...     fig, ax = plot_matrix_image(iccs)
        ...     fig.savefig(savedir / "iccs_context_image-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Selected seismograms as a matrix image, padded beyond the cross-correlation window.](../../../images/sybil/iccs_context_image.png#only-light){ loading=lazy }
        ![Selected seismograms as a matrix image, padded beyond the cross-correlation window.](../../../images/sybil/iccs_context_image-dark.png#only-dark){ loading=lazy }

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

        ![Selected seismograms as a matrix image, restricted to the cross-correlation window.](../../../images/sybil/iccs_cc_image.png#only-light){ loading=lazy }
        ![Selected seismograms as a matrix image, restricted to the cross-correlation window.](../../../images/sybil/iccs_cc_image-dark.png#only-dark){ loading=lazy }

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
