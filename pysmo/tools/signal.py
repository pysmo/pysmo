import numpy as np
import numpy.typing as npt
from pysmo import Seismogram, MiniSeismogram
from scipy.signal import correlate  # type: ignore


def envelope(seismogram: Seismogram, Tn: float, alpha: float) -> MiniSeismogram:
    """
    Calculates the envelope of a gaussian filtered seismogram.

    Parameters:
        seismogram: Name of the seismogram object passed to this function.
        Tn: Center period of Gaussian filter [in seconds]
        alpha: Set alpha (which determines filterwidth)

    Returns:
        Seismogram containing the envelope

    Examples:
        >>> from pysmo import SAC
        >>> from pysmo.tools.signal import envelope
        >>> seis = SAC.from_file('sacfile.sac').seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope_seis = envelope(seis, Tn, alpha)
    """
    clone = MiniSeismogram.clone(seismogram, skip_data=True)
    clone.data = __gauss(seismogram, Tn, alpha)[0]
    return clone


def gauss(seismogram: Seismogram, Tn: float, alpha: float) -> Seismogram:
    """
    Returns a gaussian filtered seismogram.

    Parameters:
        seismogram: Name of the SAC object passed to this function.
        Tn: Center period of Gaussian filter [in seconds]
        alpha: Set alpha (which determines filterwidth)

    Returns:
        Gaussian filtered seismogram.

    Examples:
        >>> from pysmo import SAC
        >>> from pysmo.tools.signal import gauss
        >>> seis = SAC.from_file('sacfile.sac').seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> gauss_seis = gauss(seis, Tn, alpha)
    """
    clone = MiniSeismogram.clone(seismogram, skip_data=True)
    clone.data = __gauss(seismogram, Tn, alpha)[1]
    return clone


def __gauss(
    seis: Seismogram, Tn: float, alpha: float
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    Wn = 1 / float(Tn)
    Nyq = 0.5 / seis.delta
    npts = len(seis)
    spec = np.fft.fft(seis.data)
    W = np.array(np.linspace(0, Nyq, npts))
    Hn = spec * np.exp(-1 * alpha * ((W - Wn) / Wn) ** 2)
    Qn = complex(0, 1) * Hn.real - Hn.imag
    hn = np.fft.ifft(Hn).real
    qn = np.fft.ifft(Qn).real
    an = np.sqrt(hn**2 + qn**2)  # envelope
    return (an, hn)


def xcorr(
    seis1: Seismogram, seis2: Seismogram, lag: float, normalize: bool = True
) -> np.ndarray:
    """
    The function cross-correlates two real arrays, denoted as 'a' and 'v,' utilizing the
    [scipy.signal.correlate function](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.correlate.html#scipy.signal.correlate)
    with the 'valid' mode. In this mode, the resulting array's length is equal to 2 times
    the difference between the lengths of 'a' and 'v.' This operation is often applied to
    scenarios where 'a' represents a time series, while 'v' serves as a template. If you
    intend to perform cross-correlation between two signals, each with a duration of 'z'
    units along the x-axis (e.g., seconds), spanning both negative and positive shifts
    (lags) of 'y' units on the x-axis (e.g., seconds), it is crucial to ensure that the
    'a' array commences at x=-y and concludes at x=z+y. The 'v' array, representing the
    template, may begin at the same starting point or, alternatively, initiate at x=0 and
    terminate at x=z. Here, 'z' denotes the signal's duration, while 'y' signifies the
    maximum lag of interest, both in the positive and negative directions. The output is
    normalized with autocorrelation of v (squared norm of v).

    Parameters:
        seis1: Seismogram object containing array a.
        seis2: Seismogram object containing array v.
        lag: Lag duration in seconds.
        normalize: If true, returned array is normalized.

    Returns:
        Cross correlated numpy array.

    Examples:
        >>> from pysmo import SAC
        >>> from pysmo.tools.signal import xcorr
        >>> seis = SAC.from_file('sacfile.sac').seismogram
        >>> lag = 20 # Lag in seconds
        >>> # Create a lagged version of the original signal
        >>> shift = int(lag/seis.delta)
        >>> seis_lagged = MiniSeismogram.clone(seis, skip_data=True)
        >>> seis_lagged.data = np.roll(seis.data, shift)
        >>> # Cross Correlate the original signal and the lagged version
        >>> corr_arr = xcorr(seis, seis_lagged, lag)
    """

    a, v = seis1.data, seis2.data
    lagsamp = round(lag / seis1.delta)

    if len(a) >= len(v):
        v2 = v[lagsamp : len(v) - lagsamp] if len(a) == len(v) else v
        autov = np.dot(v2, v2)
        xc = correlate(a, v2, mode="valid")
    else:
        autov = np.dot(v, v)
        xc = correlate(v, a, mode="valid")[::-1]

    if not normalize:
        autov = 1

    return xc / autov
