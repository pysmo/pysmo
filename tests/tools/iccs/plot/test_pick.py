import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.lines import Line2D
from matplotlib.widgets import Cursor

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    update_pick,
)
from tests.tools.iccs.plot._helpers import _click_button, _fire_click, _fire_move


def test_setup_phase_picker_returns_types(iccs_instance: ICCS) -> None:
    """Verify update_pick creates a Cursor and pick Line2D at x=0."""
    iccs_instance()
    fig, ax, (cursor, pick_line, b_save, b_cancel) = update_pick(
        iccs_instance, return_fig=True
    )

    assert isinstance(cursor, Cursor)
    assert isinstance(pick_line, Line2D)
    # Pick line should be at x=0 initially
    assert np.asarray(pick_line.get_xdata())[0] == 0
    plt.close(fig)


def test_setup_phase_picker_callback(iccs_instance: ICCS) -> None:
    """A valid click must update the axes title via the pick callback."""
    iccs_instance()
    fig, ax, (_, _, _, _) = update_pick(iccs_instance, return_fig=True)

    # Simulate a click at x=0 (always valid since it's the current pick)
    _fire_click(fig, ax, 0.0)

    assert "0.000" in ax.get_title()
    plt.close(fig)


def test_phase_picker_invalid_click_no_callback(iccs_instance: ICCS) -> None:
    """A click outside the valid pick range must not update the title."""
    iccs_instance()
    fig, ax, (_, _, _, _) = update_pick(iccs_instance, return_fig=True)

    original_title = ax.get_title()
    # A shift of 10 hours is definitely outside the valid range.
    _fire_click(fig, ax, pd.Timedelta(hours=10).total_seconds())

    assert ax.get_title() == original_title
    plt.close(fig)


def test_phase_picker_mouse_move_cursor_colour(iccs_instance: ICCS) -> None:
    """Cursor line turns green for valid positions and red for invalid ones."""
    iccs_instance()
    fig, ax, (cursor, _, _, _) = update_pick(iccs_instance, return_fig=True)

    # x=0 is at the current pick — always valid
    _fire_move(fig, ax, 0.0)
    assert cursor.linev.get_color() == "g"

    # A 10-hour shift is always invalid
    _fire_move(fig, ax, pd.Timedelta(hours=10).total_seconds())
    assert cursor.linev.get_color() == "r"
    plt.close(fig)


def test_update_pick_save_applies_pick(iccs_instance: ICCS) -> None:
    """Clicking Save in update_pick updates all seismogram picks."""
    iccs_instance()
    original_picks = [
        (s.refined_pick or s.initial_pick) for s in iccs_instance.seismograms
    ]

    fig, ax, (cursor, pick_line, b_save, b_cancel) = update_pick(
        iccs_instance, return_fig=True
    )

    delta_s = 1.0
    # Simulate a valid pick click at 1 second
    _fire_click(fig, ax, delta_s)

    # Click Save
    _click_button(b_save)

    for orig, s in zip(original_picks, iccs_instance.seismograms):
        assert (s.refined_pick or s.initial_pick) - orig == pytest.approx(
            pd.Timedelta(seconds=delta_s), abs=pd.Timedelta(seconds=1e-6)
        )
    plt.close(fig)


def test_update_pick_cancel_leaves_picks_unchanged(iccs_instance: ICCS) -> None:
    """Clicking Cancel in update_pick does not change any picks."""
    iccs_instance()
    original_picks = [
        (s.refined_pick or s.initial_pick) for s in iccs_instance.seismograms
    ]

    fig, ax, (cursor, pick_line, b_save, b_cancel) = update_pick(
        iccs_instance, return_fig=True
    )

    # Simulate a valid pick click
    _fire_click(fig, ax, 1.0)

    # Click Cancel instead of Save
    _click_button(b_cancel)

    for orig, s in zip(original_picks, iccs_instance.seismograms):
        assert (s.refined_pick or s.initial_pick) == orig
    plt.close(fig)


def test_update_pick_defaults_to_causal(iccs_instance: ICCS) -> None:
    """update_pick defaults to causal=True (the point of the feature)."""
    iccs_instance()
    iccs_instance.bandpass_apply = True
    fig, ax, _ = update_pick(iccs_instance, return_fig=True)
    assert "(causal)" in ax.get_ylabel()
    plt.close(fig)
