from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    _ScrollIndexTracker,
    draw_common_image,
    draw_common_stack,
    _setup_ccnorm_picker,
    _setup_phase_picker,
    _setup_timewindow_picker,
)
from pandas import Timedelta
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.widgets import Cursor, SpanSelector
import matplotlib.pyplot as plt
import numpy as np
import pytest


def test_update_pick(iccs_instance: ICCS) -> None:
    """Test updating a pick."""
    iccs = iccs_instance
    _ = iccs()
    org_picks = [s.t1 for s in iccs.seismograms if s.t1 is not None]
    pickdelta = Timedelta(seconds=1.23)
    iccs.update_all_picks(pickdelta)
    new_picks = [s.t1 for s in iccs.seismograms if s.t1 is not None]
    for org, new in zip(org_picks, new_picks):
        assert new - org == pickdelta


def test_update_pick_that_is_invalid(iccs_instance: ICCS) -> None:
    """Test if error is raised with a bad pick."""

    from pysmo.tools.iccs._iccs import _calc_valid_pick_range

    iccs = iccs_instance
    min_t1, max_t1 = _calc_valid_pick_range(iccs)
    with pytest.raises(ValueError):
        iccs.update_all_picks(max_t1 + Timedelta(seconds=1))
    with pytest.raises(ValueError):
        iccs.update_all_picks(min_t1 - Timedelta(seconds=1))


class TestPlotCommonBase:
    PADDED = False
    ALL = False

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_stack_initial(self, iccs_instance: ICCS) -> Figure:
        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_stack(ax, iccs_instance, context=self.PADDED, show_all=self.ALL)
        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_stack_after(self, iccs_instance: ICCS) -> Figure:
        iccs_instance()

        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_stack(ax, iccs_instance, context=self.PADDED, show_all=self.ALL)

        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_image_initial(self, iccs_instance: ICCS) -> Figure:
        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_image(ax, iccs_instance, context=self.PADDED, show_all=self.ALL)

        return fig

    @pytest.mark.mpl_image_compare(remove_text=True, style="default")
    def test_plot_common_image_after(self, iccs_instance: ICCS) -> Figure:
        iccs_instance()

        fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
        draw_common_image(ax, iccs_instance, context=self.PADDED, show_all=self.ALL)

        return fig


class TestPlotCommonAll(TestPlotCommonBase):
    ALL = True


class TestPlotCommonPadded(TestPlotCommonBase):
    PADDED = True


class TestPlotCommonAllPadded(TestPlotCommonBase):
    ALL = True
    PADDED = True


# ======================================================================
# New tests for the newly public helpers
# ======================================================================


def test_draw_stack_returns_none(iccs_instance: ICCS) -> None:
    """Verify draw_stack draws without error and axes has expected children."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, show_all=False)
    # Axes should contain lines (seismograms + stack) and patches (axvspan)
    assert len(ax.lines) > 0
    assert len(ax.patches) > 0
    plt.close(fig)


def test_draw_seismograms_returns_matrix(iccs_instance: ICCS) -> None:
    """Verify draw_seismograms returns an ndarray with correct shape."""
    iccs_instance()
    fig, ax = plt.subplots()
    result = draw_common_image(ax, iccs_instance, context=True, show_all=False)
    assert isinstance(result, np.ndarray)
    n_selected = sum(1 for s in iccs_instance.seismograms if s.select)
    assert result.shape[0] == n_selected
    plt.close(fig)


def test_setup_phase_picker_returns_types(iccs_instance: ICCS) -> None:
    """Verify setup_phase_picker returns (Cursor, Line2D) with pick line at x=0."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, show_all=False)

    cursor, pick_line = _setup_phase_picker(ax, iccs_instance, lambda x: None)

    assert isinstance(cursor, Cursor)
    assert isinstance(pick_line, Line2D)
    # Pick line should be at x=0 initially
    assert np.asarray(pick_line.get_xdata())[0] == 0
    plt.close(fig)


def test_setup_phase_picker_callback(iccs_instance: ICCS) -> None:
    """Simulate a valid click and verify callback is called with correct xdata."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, show_all=False)

    received: list[float] = []
    _ = _setup_phase_picker(ax, iccs_instance, received.append)

    # Simulate a click at x=0 (always valid since it's the current pick)
    event = MouseEvent("button_press_event", fig.canvas, 0, 0, button=MouseButton.LEFT)
    event.inaxes = ax
    event.xdata = 0.0
    event.ydata = 0.0
    fig.canvas.callbacks.process("button_press_event", event)

    assert len(received) == 1
    assert received[0] == 0.0
    plt.close(fig)


def test_setup_timewindow_picker_returns_type(iccs_instance: ICCS) -> None:
    """Verify setup_timewindow_picker returns a SpanSelector."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, show_all=False)

    span = _setup_timewindow_picker(ax, iccs_instance, lambda xmin, xmax: None)

    assert isinstance(span, SpanSelector)
    # Initial extents should match current window
    assert span.extents[0] == pytest.approx(iccs_instance.window_pre.total_seconds())
    assert span.extents[1] == pytest.approx(iccs_instance.window_post.total_seconds())
    plt.close(fig)


def test_setup_timewindow_picker_callback(iccs_instance: ICCS) -> None:
    """Simulate a valid selection and verify callback is called."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_stack(ax, iccs_instance, context=True, show_all=False)

    received: list[tuple[float, float]] = []

    def on_select(xmin: float, xmax: float) -> None:
        received.append((xmin, xmax))

    span = _setup_timewindow_picker(ax, iccs_instance, on_select)

    # Simulate a valid selection within the current window bounds
    pre = iccs_instance.window_pre.total_seconds()
    post = iccs_instance.window_post.total_seconds()
    span.onselect(pre, post)

    assert len(received) == 1
    assert received[0] == pytest.approx((pre, post))
    plt.close(fig)


def test_setup_ccnorm_picker_returns_types(iccs_instance: ICCS) -> None:
    """Verify setup_ccnorm_picker returns (Cursor, Line2D, ScrollIndexTracker)."""
    iccs_instance()
    fig, ax = plt.subplots()
    matrix = draw_common_image(ax, iccs_instance, context=True, show_all=False)

    cursor, pick_line, tracker = _setup_ccnorm_picker(
        ax, iccs_instance, False, len(matrix) - 1, lambda x: None
    )

    assert isinstance(cursor, Cursor)
    assert isinstance(pick_line, Line2D)
    assert isinstance(tracker, _ScrollIndexTracker)
    plt.close(fig)


def test_scroll_index_tracker(iccs_instance: ICCS) -> None:
    """Verify ScrollIndexTracker initial state and scroll behaviour."""
    iccs_instance()
    fig, ax = plt.subplots()
    draw_common_image(ax, iccs_instance, context=True, show_all=False)

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
