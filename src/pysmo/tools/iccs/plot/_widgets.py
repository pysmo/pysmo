"""Figure layout and widgets shared by the interactive tools."""

from collections.abc import Callable

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.widgets import (
    Button,
)

from .._iccs import ICCS
from ._matrix_image import draw_common_matrix_image
from ._stack import draw_common_stack


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
    no live-updating preview; see `update_bandpass` for the one dialog
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
    within the `[bottom, top]` span, matplotlib's normal `GridSpec` meaning,
    not absolute fractions), stacked top-to-bottom, where the last entry is
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
        Tuple of (save_button, cancel_button). Must be stored to prevent
        garbage collection.
    """
    b_save = Button(ax_save, "Save", color="darkgreen", hovercolor="green")
    b_save.on_clicked(on_save)
    b_cancel = Button(ax_cancel, "Cancel", color="darkred", hovercolor="red")
    b_cancel.on_clicked(on_cancel)

    return b_save, b_cancel


class _ScrollIndexTracker:
    """Track the scroll position for the min_cc picker."""

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
