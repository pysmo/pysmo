from collections.abc import Callable
from contextlib import AbstractContextManager

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from pysmo.tools.iccs import ICCS
from pysmo.tools.iccs.plot import (
    update_bandpass,
)
from pysmo.tools.iccs.plot._bandpass import _apply_bandpass_params
from tests.tools.iccs.plot._helpers import _click_button


def test_update_bandpass_returns_types(iccs_instance: ICCS) -> None:
    """update_bandpass returns (Figure, Axes, widgets_tuple)."""
    iccs_instance()
    result = update_bandpass(iccs_instance, return_fig=True)
    fig, ax, widgets = result
    _, _, _, _, _, _, _ = widgets
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    plt.close(fig)


def test_update_bandpass_matrix_image_returns_types(iccs_instance: ICCS) -> None:
    """update_bandpass with use_matrix_image=True returns correct types."""
    iccs_instance()
    result = update_bandpass(iccs_instance, use_matrix_image=True, return_fig=True)
    fig, ax, _ = result
    assert isinstance(fig, Figure)
    assert isinstance(ax, Axes)
    plt.close(fig)


def test_update_bandpass_save_applies_values(iccs_instance: ICCS) -> None:
    """Clicking Save propagates slider/checkbox values to iccs."""
    iccs_instance()
    iccs_instance.bandpass_apply = True
    orig_fmin = iccs_instance.bandpass_fmin
    orig_fmax = iccs_instance.bandpass_fmax

    (
        fig,
        ax,
        (
            check,
            slider_fmin,
            slider_fmax,
            slider_corners,
            radio,
            b_save,
            b_cancel,
        ),
    ) = update_bandpass(iccs_instance, return_fig=True)

    new_fmin = orig_fmin + 0.1
    new_fmax = orig_fmax - 0.1
    slider_fmin.set_val(np.log(new_fmin))
    slider_fmax.set_val(np.log(new_fmax))

    _click_button(b_save)

    assert iccs_instance.bandpass_fmin == pytest.approx(new_fmin)
    assert iccs_instance.bandpass_fmax == pytest.approx(new_fmax)
    assert iccs_instance.bandpass_apply is True
    plt.close(fig)


def test_update_bandpass_cancel_leaves_unchanged(iccs_instance: ICCS) -> None:
    """Clicking Cancel restores the original bandpass parameters."""
    iccs_instance()
    orig_apply = iccs_instance.bandpass_apply
    orig_fmin = iccs_instance.bandpass_fmin
    orig_fmax = iccs_instance.bandpass_fmax

    (
        fig,
        ax,
        (
            check,
            slider_fmin,
            slider_fmax,
            slider_corners,
            radio,
            b_save,
            b_cancel,
        ),
    ) = update_bandpass(iccs_instance, return_fig=True)

    slider_fmin.set_val(np.log(orig_fmin + 0.1))
    slider_fmax.set_val(np.log(orig_fmax - 0.1))

    _click_button(b_cancel)

    assert iccs_instance.bandpass_apply == orig_apply
    assert iccs_instance.bandpass_fmin == pytest.approx(orig_fmin)
    assert iccs_instance.bandpass_fmax == pytest.approx(orig_fmax)
    plt.close(fig)


def test_update_bandpass_save_with_apply_false(iccs_instance: ICCS) -> None:
    """Toggling Apply bandpass off and saving sets bandpass_apply to False."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    (
        fig,
        ax,
        (
            check,
            slider_fmin,
            slider_fmax,
            slider_corners,
            radio,
            b_save,
            b_cancel,
        ),
    ) = update_bandpass(iccs_instance, return_fig=True)

    # Toggle the checkbox off
    check.set_active(0)

    _click_button(b_save)

    assert iccs_instance.bandpass_apply is False
    plt.close(fig)


def test_update_bandpass_sliders_locked_consistently_when_apply_false(
    iccs_instance: ICCS,
) -> None:
    """fmin, fmax, and corners sliders are all inactive together when Apply bandpass starts off."""
    iccs_instance()
    iccs_instance.bandpass_apply = False

    (
        fig,
        ax,
        (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
    ) = update_bandpass(iccs_instance, return_fig=True)

    assert slider_fmin.active is False
    assert slider_fmax.active is False
    assert slider_corners.active is False
    plt.close(fig)


def test_update_bandpass_sliders_toggle_consistently_with_apply(
    iccs_instance: ICCS,
) -> None:
    """Toggling Apply bandpass locks/unlocks fmin, fmax, and corners sliders together."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    (
        fig,
        ax,
        (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
    ) = update_bandpass(iccs_instance, return_fig=True)

    assert slider_fmin.active is True
    assert slider_fmax.active is True
    assert slider_corners.active is True

    check.set_active(0)  # toggle off

    assert slider_fmin.active is False
    assert slider_fmax.active is False
    assert slider_corners.active is False

    check.set_active(0)  # toggle back on

    assert slider_fmin.active is True
    assert slider_fmax.active is True
    assert slider_corners.active is True
    plt.close(fig)


def _make_immediate_timer(_canvas: object, interval: int = 0) -> object:
    """Test helper: replaces canvas.new_timer with one that fires synchronously."""

    class _T:
        def __init__(self) -> None:
            self.single_shot = False
            self._fn: Callable[[], None] | None = None

        def add_callback(self, fn: Callable[[], None]) -> None:
            self._fn = fn

        def start(self) -> None:
            if self._fn is not None:
                self._fn()

        def stop(self) -> None:
            pass

    return _T()


def _immediate_timer_patch() -> AbstractContextManager[object]:
    """Return a patch that replaces canvas.new_timer with a synchronous timer.

    Discovers the actual canvas class at call time so the patch works regardless
    of which Matplotlib backend is active (TkAgg, Agg, Qt, etc.).
    """
    import unittest.mock

    tmp = plt.figure()
    canvas_cls = type(tmp.canvas)
    plt.close(tmp)
    return unittest.mock.patch.object(canvas_cls, "new_timer", _make_immediate_timer)


def test_update_bandpass_live_preview_stack(iccs_instance: ICCS) -> None:
    """Slider change triggers _update_stack and mutates iccs during live preview."""
    iccs_instance()
    iccs_instance.bandpass_apply = True
    new_fmin = iccs_instance.bandpass_fmin + 0.05

    with _immediate_timer_patch():
        (
            fig,
            ax,
            (
                check,
                slider_fmin,
                slider_fmax,
                slider_corners,
                radio,
                b_save,
                b_cancel,
            ),
        ) = update_bandpass(iccs_instance, return_fig=True)
        slider_fmin.set_val(np.log(new_fmin))

    assert iccs_instance.bandpass_fmin == pytest.approx(new_fmin)
    plt.close(fig)


def test_update_bandpass_live_preview_matrix(iccs_instance: ICCS) -> None:
    """Slider change triggers _update_matrix and mutates iccs during live preview."""
    iccs_instance()
    iccs_instance.bandpass_apply = True
    new_fmin = iccs_instance.bandpass_fmin + 0.05

    with _immediate_timer_patch():
        (
            fig,
            ax,
            (
                check,
                slider_fmin,
                slider_fmax,
                slider_corners,
                radio,
                b_save,
                b_cancel,
            ),
        ) = update_bandpass(iccs_instance, use_matrix_image=True, return_fig=True)
        slider_fmin.set_val(np.log(new_fmin))

    assert iccs_instance.bandpass_fmin == pytest.approx(new_fmin)
    plt.close(fig)


def test_update_bandpass_colorbar_label_updates_live_with_apply_toggle(
    iccs_instance: ICCS,
) -> None:
    """Toggling Apply bandpass updates the colorbar's "(zero-phase)" suffix live, not just at initial draw."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    with _immediate_timer_patch():
        (
            fig,
            ax,
            (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
        ) = update_bandpass(iccs_instance, return_fig=True)
        colorbar_ax = next(
            a for a in fig.axes if "Correlation coefficient" in a.get_ylabel()
        )
        assert "(zero-phase)" in colorbar_ax.get_ylabel()

        check.set_active(0)  # toggle Apply bandpass off; _on_check schedules an update

    assert "(zero-phase)" not in colorbar_ax.get_ylabel()
    plt.close(fig)


def test_update_bandpass_label_correct_on_cache_hit_after_apply_toggle(
    iccs_instance: ICCS,
) -> None:
    """Regression test: the variant label must reflect the current widget
    state even on a cache hit, not a possibly-stale `iccs.bandpass_apply`.

    `iccs.bandpass_apply` is only reassigned inside `_update_matrix`'s/
    `_update_stack`'s cache-*miss* branch. Revisiting an already-cached key
    is a cache *hit*, which never touches `iccs.bandpass_apply` — before
    this fix, the label suffix was computed from that (possibly stale)
    attribute instead of the widget's actual current state, so it could
    show the wrong suffix (or wrongly omit/include it) purely because of
    what the *previous* toggle happened to leave behind, not what's
    currently selected.

    Needs three toggles, not two: the first two are cache *misses* (correct
    under both the old and new code, since a miss always writes
    `iccs.bandpass_apply` correctly) — only the third revisits an
    already-cached key and actually exercises the hit path where the bug
    lived.
    """
    iccs_instance()
    iccs_instance.bandpass_apply = True

    with _immediate_timer_patch():
        (
            fig,
            ax,
            (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
        ) = update_bandpass(iccs_instance, return_fig=True)

        check.set_active(0)  # apply=False: cache miss, populates that key
        assert "(zero-phase)" not in ax.get_ylabel()
        check.set_active(0)  # apply=True: cache miss (first time), populates that key
        assert "(zero-phase)" in ax.get_ylabel()
        check.set_active(0)  # apply=False again: cache HIT on the first key
        assert "(zero-phase)" not in ax.get_ylabel()

    plt.close(fig)


def test_update_bandpass_radio_default_is_zerophase(iccs_instance: ICCS) -> None:
    """The causal/zero-phase radio defaults to Zero-phase."""
    iccs_instance()
    fig, ax, (_, _, _, _, radio, _, _) = update_bandpass(iccs_instance, return_fig=True)
    assert radio.value_selected == "Zero-phase"
    plt.close(fig)


def test_update_bandpass_radio_toggle_updates_preview(iccs_instance: ICCS) -> None:
    """Toggling the radio button re-renders the preview without error."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    with _immediate_timer_patch():
        fig, ax, (_, _, _, _, radio, _, _) = update_bandpass(
            iccs_instance, return_fig=True
        )
        radio.set_active(1)  # "Causal"

    assert radio.value_selected == "Causal"
    plt.close(fig)


def test_update_bandpass_corners_save_applies_value(iccs_instance: ICCS) -> None:
    """Clicking Save propagates the corners slider value to iccs.corners."""
    iccs_instance()
    iccs_instance.bandpass_apply = True

    (
        fig,
        ax,
        (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
    ) = update_bandpass(iccs_instance, return_fig=True)

    slider_corners.set_val(4)
    _click_button(b_save)

    assert iccs_instance.corners == 4
    plt.close(fig)


def test_update_bandpass_corners_cancel_leaves_unchanged(iccs_instance: ICCS) -> None:
    """Clicking Cancel restores the original corners value."""
    iccs_instance()
    iccs_instance.bandpass_apply = True
    orig_corners = iccs_instance.corners

    (
        fig,
        ax,
        (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
    ) = update_bandpass(iccs_instance, return_fig=True)

    slider_corners.set_val(orig_corners + 2)
    _click_button(b_cancel)

    assert iccs_instance.corners == orig_corners
    plt.close(fig)


def test_update_bandpass_corners_slider_not_clamped_above_default_max(
    iccs_instance: ICCS,
) -> None:
    """Regression test: corners above the slider's default valmax=8 must not be
    silently clamped and overwritten on an untouched save.

    `matplotlib.widgets.Slider` silently clamps `valinit` to `valmax` when
    out of range — with a fixed `valmax=8`, setting `iccs.corners=12` before
    opening this dialog would previously mean the slider displayed (and, on
    an untouched Save, wrote back) 8 instead of 12. `valmax` must be computed
    as `max(8, iccs.corners)`.
    """
    iccs_instance()
    iccs_instance.bandpass_apply = True
    iccs_instance.corners = 12

    (
        fig,
        ax,
        (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
    ) = update_bandpass(iccs_instance, return_fig=True)

    assert slider_corners.val == 12

    # Save without touching the corners slider must not overwrite the value.
    _click_button(b_save)
    assert iccs_instance.corners == 12
    plt.close(fig)


def test_apply_bandpass_params_avoids_stale_intermediate_rejection(
    iccs_instance: ICCS,
) -> None:
    """A fixed write order (fmin, fmax, corners) can reject a jointly-valid target; a safe order doesn't."""
    iccs_instance.corners = 1
    iccs_instance.bandpass_fmin = 0.3
    iccs_instance.bandpass_fmax = 1.0

    assert _apply_bandpass_params(iccs_instance, True, 0.5, 2.0, 4)

    assert iccs_instance.bandpass_apply is True
    assert iccs_instance.bandpass_fmin == pytest.approx(0.5)
    assert iccs_instance.bandpass_fmax == pytest.approx(2.0)
    assert iccs_instance.corners == 4


def test_apply_bandpass_params_returns_false_on_invalid_target(
    iccs_instance: ICCS,
) -> None:
    """An invalid target combination is rejected and iccs is left unchanged."""
    iccs_instance.bandpass_apply = True
    orig_fmin = iccs_instance.bandpass_fmin
    orig_fmax = iccs_instance.bandpass_fmax
    orig_corners = iccs_instance.corners

    assert not _apply_bandpass_params(iccs_instance, True, 0.5, 1.0, 1)

    assert iccs_instance.bandpass_fmin == orig_fmin
    assert iccs_instance.bandpass_fmax == orig_fmax
    assert iccs_instance.corners == orig_corners


def test_update_bandpass_causal_preview_ignores_invalid_combination(
    iccs_instance: ICCS,
) -> None:
    """Dragging into a combination causal_band would invert doesn't raise or mutate iccs.

    Each slider change triggers its own debounced write, so fmin/fmax move
    first (each individually valid against the still-default corners=2:
    causal_band(0.5, 2.0, 2) and causal_band(0.5, 1.0, 2) both hold), then
    lowering corners to 1 is the step that actually inverts the band
    (causal_band(0.5, 1.0, 1) does not). That last write must be silently
    refused (matching the existing fmin >= fmax guard's behaviour), not
    raise from inside the debounced timer callback, leaving corners at its
    last valid value.
    """
    iccs_instance()
    iccs_instance.bandpass_apply = True
    orig_corners = iccs_instance.corners

    with _immediate_timer_patch():
        (
            fig,
            ax,
            (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
        ) = update_bandpass(iccs_instance, return_fig=True)
        radio.set_active(1)  # "Causal"
        slider_fmin.set_val(np.log(0.5))
        slider_fmax.set_val(np.log(1.0))
        slider_corners.set_val(1)  # refused: causal_band(0.5, 1.0, 1) inverts

    assert iccs_instance.bandpass_fmin == pytest.approx(0.5)
    assert iccs_instance.bandpass_fmax == pytest.approx(1.0)
    assert iccs_instance.corners == orig_corners
    plt.close(fig)


def test_update_bandpass_causal_save_ignores_invalid_combination(
    iccs_instance: ICCS,
) -> None:
    """Clicking Save in an invalid causal-band combination doesn't raise or mutate iccs.

    Mirrors the preview guard's silent-refusal behaviour: with the sliders
    left at fmin=0.5, fmax=1.0, corners=1 (causal_band(0.5, 1.0, 1)
    inverts), Save must refuse rather than propagate the uncaught
    ValueError bandpass_fmin/bandpass_fmax/corners' own validators would
    otherwise raise.
    """
    iccs_instance()
    iccs_instance.bandpass_apply = True
    orig_fmin = iccs_instance.bandpass_fmin
    orig_fmax = iccs_instance.bandpass_fmax
    orig_corners = iccs_instance.corners

    (
        fig,
        ax,
        (check, slider_fmin, slider_fmax, slider_corners, radio, b_save, b_cancel),
    ) = update_bandpass(iccs_instance, return_fig=True)
    radio.set_active(1)  # "Causal"
    slider_fmin.set_val(np.log(0.5))
    slider_fmax.set_val(np.log(1.0))
    slider_corners.set_val(1)

    _click_button(b_save)  # must not raise

    assert iccs_instance.bandpass_fmin == pytest.approx(orig_fmin)
    assert iccs_instance.bandpass_fmax == pytest.approx(orig_fmax)
    assert iccs_instance.corners == orig_corners
    plt.close(fig)
