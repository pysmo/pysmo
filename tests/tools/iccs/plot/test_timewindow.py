import matplotlib.pyplot as plt
import pytest
from matplotlib.widgets import SpanSelector

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    update_timewindow,
)
from tests.tools.iccs.plot._helpers import _click_button


def test_setup_timewindow_picker_returns_type(iccs_instance: ICCS) -> None:
    """Verify update_timewindow creates a SpanSelector with correct initial extents."""
    iccs_instance()
    fig, ax, (span, _, _) = update_timewindow(iccs_instance, return_fig=True)

    assert isinstance(span, SpanSelector)
    # Initial extents should match current window
    assert span.extents[0] == pytest.approx(iccs_instance.window_pre.total_seconds())
    assert span.extents[1] == pytest.approx(iccs_instance.window_post.total_seconds())
    plt.close(fig)


def test_setup_timewindow_picker_callback(iccs_instance: ICCS) -> None:
    """A valid selection must update the axes title via the selection callback."""
    iccs_instance()
    fig, ax, (span, _, _) = update_timewindow(iccs_instance, return_fig=True)

    pre = iccs_instance.window_pre.total_seconds()
    post = iccs_instance.window_post.total_seconds()
    span.onselect(pre, post)

    assert f"{pre:.3f}" in ax.get_title()
    assert f"{post:.3f}" in ax.get_title()
    plt.close(fig)


def test_timewindow_picker_invalid_selection_resets_extents(
    iccs_instance: ICCS,
) -> None:
    """An invalid selection must reset the SpanSelector to the previous extents."""
    iccs_instance()
    fig, ax, (span, b_save, b_cancel) = update_timewindow(
        iccs_instance, return_fig=True
    )

    original_extents = span.extents

    # Select a window where pre > post (swapped) — always invalid.
    post = iccs_instance.window_post.total_seconds()
    pre = iccs_instance.window_pre.total_seconds()
    span.onselect(post, pre)  # reversed → invalid

    assert span.extents == pytest.approx(original_extents)
    assert ax.get_title() == "Invalid window choice."
    plt.close(fig)


def test_timewindow_picker_valid_then_invalid_keeps_last_valid(
    iccs_instance: ICCS,
) -> None:
    """After a valid then invalid selection, extents settle at the last valid ones."""
    iccs_instance()
    fig, ax, (span, b_save, b_cancel) = update_timewindow(
        iccs_instance, return_fig=True
    )

    # First, a valid narrower window
    pre = iccs_instance.window_pre.total_seconds() / 2
    post = iccs_instance.window_post.total_seconds() / 2
    span.onselect(pre, post)
    assert f"{pre:.3f}" in ax.get_title()

    # Then an invalid selection (reversed)
    span.onselect(post, pre)
    assert span.extents == pytest.approx((pre, post))
    plt.close(fig)


def test_update_timewindow_save_applies_window(iccs_instance: ICCS) -> None:
    """Clicking Save in update_timewindow updates window_pre and window_post."""
    iccs_instance()
    fig, ax, (span, b_save, b_cancel) = update_timewindow(
        iccs_instance, return_fig=True
    )

    # Choose a valid new window (half the current one)
    new_pre = iccs_instance.window_pre.total_seconds() / 2
    new_post = iccs_instance.window_post.total_seconds() / 2
    span.onselect(new_pre, new_post)

    _click_button(b_save)

    assert iccs_instance.window_pre.total_seconds() == pytest.approx(new_pre)
    assert iccs_instance.window_post.total_seconds() == pytest.approx(new_post)
    plt.close(fig)


def test_update_timewindow_cancel_leaves_window_unchanged(iccs_instance: ICCS) -> None:
    """Clicking Cancel in update_timewindow does not change window_pre/post."""
    iccs_instance()
    orig_pre = iccs_instance.window_pre
    orig_post = iccs_instance.window_post

    fig, ax, (span, b_save, b_cancel) = update_timewindow(
        iccs_instance, return_fig=True
    )

    # Simulate a selection
    new_pre = iccs_instance.window_pre.total_seconds() / 2
    new_post = iccs_instance.window_post.total_seconds() / 2
    span.onselect(new_pre, new_post)

    # Click Cancel
    _click_button(b_cancel)

    assert iccs_instance.window_pre == orig_pre
    assert iccs_instance.window_post == orig_post
    plt.close(fig)


def test_update_timewindow_defaults_to_zerophase(iccs_instance: ICCS) -> None:
    """update_timewindow defaults to causal=False (matches what window_pre/post actually crop)."""
    iccs_instance()
    iccs_instance.bandpass_apply = True
    fig, ax, _ = update_timewindow(iccs_instance, return_fig=True)
    assert "(zero-phase)" in ax.get_ylabel()
    plt.close(fig)
