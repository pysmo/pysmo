"""Pick updates, convergence, and pick limits for ICCS."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from numpy.linalg import norm
from scipy.stats.mstats import pearsonr

from pysmo import Seismogram

from ._prepare import _compute_ramp, _current_pick
from ._types import ConvergenceMethod, IccsSeismogram

if TYPE_CHECKING:
    from ._iccs import ICCS


def _update_seismogram(
    delay: pd.Timedelta,
    cc: float | None,
    seismogram: IccsSeismogram,
    autoflip: bool,
    autoselect: bool,
    min_cc_for_autoselect: np.floating | float,
    current_window: tuple[pd.Timedelta, pd.Timedelta],
    ramp_width: pd.Timedelta | float,
) -> bool:
    """Update IccsSeismogram attributes based on cross-correlation results.

    Optionally toggles `flip` (if `autoflip` is True and the correlation
    coefficient is negative) and `select` (if `autoselect` is True and
    the absolute correlation coefficient is below the threshold). The pick
    `refined_pick` is updated unless the new value would move the window (including its
    taper ramp) outside the seismogram.

    Args:
        delay: Time shift from cross-correlation.
        cc: Normalised cross-correlation coefficient. If it is `None`,
            no changes to `flip` and `select` will be made.
        seismogram: Seismogram to update.
        autoflip: Automatically toggle the `flip` attribute.
        autoselect: Automatically toggle the `select` attribute.
        min_cc_for_autoselect: Threshold for `autoselect`.
        current_window: Current `(window_pre, window_post)` tuple.
        ramp_width: Current `ramp_width`, needed because
            `_prepare_seismograms` tapers the window and
            `pysmo.functions.window` rejects a pick with no room for the ramp.

    Returns:
        `True` if `refined_pick` was updated, `False` if the shift was refused.
    """
    if cc is not None:
        if autoflip and cc < 0:
            seismogram.flip = not seismogram.flip
            cc = abs(cc)

        if autoselect:
            seismogram.select = bool(cc >= min_cc_for_autoselect)

    updated_pick = _current_pick(seismogram) + delay
    ramp = _compute_ramp(ramp_width, current_window[0], current_window[1])
    limit_pre = seismogram.begin_time - current_window[0] + ramp
    limit_post = seismogram.end_time - current_window[1] - ramp

    if not limit_pre <= updated_pick <= limit_post:
        # stacklevel is caller-dependent: __call__ is 4 frames up, run_mccc is 3.
        # Use stacklevel=2 to point at the direct caller of _update_seismogram.
        warnings.warn(
            f"Refusing to update refined_pick for seismogram with initial_pick={seismogram.initial_pick}. "
            + "Would move out of limits - consider reducing window size.",
            stacklevel=2,
        )
        return False

    seismogram.refined_pick = updated_pick
    return True


def _calc_convergence(
    current_stack: Seismogram,
    prev_stack: Seismogram,
    method: ConvergenceMethod,
) -> float:
    """Calculate criterion of convergence.

    This function calculates a criterion of convergence based on the current and
    previous stack using one of the following methods:

    - Convergence by correlation coefficient.
    - Convergence by change of stack.

    Args:
        current_stack: Current stack.
        prev_stack: Stack from last iteration.
        method: Method of convergence criterion calculation.
    """
    if method == ConvergenceMethod.corrcoef:
        if np.array_equal(current_stack.data, prev_stack.data):
            return 0.0  # unchanged stack has converged; pearsonr would be NaN
        covr = float(pearsonr(current_stack.data, prev_stack.data)[0])
        # NaN (a constant stack) -> unconverged, not past the <= check.
        return 1 - covr if not np.isnan(covr) else float("inf")
    elif method == ConvergenceMethod.change:
        change = norm(current_stack.data - prev_stack.data, 1)
        denominator = norm(current_stack.data, 2)
        if denominator == 0:
            # A degenerate (all-zero) stack has no meaningful relative
            # change: 0.0 if it didn't actually change, otherwise treat it
            # as unconverged rather than raising/returning NaN.
            return 0.0 if change == 0 else float("inf")
        return float(change / denominator / len(current_stack.data))
    raise ValueError(f"Unknown convergence method: {method}.")


def _calc_valid_pick_range(instance: ICCS) -> tuple[pd.Timedelta, pd.Timedelta]:
    """Calculate the valid shift range for updating the pick.

    The pick delta must ensure there is enough space on either end of every
    seismogram (selected or not) to accommodate the time window and ramp,
    because `_prepare_seismograms` processes all seismograms.

    Args:
        instance: The `ICCS` instance to compute the valid range for.

    Returns:
        A `(min_pick_delta, max_pick_delta)` tuple of valid shift bounds.
    """
    if not instance.seismograms:
        return pd.Timedelta(days=-365 * 100), pd.Timedelta(days=365 * 100)

    td_pre_values = []
    td_post_values = []
    for s in instance.seismograms:
        pick = _current_pick(s)
        td_pre_values.append(s.begin_time - pick - instance.window_pre)
        td_post_values.append(s.end_time - pick - instance.window_post)

    ramp = instance.ramp_width_timedelta
    return max(td_pre_values) + ramp, min(td_post_values) - ramp
