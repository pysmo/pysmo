"""
This module provides functions commonly used in signal processing.

Functions:
    delay: Cross correlates two seismograms to determine signal delay.
    envelope: Calculates the envelope of a gaussian filtered seismogram.
    gauss: Returns a gaussian filtered seismogram.
"""

from datetime import timedelta
import numpy as np
import numpy.typing as npt
from copy import deepcopy
from math import ceil
from scipy.signal import correlate as _correlate
from scipy.stats import pearsonr as _pearsonr
from pysmo import Seismogram


def delay(
    seismogram1: Seismogram,
    seismogram2: Seismogram,
    max_delay: timedelta | None = None,
    allow_negative: bool = False,
) -> tuple[timedelta, float]:
    """
    Cross correlates two seismograms to determine signal delay.

    This functions is a wrapper around the
    [`#!py scipy.signal.correlate()`][scipy.signal.correlate] function.
    The default behavior is to call the correlate function with
    `#!py mode="full"` using the input seismograms directly. This is the most
    robust option, but also the slowest.

    When `max_delay` is set to a value, the search space is limited to
    +/- the equivalent number of samples for value. This is useful for finding
    the exact delay when an approximate delay time is known, and the input
    seismograms are windowed accordingly. This mode requires the seismograms to
    be of equal length.

    Implications of setting the `max_delay` parameter are the following:

    - If the true delay (i.e. the amount of time the seismograms _should_ be
      shifted by) lies within the `max_delay` range, and also produces the
      highest correlation, the delay time returned is identical for both
      methods.
    - If the true delay lies outside the `max_delay` range and produces the
      highest correlation, the delay time returned will be incorrect when
      `max_delay` is set.
    - In the event that the true delay lies within the `max_delay` range but
      the maximum signal correlation occurs outside, it will be correctly
      retrieved when the `max_delay` parameter is set, while not setting it
      yields an incorrect result.

    Warning:
        This function does not take into account the `begin_time` attribute of
        the input seismograms. Thus, using the output of this function directly
        aligns the data of the seismograms, but not the seismograms themselves.
        If that is desired, the difference between `begin_time` attribute of
        two seismograms needs be added to the delay calculated here.

    Parameters:
        seismogram1: First seismogram to cross correlate.
        seismogram2: Second seismogram to cross correlate.
        max_delay: Maximum length of the delay (positive or negative).
        allow_negative: Return the delay corresponding to the minium
            cross correlation value if its absolue value is larger than
            the maximum positive value.

    Returns:
        delay: Time delay of the second seismogram with respect to the first.
        ccnorm: Normalised cross correlation value of the overlapping
            seismograms *after* shifting. Always between -1 and 1.

    Examples:
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.classes import SAC
        >>> from pysmo.functions import detrend
        >>> from pysmo.tools.signal import delay
        >>> from datetime import timedelta
        >>> import numpy as np
        >>> my_sac = SAC.from_file('testfile.sac')
        >>> seis1 = detrend(my_sac.seismogram)
        >>> # create a second seismogram from the first with
        >>> # a different begin_time and a shift in the data.
        >>> seis2 = MiniSeismogram.clone(seis1, skip_data=True)
        >>> nroll = 1234
        >>> seis2.data = np.roll(seis1.data, nroll)
        >>> begin_time_delay = timedelta(seconds=100)
        >>> seis2.begin_time += begin_time_delay
        >>> signal_delay = nroll * seis1.delta
        >>> expected_delay = begin_time_delay + signal_delay
        >>> calculated_delay = delay(seis1, seis2, max_delay=signal_delay+timedelta(seconds=1)
        >>> expected_delay - calculated_delay
        datetime.timedelta(0)
    """
    if seismogram1.delta != seismogram2.delta:
        raise ValueError("Input seismograms must have the same sampling rate.")

    in1, in2 = seismogram1.data, seismogram2.data
    delta = seismogram1.delta
    mode = "full"

    if max_delay is not None:
        if len(in1) != len(in2):
            raise ValueError(
                "Input seismograms must be of equal length when using `max_delay`."
            )
        mode = "valid"
        max_lag_in_samples = ceil(max_delay / delta)
        zeros_to_add = np.zeros(max_lag_in_samples)
        in1 = np.append(zeros_to_add, in1)
        in1 = np.append(in1, zeros_to_add)

    corr = _correlate(in1, in2, mode=mode)  # type: ignore
    corr_index = np.argmax(corr)

    if allow_negative and np.max(corr) < -1 * np.min(corr):
        corr_index = np.argmin(corr)

    if max_delay is not None:
        shift = -int(corr_index - max_lag_in_samples)
    else:
        shift = int(len(in2) - 1 - corr_index)

    delay = shift * delta

    # find overlapping parts of seismograms after allignment
    if shift < 0:
        in1 = in1[-shift:]
    else:
        in2 = in2[shift:]
    if len(in1) > len(in2):
        in1 = in1[: len(in2)]
    else:
        in2 = in2[: len(in1)]

    covr, _ = _pearsonr(in1, in2)

    return delay, float(covr)


def envelope[T: Seismogram](seismogram: T, Tn: float, alpha: float) -> T:
    """
    Calculates the envelope of a gaussian filtered seismogram.

    Parameters:
        seismogram: Name of the seismogram object passed to this function.
        Tn: Center period of Gaussian filter [in seconds]
        alpha: Set alpha (which determines filterwidth)

    Returns:
        Seismogram containing the envelope

    Examples:
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import envelope
        >>> seis = SAC.from_file('sacfile.sac').seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope_seis = envelope(seis, Tn, alpha)
    """
    clone = deepcopy(seismogram)
    clone.data = _gauss(seismogram, Tn, alpha)[0]
    return clone


def gauss[T: Seismogram](seismogram: T, Tn: float, alpha: float) -> T:
    """
    Returns a gaussian filtered seismogram.

    Parameters:
        seismogram: Name of the SAC object passed to this function.
        Tn: Center period of Gaussian filter [in seconds]
        alpha: Set alpha (which determines filterwidth)

    Returns:
        Gaussian filtered seismogram.

    Examples:
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import gauss
        >>> seis = SAC.from_file('sacfile.sac').seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> gauss_seis = gauss(seis, Tn, alpha)
    """
    clone = deepcopy(seismogram)
    clone.data = _gauss(seismogram, Tn, alpha)[1]
    return clone


def _gauss(
    seismogram: Seismogram, Tn: float, alpha: float
) -> tuple[npt.NDArray, npt.NDArray]:
    Wn = 1 / float(Tn)
    Nyq = 0.5 / seismogram.delta.total_seconds()
    npts = len(seismogram)
    spec = np.fft.fft(seismogram.data)
    W = np.array(np.linspace(0, Nyq, npts))
    Hn = spec * np.exp(-1 * alpha * ((W - Wn) / Wn) ** 2)
    Qn = complex(0, 1) * Hn.real - Hn.imag
    hn = np.fft.ifft(Hn).real
    qn = np.fft.ifft(Qn).real
    an = np.sqrt(hn**2 + qn**2)  # envelope
    return (an, hn)
