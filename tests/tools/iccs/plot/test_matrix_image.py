import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    draw_common_matrix_image,
    plot_matrix_image,
)


def test_draw_seismograms_returns_matrix(iccs_instance: ICCS) -> None:
    """Verify draw_seismograms returns an ndarray with correct shape."""
    iccs_instance()
    fig, ax = plt.subplots()
    result = draw_common_matrix_image(
        ax, iccs_instance, context=True, all_seismograms=False
    )
    assert isinstance(result, np.ndarray)
    n_selected = sum(1 for s in iccs_instance.seismograms if s.select)
    assert result.shape[0] == n_selected
    plt.close(fig)


def test_draw_common_matrix_image_xlim_with_context(iccs_instance: ICCS) -> None:
    """Image x-extent covers window + context_width on each side when context=True."""
    fig, ax = plt.subplots()
    draw_common_matrix_image(ax, iccs_instance, context=True, all_seismograms=False)
    # imshow extent is encoded in the AxesImage
    img = ax.images[0]
    img_xmin, img_xmax = img.get_extent()[:2]
    assert img_xmin == pytest.approx(
        iccs_instance.window_pre.total_seconds()
        - iccs_instance.context_width.total_seconds()
    )
    assert img_xmax == pytest.approx(
        iccs_instance.window_post.total_seconds()
        + iccs_instance.context_width.total_seconds()
    )
    plt.close(fig)


def test_draw_common_matrix_image_window_boundary_lines(iccs_instance: ICCS) -> None:
    """draw_common_matrix_image draws axvlines at window_pre and window_post."""
    fig, ax = plt.subplots()
    draw_common_matrix_image(ax, iccs_instance, context=True, all_seismograms=False)
    # Collect x-positions of vertical lines
    vline_xs = []
    for line in ax.lines:
        xdata = np.asarray(line.get_xdata())
        if len(xdata) == 2 and xdata[0] == xdata[1]:
            vline_xs.append(xdata[0])

    assert iccs_instance.window_pre.total_seconds() in [
        pytest.approx(x) for x in vline_xs
    ]
    assert iccs_instance.window_post.total_seconds() in [
        pytest.approx(x) for x in vline_xs
    ]
    plt.close(fig)


def test_draw_common_matrix_image_causal_labels_variant(iccs_instance: ICCS) -> None:
    """The x-label identifies the causal variant, only when bandpass_apply=True."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    fig, ax = plt.subplots()
    draw_common_matrix_image(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    assert "(causal)" in ax.get_xlabel()
    plt.close(fig)


def test_draw_common_matrix_image_ylabel_zerophase_only_when_apply_true(
    iccs_instance: ICCS,
) -> None:
    """The row-order y-label always reads zero-phase, gated the same way as the colorbar."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    fig, ax = plt.subplots()
    draw_common_matrix_image(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    assert "(zero-phase)" in ax.get_ylabel()
    plt.close(fig)

    iccs_instance.bandpass_apply = False
    fig, ax = plt.subplots()
    draw_common_matrix_image(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    assert "(zero-phase)" not in ax.get_ylabel()
    plt.close(fig)


def test_plot_matrix_image_causal_smoke(iccs_instance: ICCS) -> None:
    """plot_matrix_image accepts causal=True and draws without error."""
    iccs_instance()
    fig, ax = plot_matrix_image(
        iccs_instance, context=False, causal=True, return_fig=True
    )
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    plt.close(fig)
