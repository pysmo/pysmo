from pysmo import Seismogram
import numpy as np


def xcorr(seis1: Seismogram, seis2: Seismogram, lagsamp: int, normalize: bool = True) -> np.ndarray:
    """
    Cross-correlates real arrays a and v, using numpy.correlate
    with mode = valid, which means that the length of the array that
    is returned equals 2*(length(a) - length(v)).
    For example: a is a time series and v is a template.
    If you're interested in cross-correlation of two signals with duration z x-axis units
    (e.g. seconds) of two arrays over -y and +y maximum shifts (lags) in x-axis units
    (e.g. seconds), then please make sure that array a begins at x=-y and ends at x=z+y.
    Array v (e.g. the template) may start at the same time, but could instead start
    at x=0 and end at x=z. (z = signal duration, y = maximum lag of interest (+ & -)).
    Output is normalized with autocorrelation of v (squared norm of v).

    :param seis1: Seismogram object containing array a.
    :type seismogram: pysmo.Seismogram
    :param seis2: Seismogram object containing array v.
    :type seismogram: pysmo.Seismogram
    :param lagsamp: Lag duration.
    :type int
    :param normalize: If true, returned array is normalized
    :type bool
    :returns: Cross correlated numpy array.
    :rtype: np.ndarray
    """

    a, v = seis1.data, seis2.data

    if len(a) >= len(v):
        v2 = v[lagsamp:len(v)-lagsamp] if len(a) == len(v) else v
        autov = np.dot(v2, v2)
        xc = np.correlate(a, v2, mode='valid')
    else:
        autov = np.dot(v, v)
        xc = np.correlate(v, a, mode='valid')[::-1]

    if not normalize:
        autov = 1

    return xc/autov
