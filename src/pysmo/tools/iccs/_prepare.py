"""Preparation of seismograms and stacks for ICCS."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

import numpy as np
import numpy.typing as npt
import pandas as pd
from attrs import cmp_using, define, field

from pysmo import MiniSeismogram
from pysmo._types.seismogram import SeismogramEndtimeMixin
from pysmo.functions import (
    crop,
    detrend,
    normalize,
    pad,
    resample,
    window,
)
from pysmo.tools.signal import bandpass, causal_band
from pysmo.tools.utils import average_datetimes

from ._types import IccsSeismogram

if TYPE_CHECKING:
    from ._iccs import ICCS


def _compute_ramp(
    ramp_width: float | pd.Timedelta,
    window_pre: pd.Timedelta,
    window_post: pd.Timedelta,
) -> pd.Timedelta:
    """Compute the taper ramp duration, matching `pysmo.functions.window` semantics.

    Args:
        ramp_width: Ramp width, either as an absolute `pandas.Timedelta`
            or as a non-negative float fraction of the window duration.
        window_pre: Start of the window relative to the pick (negative).
        window_post: End of the window relative to the pick (positive).

    Returns:
        Absolute ramp duration as a `pandas.Timedelta`.
    """
    if isinstance(ramp_width, pd.Timedelta):
        return ramp_width
    return ramp_width * (window_post - window_pre)


@define
class _EphemeralSeismogram(SeismogramEndtimeMixin):
    """A Seismogram class used internally in ICCS to store the prepared seismograms.

    This class is not intended for use outside of the ICCS class, and is not
    exposed in the public API. It is used to store the prepared seismograms
    (i.e. the seismograms that are cropped, tapered, and normalised based on
    the current pick and time window) for use in the cross-correlation and
    stacking. The data in these seismograms are modified on the fly when the
    picks and time windows are updated, but they are not intended to be modified
    directly by users.

    When `bandpass_apply` is `False`, the `*_causal` properties return the
    exact same objects as their zero-phase counterparts, not copies; an
    in-place mutation through one name would be visible through the other.
    """

    parent_seismogram: IccsSeismogram
    """The parent `IccsSeismogram` this ephemeral seismogram is derived from."""

    begin_time: pd.Timestamp = field(init=False)
    """Seismogram begin time."""

    delta: pd.Timedelta = field(init=False)
    """Seismogram sampling interval."""

    data: npt.NDArray[np.floating] = field(init=False, eq=cmp_using(eq=np.array_equal))
    """Seismogram data."""

    def __attrs_post_init__(self) -> None:
        self.begin_time = self.parent_seismogram.begin_time
        self.delta = self.parent_seismogram.delta
        self.data = self.parent_seismogram.data.copy()


def _current_pick(seismogram: IccsSeismogram) -> pd.Timestamp:
    """Return `refined_pick`, or `initial_pick` if it is not set."""
    if pd.isnull(seismogram.refined_pick):
        return seismogram.initial_pick
    return seismogram.refined_pick


def _prepare_seismograms(
    instance: ICCS, add_context: bool = False, causal: bool = False
) -> list[_EphemeralSeismogram]:
    """Prepare cc_seismograms or context_seismograms."""

    if not instance.seismograms:
        return []

    ephemeral_seismograms: list[_EphemeralSeismogram] = []

    min_delta = instance.min_delta

    for seismogram in instance.seismograms:
        pick = _current_pick(seismogram)
        window_start = pick + instance.window_pre
        window_end = pick + instance.window_post

        ephemeral_seismogram = _EphemeralSeismogram(parent_seismogram=seismogram)

        if instance.bandpass_apply:
            if causal:
                freqmin, freqmax = causal_band(
                    instance.bandpass_fmin, instance.bandpass_fmax, instance.corners
                )
            else:
                freqmin, freqmax = instance.bandpass_fmin, instance.bandpass_fmax
            bandpass(
                ephemeral_seismogram,
                freqmin,
                freqmax,
                corners=instance.corners * 2 if causal else instance.corners,
                zerophase=not causal,
            )

        if not np.isclose(
            ephemeral_seismogram.delta.total_seconds(), min_delta.total_seconds()
        ):
            resample(ephemeral_seismogram, min_delta)

        if add_context:
            context_window_start = window_start - instance.context_width
            context_window_end = window_end + instance.context_width

            if (
                context_window_start < seismogram.begin_time
                or context_window_end > seismogram.end_time
            ):
                pad(
                    ephemeral_seismogram,
                    context_window_start,
                    context_window_end,
                    mode="linear_ramp",
                    end_values=(0, 0),
                )

            crop(ephemeral_seismogram, context_window_start, context_window_end)
            detrend(ephemeral_seismogram)
            normalize(ephemeral_seismogram, window_start, window_end)
        else:
            window(ephemeral_seismogram, window_start, window_end, instance.ramp_width)
            normalize(ephemeral_seismogram)

        if seismogram.flip:
            ephemeral_seismogram.data *= -1

        ephemeral_seismograms.append(ephemeral_seismogram)

    # If all seismograms have the same length, return them now.
    if len(lengths := {len(s.data) for s in ephemeral_seismograms}) == 1:
        return ephemeral_seismograms

    # Shorten seismograms if necessary and return (floating-point precision
    # can cause small differences in length after resampling). We cut off
    # at the end so the `begin_time` will not change.
    for s in ephemeral_seismograms:
        s.data = s.data[: min(lengths)]
    return ephemeral_seismograms


def _create_stack(seismograms: Sequence[_EphemeralSeismogram]) -> MiniSeismogram:
    """Create a stack by averaging all selected seismograms.

    Args:
        seismograms: Prepared seismograms to stack.

    Returns:
        A new seismogram whose data are the sample-wise mean of the selected
        input seismograms.

    Raises:
        ValueError: If no seismograms are selected.
    """
    if not seismograms:
        raise ValueError("Cannot create stack: no seismograms are loaded.")
    selected = [p for p in seismograms if p.parent_seismogram.select]
    if not selected:
        raise ValueError(
            "Cannot create stack: no seismograms are selected. "
            + "Ensure at least one seismogram has select=True before accessing the stack."
        )
    begin_time = average_datetimes([p.begin_time for p in selected])
    delta = selected[0].delta
    data = np.mean(
        np.array([p.data for p in selected]),
        axis=0,
    )
    return MiniSeismogram(begin_time=begin_time, delta=delta, data=data)
