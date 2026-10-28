import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    draw_common_stack,
    plot_stack,
)


def test_draw_stack_returns_none(iccs_instance: ICCS) -> None:
    """Verify draw_stack draws without error and axes has expected children."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, all_seismograms=False)
    # Axes should contain lines (seismograms + stack) and patches (axvspan)
    assert len(ax.lines) > 0
    assert len(ax.patches) > 0
    plt.close(fig)


def test_draw_common_stack_xlim_no_ramp(iccs_instance: ICCS) -> None:
    """x-axis limits equal window_pre / window_post when ramp_width is zero."""
    iccs_instance.ramp_width = pd.Timedelta(0)
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=False, all_seismograms=False)
    xmin, xmax = ax.get_xlim()
    assert xmin == pytest.approx(iccs_instance.window_pre.total_seconds())
    assert xmax == pytest.approx(iccs_instance.window_post.total_seconds())
    plt.close(fig)


def test_draw_common_stack_xlim_with_ramp(iccs_instance: ICCS) -> None:
    """x-axis limits extend by ramp_width beyond the CC window when context=False."""
    ramp = pd.Timedelta(seconds=2)
    iccs_instance.ramp_width = ramp
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=False, all_seismograms=False)
    xmin, xmax = ax.get_xlim()
    assert xmin == pytest.approx(
        iccs_instance.window_pre.total_seconds() - ramp.total_seconds()
    )
    assert xmax == pytest.approx(
        iccs_instance.window_post.total_seconds() + ramp.total_seconds()
    )
    plt.close(fig)


def test_draw_common_stack_xlim_with_context(iccs_instance: ICCS) -> None:
    """x-axis limits extend by context_width beyond the CC window when context=True."""
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, all_seismograms=False)
    xmin, xmax = ax.get_xlim()
    assert xmin == pytest.approx(
        iccs_instance.window_pre.total_seconds()
        - iccs_instance.context_width.total_seconds()
    )
    assert xmax == pytest.approx(
        iccs_instance.window_post.total_seconds()
        + iccs_instance.context_width.total_seconds()
    )
    plt.close(fig)


def test_draw_common_stack_window_markers(iccs_instance: ICCS) -> None:
    """axvspan and axvlines mark window_pre / window_post regardless of ramp."""
    ramp = pd.Timedelta(seconds=2)
    iccs_instance.ramp_width = ramp
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=False, all_seismograms=False)

    # axvspan covers the time window (not the taper ramp)
    spans = ax.patches
    assert len(spans) >= 1
    span = spans[0]
    assert isinstance(span, Rectangle)
    span_xmin = span.get_x()
    span_xmax = span.get_x() + span.get_width()
    assert span_xmin == pytest.approx(iccs_instance.window_pre.total_seconds())
    assert span_xmax == pytest.approx(iccs_instance.window_post.total_seconds())
    plt.close(fig)


def test_draw_common_stack_causal_labels_variant(iccs_instance: ICCS) -> None:
    """The y-label identifies the causal variant, only when bandpass_apply=True."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    fig, ax = plt.subplots()
    draw_common_stack(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    assert "(causal)" in ax.get_ylabel()
    plt.close(fig)

    fig, ax = plt.subplots()
    draw_common_stack(
        ax, iccs_instance, context=False, all_seismograms=False, causal=False
    )
    assert "(zero-phase)" in ax.get_ylabel()
    plt.close(fig)


def test_draw_common_stack_causal_unlabelled_when_apply_false(
    iccs_instance: ICCS,
) -> None:
    """No variant suffix is shown when bandpass_apply=False (variants are identical)."""
    iccs_instance()
    assert iccs_instance.bandpass_apply is False

    fig, ax = plt.subplots()
    draw_common_stack(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    assert "(causal)" not in ax.get_ylabel()
    assert "(zero-phase)" not in ax.get_ylabel()
    plt.close(fig)


def test_draw_common_stack_colorbar_labels_zerophase_only_when_apply_true(
    iccs_instance: ICCS,
) -> None:
    """The colorbar always reads zero-phase, never "(causal)", regardless of the preview toggle."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    fig, ax = plt.subplots()
    draw_common_stack(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    colorbar_ax = fig.axes[-1]
    assert "(zero-phase)" in colorbar_ax.get_ylabel()
    assert "(causal)" not in colorbar_ax.get_ylabel()
    plt.close(fig)

    iccs_instance.bandpass_apply = False
    fig, ax = plt.subplots()
    draw_common_stack(
        ax, iccs_instance, context=False, all_seismograms=False, causal=True
    )
    colorbar_ax = fig.axes[-1]
    assert "(zero-phase)" not in colorbar_ax.get_ylabel()
    plt.close(fig)


def test_plot_stack_causal_smoke(iccs_instance: ICCS) -> None:
    """plot_stack accepts causal=True and draws without error."""
    iccs_instance()
    fig, ax = plot_stack(iccs_instance, context=False, causal=True, return_fig=True)
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    plt.close(fig)
