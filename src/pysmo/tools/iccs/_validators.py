"""Attribute validators and cache-clearing hooks for the ICCS class."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from attrs import Attribute, validate

from pysmo.tools.signal import causal_band
from pysmo.typing import (
    NonNegativeNumber,
    NonNegativeTimedelta,
)

from ._prepare import _compute_ramp

if TYPE_CHECKING:
    from ._iccs import ICCS


def _on_setattr_clear_cache[T](instance: ICCS, attribute: Attribute[T], value: T) -> T:
    """Setter that causes cached attributes to be cleared when their value changes."""

    current = getattr(instance, attribute.name)

    if current is value:
        return value

    if isinstance(current, np.ndarray) and isinstance(value, np.ndarray):
        if np.array_equal(current, value):
            return value

    elif (current == value) is True:
        return value

    instance.clear_cache()

    if attribute.name == "seismograms":
        object.__setattr__(instance, "seismograms", value)
        try:
            validate(instance)
        except Exception:
            # Roll back so a failed reassignment doesn't leave the instance
            # holding the (invalid) new value despite the raised exception.
            object.__setattr__(instance, "seismograms", current)
            raise

    return value


def _on_setattr_clear_context_cache[T](
    instance: ICCS, attribute: Attribute[T], value: T
) -> T:
    """Setter for `context_width`: only the context caches depend on it."""
    if (current := getattr(instance, attribute.name)) is value or (
        current == value
    ) is True:
        return value
    instance._clear_context_caches()
    return value


def _validate_window_pre(
    instance: ICCS, attribute: Attribute[pd.Timedelta], value: pd.Timedelta
) -> None:
    """Ensure window_pre fits within all seismograms, accounting for the taper ramp."""
    ramp = _compute_ramp(instance.ramp_width, value, instance.window_post)
    if not (value >= instance.max_td_pre + ramp):
        raise ValueError("window_pre is too low for one or more seismograms.")


def _validate_window_post(
    instance: ICCS, attribute: Attribute[pd.Timedelta], value: pd.Timedelta
) -> None:
    """Ensure window_post fits within all seismograms, accounting for the taper ramp."""
    ramp = _compute_ramp(instance.ramp_width, instance.window_pre, value)
    if not (value <= instance.min_td_post - ramp):
        raise ValueError("window_post is too high for one or more seismograms.")


def _validate_bandpass_fmin(
    instance: ICCS, attribute: Attribute[float], value: float
) -> None:
    """Ensure bandpass_fmin is positive and below bandpass_fmax."""
    if value <= 0:
        raise ValueError("bandpass_fmin must be positive.")
    if value >= instance.bandpass_fmax:
        raise ValueError("bandpass_fmin must be less than bandpass_fmax.")
    try:
        causal_band(value, instance.bandpass_fmax, instance.corners)
    except ValueError:
        raise ValueError(
            "bandpass_fmin is too close to bandpass_fmax for the causal "
            + "variant's corrected passband at the current corners."
        ) from None


def _validate_bandpass_fmax(
    instance: ICCS, attribute: Attribute[float], value: float
) -> None:
    """Ensure bandpass_fmax is above bandpass_fmin and below the Nyquist frequency."""
    if value <= instance.bandpass_fmin:
        raise ValueError("bandpass_fmax must be greater than bandpass_fmin.")
    if instance.bandpass_apply and instance.seismograms:
        nyquist = 0.5 / instance.max_delta.total_seconds()
        if value >= nyquist:
            raise ValueError(
                f"bandpass_fmax must be below the Nyquist frequency ({nyquist} Hz)."
            )
    try:
        causal_band(instance.bandpass_fmin, value, instance.corners)
    except ValueError:
        raise ValueError(
            "bandpass_fmax is too close to bandpass_fmin for the causal "
            + "variant's corrected passband at the current corners."
        ) from None


def _validate_corners_causal_band(
    instance: ICCS, attribute: Attribute[int], value: int
) -> None:
    """Ensure corners doesn't invert the causal variant's corrected passband."""
    try:
        causal_band(instance.bandpass_fmin, instance.bandpass_fmax, value)
    except ValueError:
        raise ValueError(
            "corners is too low for the causal variant's corrected "
            + "passband at the current bandpass_fmin/bandpass_fmax."
        ) from None


def _validate_bandpass_apply(
    instance: ICCS, attribute: Attribute[bool], value: bool
) -> None:
    """Ensure Nyquist constraint is met when enabling the bandpass filter."""
    if value and instance.seismograms:
        nyquist = 0.5 / instance.max_delta.total_seconds()
        if instance.bandpass_fmax >= nyquist:
            raise ValueError(
                f"bandpass_fmax must be below the Nyquist frequency ({nyquist} Hz)."
            )


def _validate_ramp_width(
    instance: ICCS,
    attribute: Attribute[NonNegativeTimedelta | NonNegativeNumber],
    value: NonNegativeTimedelta | NonNegativeNumber,
) -> None:
    ramp = _compute_ramp(value, instance.window_pre, instance.window_post)
    if ramp < pd.Timedelta(0):
        raise ValueError("ramp_width must be non-negative.")
    if not (
        ramp <= instance.window_pre - instance.max_td_pre
        and ramp <= instance.min_td_post - instance.window_post
    ):
        raise ValueError("ramp_width is too high for one or more seismograms.")
