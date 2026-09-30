"""Interactive bandpass parameter update."""

from collections import OrderedDict
from collections.abc import Callable
from typing import Literal, overload

import matplotlib.pyplot as plt
import numpy as np
import numpy.typing as npt
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, TimerBase
from matplotlib.colors import PowerNorm
from matplotlib.figure import Figure
from matplotlib.widgets import (
    Button,
    CheckButtons,
    RadioButtons,
    Slider,
)

from pysmo.tools.signal import causal_band

from .._defaults import IccsDefaults
from .._iccs import ICCS
from ._common import _make_mask, _variant_suffix
from ._matrix_image import _draw_matrix_image_initial
from ._stack import _draw_stack_initial
from ._widgets import _add_save_cancel_buttons, _left_margin, _widget_gridspec


def _apply_bandpass_params(
    iccs: ICCS, apply: bool, fmin: float, fmax: float, corners: int
) -> bool:
    """Apply new bandpass parameters together, without spurious rejections.

    ICCS's per-field validators check each new value against the *other*
    fields' current values, so setting bandpass_fmin, bandpass_fmax, and
    corners one at a time in a fixed order can spuriously reject a
    combination that's valid once all three are set together (e.g. a step
    checked against a stale, narrower band left over from a previous
    update).

    Avoided by validating the full target via
    [`causal_band`][pysmo.tools.signal.causal_band] first, then writing
    fields moving in the *permissive* direction (`bandpass_fmin` down,
    `bandpass_fmax` up, `corners` up) before the *restrictive* ones: a
    permissive write can only make an already-valid combination more valid,
    and by the time a restrictive field is written the others are already
    at their validated target, so it succeeds too.

    Returns:
        `True` if the target combination was valid and applied (cache
        cleared). `False` if invalid: `iccs` is left unchanged.
    """
    if fmin >= fmax:
        return False
    try:
        causal_band(fmin, fmax, corners)
    except ValueError:
        return False

    iccs.bandpass_apply = apply

    fields = [
        ("bandpass_fmin", fmin, fmin <= iccs.bandpass_fmin),
        ("bandpass_fmax", fmax, fmax >= iccs.bandpass_fmax),
        ("corners", corners, corners >= iccs.corners),
    ]
    for name, value, permissive in sorted(fields, key=lambda f: not f[2]):
        setattr(iccs, name, value)

    return True


@overload
def update_bandpass(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    return_fig: Literal[True] = True,
) -> tuple[
    Figure,
    Axes,
    tuple[CheckButtons, Slider, Slider, Slider, RadioButtons, Button, Button],
]: ...


@overload
def update_bandpass(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    *,
    return_fig: Literal[False],
) -> None: ...


def update_bandpass(
    iccs: ICCS,
    context: bool = True,
    all_seismograms: bool = False,
    use_matrix_image: bool = False,
    return_fig: bool = True,
) -> (
    tuple[
        Figure,
        Axes,
        tuple[CheckButtons, Slider, Slider, Slider, RadioButtons, Button, Button],
    ]
    | None
):
    """Interactively update the bandpass filter parameters.

    This function launches an interactive figure to adjust
    [`bandpass_apply`][pysmo.tools.iccs.ICCS.bandpass_apply],
    [`bandpass_fmin`][pysmo.tools.iccs.ICCS.bandpass_fmin],
    [`bandpass_fmax`][pysmo.tools.iccs.ICCS.bandpass_fmax], and
    [`corners`][pysmo.tools.iccs.ICCS.corners] with a live preview. A radio
    button toggles the preview between the causal and zero-phase variants;
    this is UI-only, not a saved parameter, since both renderings are
    relevant while tuning rather than there being a default to pick.

    Args:
        iccs: Instance of the [`ICCS`][pysmo.tools.iccs.ICCS] class.
        context: Determines which seismograms are used:
            - `True`: `context_seismograms` are used.
            - `False`: `cc_seismograms` are used.
        all_seismograms: If `True`, all seismograms are shown in the plot instead of the
            selected ones only.
        use_matrix_image: Use the
            [matrix image][pysmo.tools.iccs.plot_matrix_image]
            instead of the [stack][pysmo.tools.iccs.plot_stack].
        return_fig: If `True`, the [`Figure`][matplotlib.figure.Figure] and
            [`Axes`][matplotlib.axes.Axes] objects are returned instead of
            shown.

    Returns:
        Figure with the filter widgets if `return_fig` is `True`.

    Examples:
        ```python
        >>> from pysmo.tools.iccs import ICCS, update_bandpass
        >>> iccs = ICCS(iccs_seismograms)
        >>> iccs.bandpass_apply = True  # start with bandpass applied
        >>> _ = iccs(autoselect=True, autoflip=True)
        >>>
        >>> fig, ax, widgets = update_bandpass(iccs)
        >>> # fig.show() # or integrate into your own application
        >>>
        ```

        <!-- invisible-code-block: python
        ```
        >>> if savedir:
        ...     fig.savefig(savedir / "iccs_update_bandpass.png", transparent=True)
        ...     import matplotlib.pyplot as plt
        ...     plt.close("all")
        ...     plt.style.use("dark_background")
        ...     fig, ax, widgets = update_bandpass(iccs)
        ...     fig.savefig(savedir / "iccs_update_bandpass-dark.png", transparent=True)
        ...     plt.style.use("default")
        >>>
        ```
        -->

        ![Interactively adjusting the bandpass filter parameters on the ICCS stack.](../../../images/sybil/iccs_update_bandpass.png#only-light){ loading=lazy }
        ![Interactively adjusting the bandpass filter parameters on the ICCS stack.](../../../images/sybil/iccs_update_bandpass-dark.png#only-dark){ loading=lazy }
    """
    _orig_apply = iccs.bandpass_apply
    _orig_fmin = iccs.bandpass_fmin
    _orig_fmax = iccs.bandpass_fmax
    _orig_corners = iccs.corners

    _BANDPASS_CACHE_SIZE = 8

    def _quantise_freq(f: float, sig_figs: int = 4) -> float:
        """Round *f* to *sig_figs* significant figures for use as a cache key."""
        if f <= 0:
            return f
        magnitude = 10 ** (sig_figs - 1 - int(np.floor(np.log10(f))))
        return round(f * magnitude) / magnitude

    nyquist = 0.5 / iccs.max_delta.total_seconds()
    _freq_eps = nyquist * 1e-4  # open-bound approximation matching bandpass constraints
    _log_min = np.log(_freq_eps)
    # Use a slightly tighter upper bound near Nyquist to keep inter-slider
    # constraints safely within the global slider range.
    _log_max = np.log(nyquist - 2 * _freq_eps)

    fig, ax = plt.subplots(figsize=(10, 7.7))

    _debounce_timer: list[TimerBase | None] = [None]
    _updating: list[bool] = [False]
    update_fn: Callable[[], None]

    def _current_causal() -> bool:
        return radio.value_selected == "Causal"

    bottom_margin = 0.38 if use_matrix_image else 0.35

    if use_matrix_image:
        axes_image, _ = _draw_matrix_image_initial(
            ax, iccs, context, all_seismograms, False
        )
        fig.subplots_adjust(
            bottom=bottom_margin, left=_left_margin(True), right=0.95, top=0.93
        )
        _matrix_cache: OrderedDict[
            tuple[bool, float, float, bool, int], npt.NDArray[np.floating]
        ] = OrderedDict()

        def _update_matrix() -> None:
            apply = check.get_status()[0]
            fmin = max(_quantise_freq(float(np.exp(slider_fmin.val))), _freq_eps)
            fmax = min(
                _quantise_freq(float(np.exp(slider_fmax.val))), nyquist - _freq_eps
            )
            if fmin >= fmax:
                return
            causal = _current_causal()
            corners = int(slider_corners.val)
            key = (apply, fmin, fmax, causal, corners)
            if key not in _matrix_cache:
                if len(_matrix_cache) >= _BANDPASS_CACHE_SIZE:
                    _matrix_cache.popitem(last=False)
                if not _apply_bandpass_params(iccs, apply, fmin, fmax, corners):
                    return
                if context:
                    seismograms = (
                        iccs.context_seismograms_causal
                        if causal
                        else iccs.context_seismograms
                    )
                else:
                    seismograms = (
                        iccs.cc_seismograms_causal if causal else iccs.cc_seismograms
                    )
                mask = _make_mask(iccs, all_seismograms)
                ccs = np.abs(np.compress(mask, iccs.ccs))
                matrix = np.array([s.data for s, m in zip(seismograms, mask) if m])
                _matrix_cache[key] = matrix[np.argsort(ccs)[::-1]]
            else:
                _matrix_cache.move_to_end(key)
            axes_image.set_data(_matrix_cache[key])
            ax.set_xlabel(f"Time relative to pick [s]{_variant_suffix(apply, causal)}")
            ax.set_ylabel(
                "Seismograms sorted by correlation coefficient"
                + f"{_variant_suffix(apply, False)}"
            )
            fig.canvas.draw_idle()

        update_fn = _update_matrix
    else:
        seis_lines, stack_line, scalar_mappable, colorbar = _draw_stack_initial(
            ax, iccs, context, all_seismograms, False
        )
        fig.subplots_adjust(
            bottom=bottom_margin, left=_left_margin(False), right=0.95, top=0.93
        )
        _stack_cache: OrderedDict[
            tuple[bool, float, float, bool, int],
            tuple[
                list[npt.NDArray[np.floating]],
                npt.NDArray[np.floating],
                npt.NDArray[np.floating],
            ],
        ] = OrderedDict()

        def _update_stack() -> None:
            apply = check.get_status()[0]
            fmin = max(_quantise_freq(float(np.exp(slider_fmin.val))), _freq_eps)
            fmax = min(
                _quantise_freq(float(np.exp(slider_fmax.val))), nyquist - _freq_eps
            )
            if fmin >= fmax:
                return
            causal = _current_causal()
            corners = int(slider_corners.val)
            key = (apply, fmin, fmax, causal, corners)
            if key not in _stack_cache:
                if len(_stack_cache) >= _BANDPASS_CACHE_SIZE:
                    _stack_cache.popitem(last=False)
                if not _apply_bandpass_params(iccs, apply, fmin, fmax, corners):
                    return
                if context:
                    seismograms = (
                        iccs.context_seismograms_causal
                        if causal
                        else iccs.context_seismograms
                    )
                    stack = iccs.context_stack_causal if causal else iccs.context_stack
                else:
                    seismograms = (
                        iccs.cc_seismograms_causal if causal else iccs.cc_seismograms
                    )
                    stack = iccs.stack_causal if causal else iccs.stack
                mask = _make_mask(iccs, all_seismograms)
                ccs = np.abs(np.compress(mask, iccs.ccs))
                seis_data = [s.data.copy() for s, m in zip(seismograms, mask) if m]
                _stack_cache[key] = (seis_data, stack.data.copy(), ccs)
            else:
                _stack_cache.move_to_end(key)
            seis_data, stack_data, ccs = _stack_cache[key]
            new_norm = PowerNorm(vmin=np.min(ccs), vmax=np.max(ccs), gamma=2)
            new_colors = IccsDefaults.stack_cmap(new_norm(ccs))
            for line, data, color in zip(seis_lines, seis_data, new_colors):
                line.set_ydata(data)
                line.set_color(color)
            stack_line.set_ydata(stack_data)
            scalar_mappable.set_norm(new_norm)
            colorbar.update_normal(scalar_mappable)
            colorbar.set_label(
                f"|Correlation coefficient|{_variant_suffix(apply, False)}"
            )
            ax.set_ylabel(f"Normalised amplitude{_variant_suffix(apply, causal)}")
            fig.canvas.draw_idle()

        update_fn = _update_stack

    ax.set_title("Update bandpass filter parameters.")

    gs_widgets = _widget_gridspec(
        fig, height_ratios=[1, 1, 1, 1.8], top=bottom_margin - 0.07, bottom=0.02
    )
    ax_fmin = fig.add_subplot(gs_widgets[0, 1:11])
    ax_fmax = fig.add_subplot(gs_widgets[1, 1:11])
    ax_corners = fig.add_subplot(gs_widgets[2, 1:11])
    ax_check = fig.add_subplot(gs_widgets[3, 1:4])
    ax_radio = fig.add_subplot(gs_widgets[3, 4:8])
    ax_save = fig.add_subplot(gs_widgets[3, 8:10])
    ax_cancel = fig.add_subplot(gs_widgets[3, 10:12])

    # Align left edges with the main plot's y-axis, not the grid's column 1.
    check_pos = ax_check.get_position()
    shift = _left_margin(use_matrix_image) - check_pos.x0
    ax_check.set_position(check_pos.translated(shift, 0))
    radio_pos = ax_radio.get_position()
    ax_radio.set_position(radio_pos.translated(shift, 0))

    _fg = plt.rcParams.get("text.color", "black")
    ax_check.set_frame_on(True)
    for spine in ax_check.spines.values():
        spine.set_edgecolor(_fg)
    check = CheckButtons(
        ax_check,
        ["Apply bandpass"],
        [iccs.bandpass_apply],
        label_props={"color": [_fg], "fontsize": [11]},
        frame_props={"edgecolor": _fg, "s": 200},
        check_props={"color": _fg, "s": 200},
    )
    ax_radio.set_frame_on(True)
    ax_radio.set_xticks([])
    ax_radio.set_yticks([])
    for spine in ax_radio.spines.values():
        spine.set_edgecolor(_fg)
    ax_radio.text(
        0.5,
        0.85,
        "Preview as (not saved)",
        ha="center",
        va="top",
        fontsize=9,
        color=_fg,
        transform=ax_radio.transAxes,
    )
    # Give RadioButtons its own axes covering only the box's lower portion,
    # so it doesn't centre itself over the label above. fig.add_axes, not
    # ax_radio.inset_axes: an inset axes' locator recomputes its position
    # from the parent on every redraw, discarding set_position() below.
    radio_box_pos = ax_radio.get_position()
    ax_radio_toggles = fig.add_axes(
        (
            radio_box_pos.x0,
            radio_box_pos.y0,
            radio_box_pos.width,
            radio_box_pos.height * 0.55,
        )
    )
    ax_radio_toggles.set_frame_on(False)
    radio = RadioButtons(
        ax_radio_toggles,
        ["Zero-phase", "Causal"],
        active=0,
        layout="horizontal",
        label_props={"color": [_fg, _fg], "fontsize": [11, 11]},
    )
    # RadioButtons has no option to centre the group; measure how much
    # width it actually used, once rendered, and shift to centre it.
    fig.canvas.draw()
    content_right = radio.labels[-1].get_window_extent().x1
    toggles_bbox = ax_radio_toggles.get_window_extent()
    content_fraction = (content_right - toggles_bbox.x0) / toggles_bbox.width
    toggles_pos = ax_radio_toggles.get_position()
    offset = (1 - content_fraction) / 2 * toggles_pos.width
    ax_radio_toggles.set_position(toggles_pos.translated(offset, 0))
    slider_fmin = Slider(
        ax_fmin, "fmin [Hz]", _log_min, _log_max, valinit=np.log(iccs.bandpass_fmin)
    )
    slider_fmax = Slider(
        ax_fmax, "fmax [Hz]", _log_min, _log_max, valinit=np.log(iccs.bandpass_fmax)
    )
    slider_corners = Slider(
        ax_corners,
        "corners",
        valmin=1,
        valmax=max(8, iccs.corners),
        valinit=iccs.corners,
        valstep=1,
    )
    # Show Hz values rather than the internal log values
    slider_fmin.valtext.set_text(f"{iccs.bandpass_fmin:.3f}")
    slider_fmax.valtext.set_text(f"{iccs.bandpass_fmax:.3f}")
    # Set initial inter-slider bounds
    slider_fmax.valmin = np.log(iccs.bandpass_fmin + _freq_eps)
    slider_fmin.valmax = np.log(iccs.bandpass_fmax - _freq_eps)

    if not iccs.bandpass_apply:
        slider_fmin.set_active(False)
        slider_fmax.set_active(False)
        slider_corners.set_active(False)

    def _schedule_update() -> None:
        if _debounce_timer[0] is not None:
            _debounce_timer[0].stop()
        timer = fig.canvas.new_timer(interval=150)
        timer.single_shot = True
        timer.add_callback(update_fn)
        _debounce_timer[0] = timer
        timer.start()

    def _on_fmin_change(_: float) -> None:
        if _updating[0]:
            return
        _updating[0] = True
        fmin = float(np.exp(slider_fmin.val))
        slider_fmax.valmin = np.log(fmin + _freq_eps)
        if float(slider_fmax.val) <= np.log(fmin + _freq_eps):
            slider_fmax.set_val(np.log(fmin + _freq_eps))
        _updating[0] = False
        slider_fmin.valtext.set_text(f"{fmin:.3f}")
        slider_fmax.valtext.set_text(f"{np.exp(slider_fmax.val):.3f}")
        _schedule_update()

    def _on_fmax_change(_: float) -> None:
        if _updating[0]:
            return
        _updating[0] = True
        fmax = float(np.exp(slider_fmax.val))
        slider_fmin.valmax = np.log(fmax - _freq_eps)
        if float(slider_fmin.val) >= np.log(fmax - _freq_eps):
            slider_fmin.set_val(np.log(fmax - _freq_eps))
        _updating[0] = False
        slider_fmin.valtext.set_text(f"{np.exp(slider_fmin.val):.3f}")
        slider_fmax.valtext.set_text(f"{fmax:.3f}")
        _schedule_update()

    def _on_corners_change(_: float) -> None:
        _schedule_update()

    def _on_check(_label: str | None) -> None:
        apply = check.get_status()[0]
        slider_fmin.set_active(apply)
        slider_fmax.set_active(apply)
        slider_corners.set_active(apply)
        _schedule_update()

    def _on_radio_change(_label: str | None) -> None:
        _schedule_update()

    slider_fmin.on_changed(_on_fmin_change)
    slider_fmax.on_changed(_on_fmax_change)
    slider_corners.on_changed(_on_corners_change)
    check.on_clicked(_on_check)
    radio.on_clicked(_on_radio_change)

    def on_save(_: Event) -> None:
        if _debounce_timer[0] is not None:
            _debounce_timer[0].stop()
        fmin = float(np.exp(slider_fmin.val))
        fmax = float(np.exp(slider_fmax.val))
        corners = int(slider_corners.val)
        apply = check.get_status()[0]
        if not _apply_bandpass_params(iccs, apply, fmin, fmax, corners):
            return
        if not return_fig:
            plt.close(fig)

    def on_cancel(_: Event) -> None:
        if _debounce_timer[0] is not None:
            _debounce_timer[0].stop()
        # Restore via _apply_bandpass_params, not direct field assignment:
        # the live preview only writes iccs's bandpass_*/corners fields on a
        # cache miss, so they can be an arbitrary previously-visited slider
        # combination at this point, and restoring the original values in a
        # fixed order can spuriously fail the same way a fixed-order update
        # can (see _apply_bandpass_params's docstring).
        _apply_bandpass_params(iccs, _orig_apply, _orig_fmin, _orig_fmax, _orig_corners)
        if not return_fig:
            plt.close(fig)

    b_save, b_cancel = _add_save_cancel_buttons(ax_save, ax_cancel, on_save, on_cancel)

    if return_fig:
        return (
            fig,
            ax,
            (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
        )
    plt.show()
    return None
