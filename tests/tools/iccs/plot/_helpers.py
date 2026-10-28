"""Event helpers shared by the ICCS plot tests."""

from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.figure import Figure
from matplotlib.widgets import Button


def _fire_click(fig: Figure, ax: Axes, x: float) -> None:
    """Helper: simulate a left-click at x in axes coordinates."""
    event = MouseEvent("button_press_event", fig.canvas, 0, 0, button=MouseButton.LEFT)
    event.inaxes = ax
    event.xdata = x
    event.ydata = 0.0
    fig.canvas.callbacks.process("button_press_event", event)


def _fire_click_y(fig: Figure, ax: Axes, y: float) -> None:
    """Helper: simulate a left-click at y in axes coordinates."""
    event = MouseEvent("button_press_event", fig.canvas, 0, 0, button=MouseButton.LEFT)
    event.inaxes = ax
    event.xdata = 0.0
    event.ydata = y
    fig.canvas.callbacks.process("button_press_event", event)


def _fire_move(fig: Figure, ax: Axes, x: float | None) -> None:
    """Helper: simulate a mouse-move at x (or outside axes if x is None)."""
    event = MouseEvent("motion_notify_event", fig.canvas, 0, 0)
    event.inaxes = ax if x is not None else None
    event.xdata = x
    event.ydata = 0.0
    fig.canvas.callbacks.process("motion_notify_event", event)


def _fire_move_y(fig: Figure, ax: Axes, y: float | None) -> None:
    """Helper: simulate a mouse-move at y (or outside axes if y is None)."""
    event = MouseEvent("motion_notify_event", fig.canvas, 0, 0)
    event.inaxes = ax if y is not None else None
    event.xdata = 0.0
    event.ydata = y
    fig.canvas.callbacks.process("motion_notify_event", event)


def _click_button(button: "Button") -> None:
    """Helper: trigger a matplotlib Button's click observers directly."""
    from matplotlib.backend_bases import MouseEvent

    event = MouseEvent("button_release_event", button.ax.figure.canvas, 0, 0)
    button._observers.process("clicked", event)  # type: ignore[attr-defined]
