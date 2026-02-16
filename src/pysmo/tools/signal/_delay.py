from pysmo import Seismogram
from datetime import timedelta
from scipy.signal import correlate as _correlate
from scipy.stats.mstats import pearsonr as _pearsonr
import numpy as np
import math

__all__ = ["delay"]


def delay(
    seismogram1: Seismogram,
    seismogram2: Seismogram,
    total_delay: bool = False,
    max_shift: timedelta | None = None,
    abs_max: bool = False,
) -> tuple[timedelta, float]:
    """
    Cross correlates two seismograms to determine signal delay.

    This function is a wrapper around the
    [`scipy.signal.correlate`][scipy.signal.correlate] function. The default
    behaviour is to call the correlate function with `#!py mode="full"` using
    the full length data of the input seismograms. This is the most robust
    option, but also the slowest.

    If an approximate delay is known (e.g. because a particular phase is being
    targeted using a computed arrival time), the search space can be limited
    by setting the `max_shift` parameter to a value. The length of the
    seismogram data used for the cross-correlation is then set such that the
    calculated delay lies within +/- `max_shift`.

    Note:
        `max_shift` intentionally does *not* take the begin times of the
        seismograms into consideration. Thus, calling `#!py delay()` with
        `#!py total_delay=True` may return a delay that is larger than
        `max_shift`.

    Implications of setting the `max_shift` parameter are as follows:

    - This mode requires the seismograms to be of equal length.
    - If the true delay (i.e. the amount of time the seismograms _should_ be
      shifted by) lies within the `max_shift` range, and also produces the
      highest correlation, the delay time returned is identical for both
      methods.
    - If the true delay lies outside the `max_shift` range and produces the
      highest correlation, the delay time returned will be incorrect when
      `max_shift` is set.
    - In the event that the true delay lies within the `max_shift` range but
      the maximum signal correlation occurs outside, it will be correctly
      retrieved when the `max_shift` parameter is set, while not setting it
      yields an incorrect result.


    Parameters:
        seismogram1: First seismogram to use for cross correlation.
        seismogram2: Second seismogram to use for cross correlation.
        total_delay: Include the difference in `begin_time` in the delay.
        max_shift: Maximum (absolute) length of the delay.
        abs_max: Return the delay corresponding to absolute maximum.

    Returns:
        delay: Time delay of the second seismogram with respect to the first.
        ccnorm: Normalised cross correlation value of the overlapping
            seismograms *after* shifting (uses
            [`scipy.stats.mstats.pearsonr`][scipy.stats.mstats.pearsonr] for
            the calculation). This value ranges from -1 to 1, with 1 indicating
            a perfect correlation, 0 indicating no correlation, and -1
            indicating a perfect anti-correlation.

    Examples:
        To illustration the use of the `delay()` function, we read a seismogram
        from a SAC file and then generate a second seismogram from it by
        modifying it with a shift in the data and a shift in the begin time.
        This means the true delay is known, and we are able to compare the
        computed delays with this known delay:

        ```python
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import detrend, clone_to_mini
        >>> from pysmo.tools.signal import delay
        >>> from datetime import timedelta
        >>> import numpy as np
        >>>
        >>> # Create a Seismogram from a SAC file and detrend it:
        >>> seis1 = SAC.from_file("example.sac").seismogram
        >>> detrend(seis1)
        >>>
        >>> # Create a second seismogram from the first with
        >>> # a different begin_time and a shift in the data:
        >>> seis2 = clone_to_mini(MiniSeismogram, seis1)
        >>> nroll = 1234
        >>> seis2.data = np.roll(seis2.data, nroll)
        >>> begin_time_delay = timedelta(seconds=100)
        >>> seis2.begin_time += begin_time_delay
        >>>
        >>> # The signal delay is the number of samples shifted * delta:
        >>> (signal_delay := nroll * seis1.delta).total_seconds()
        24.68
        >>>
        >>> # Call the delay function with the two seismograms and verify
        >>> # that the caclulated_delay is equal to the known signal delay:
        >>> calculated_delay, _ = delay(seis1, seis2)
        >>> calculated_delay == signal_delay
        True
        >>>
        ```

        As we know what the true delay is, we can mimic a scenario where an
        approximate delay is known prior to the cross-correlation, which can be
        used to limit the search space and speed up the calculation. Here we
        assign a value of the known signal delay plus 1 second to the
        `max_shift` parameter:

        ```python
        >>> max_shift = signal_delay + timedelta(seconds=1)
        >>> calculated_delay, _ = delay(seis1, seis2, max_shift=max_shift)
        >>> # As before, the calculated delay should be equal to the signal delay:
        >>> calculated_delay == signal_delay
        True
        >>>
        ```

        Setting `total_delay=True`, we also takes into account the difference
        in `begin_time` between the two seismograms:

        ```python
        >>> calculated_delay, _ = delay(seis1, seis2, total_delay=True, max_shift=signal_delay+timedelta(seconds=1))
        >>> # With `total_delay=True`, the calculated delay should be equal to
        >>> # the signal delay plus the begin time difference:
        >>> calculated_delay == signal_delay + (seis1.begin_time - seis2.begin_time)
        True
        >>>
        ```

        To demonstrate usage of the `abs_max` parameter, we flip the sign of
        the second seismogram data:

        ```python
        >>> seis2.data *= -1
        >>> calculated_delay, ccnorm = delay(seis1, seis2)
        >>> # Without `abs_max=True`, the calculated delay is no longer equal
        >>> # to the true signal delay (as expected):
        >>> calculated_delay == signal_delay
        False
        >>> # The normalised cross correlation value is also not very high
        >>> ccnorm
        np.float64(0.4267205)
        >>>
        >>> calculated_delay, ccnorm = delay(seis1, seis2, abs_max=True)
        >>> # with `abs_max=True`, the signal delay is again retrieved:
        >>> calculated_delay == signal_delay
        True
        >>> # And, as the signals are completely opposite, the normalised
        >>> # cross correlation value is -1:
        >>> np.testing.assert_approx_equal(ccnorm, -1)
        >>>
        ```
    """

    if seismogram1.delta != seismogram2.delta:
        raise ValueError("Input seismograms must have the same sampling rate.")

    if max_shift is not None and len(seismogram1) != len(seismogram2):
        raise ValueError(
            "Input seismograms must be of equal length when using `max_shift`."
        )

    data1, data2 = seismogram1.data, seismogram2.data
    delta = seismogram1.delta

    if max_shift is not None:
        max_lag_in_samples = math.ceil(max_shift / delta)
        zeros_to_add = np.zeros(max_lag_in_samples)
        data1 = np.append(zeros_to_add, data1)
        data1 = np.append(data1, zeros_to_add)
        corr = _correlate(data1, data2, mode="valid")
    else:
        corr = _correlate(data1, data2, mode="full")

    corr_index = np.argmax(corr)

    if abs_max and np.max(corr) < -1 * np.min(corr):
        corr_index = np.argmin(corr)

    if max_shift is not None:
        shift = -int(corr_index - max_lag_in_samples)
    else:
        shift = int(np.size(data2) - 1 - corr_index)

    delay = shift * delta

    # find overlapping parts of seismograms after allignment
    if shift < 0:
        data1 = data1[-shift:]
    else:
        data2 = data2[shift:]
    if np.size(data1) > np.size(data2):
        data1 = data1[: np.size(data2)]
    else:
        data2 = data2[: np.size(data1)]

    covr, _ = _pearsonr(data1, data2)

    if total_delay:
        delay += seismogram1.begin_time - seismogram2.begin_time

    return delay, covr
