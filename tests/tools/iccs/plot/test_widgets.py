from typing import Literal

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent
from matplotlib.figure import Figure

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    draw_common_matrix_image,
)
from pysmo.tools.iccs.plot._widgets import _ScrollIndexTracker


def test_scroll_index_tracker(iccs_instance: ICCS) -> None:
    """Verify ScrollIndexTracker initial state and scroll behaviour."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_matrix_image(ax, iccs_instance, context=True, all_seismograms=False)

    tracker = _ScrollIndexTracker(ax, fig)
    initial = tracker.scroll_index

    # Simulate scroll down (reduces visible range)
    event_down = MouseEvent("scroll_event", fig.canvas, 0, 0)
    event_down.inaxes = ax
    event_down.button = "down"
    tracker.on_scroll(event_down)
    assert tracker.scroll_index <= initial

    # Simulate scroll up (increases visible range)
    event_up = MouseEvent("scroll_event", fig.canvas, 0, 0)
    event_up.inaxes = ax
    event_up.button = "up"
    tracker.on_scroll(event_up)
    assert tracker.scroll_index >= 1
    plt.close(fig)


def test_scroll_tracker_initial_state(iccs_instance: ICCS) -> None:
    """Tracker scroll_index starts at the top y-limit of the axes."""
    iccs_instance()
    fig, ax = plt.subplots()
    ax.set_ylim(0, 10)
    tracker = _ScrollIndexTracker(ax, fig)
    assert tracker.scroll_index == pytest.approx(10.0)
    assert tracker.max_scroll_index == pytest.approx(10.0)
    plt.close(fig)


def _scroll_event(
    fig: Figure, ax: Axes, direction: Literal["up", "down"]
) -> MouseEvent:
    """Create a scroll MouseEvent aimed at the given axes."""
    event = MouseEvent("scroll_event", fig.canvas, 0, 0, button=direction)
    event.inaxes = ax
    return event


def test_scroll_tracker_scroll_up_increases_index(iccs_instance: ICCS) -> None:
    """Scrolling up increases scroll_index (shows more rows), clamped at max."""
    iccs_instance()
    fig, ax = plt.subplots()
    ax.set_ylim(0, 5)
    tracker = _ScrollIndexTracker(ax, fig)
    # Manually reduce the index so there is room to scroll up.
    tracker.scroll_index = 1
    tracker.update()
    initial = tracker.scroll_index
    tracker.on_scroll(_scroll_event(fig, ax, "up"))
    assert tracker.scroll_index > initial
    plt.close(fig)


def test_scroll_tracker_scroll_down_clamps_at_one(iccs_instance: ICCS) -> None:
    """Scrolling down beyond the minimum clamps at 1."""
    iccs_instance()
    fig, ax = plt.subplots()
    ax.set_ylim(0, 10)
    tracker = _ScrollIndexTracker(ax, fig)
    for _ in range(100):
        tracker.on_scroll(_scroll_event(fig, ax, "down"))
    assert tracker.scroll_index == pytest.approx(1.0)
    plt.close(fig)


def test_scroll_tracker_scroll_up_clamps_at_max(iccs_instance: ICCS) -> None:
    """Scrolling up beyond the maximum clamps at max_scroll_index."""
    iccs_instance()
    fig, ax = plt.subplots()
    ax.set_ylim(0, 10)
    tracker = _ScrollIndexTracker(ax, fig)
    for _ in range(100):
        tracker.on_scroll(_scroll_event(fig, ax, "up"))
    assert tracker.scroll_index == pytest.approx(tracker.max_scroll_index)
    plt.close(fig)
