import numpy as np
import numpy.typing as npt
from copy import deepcopy
from pysmo import Seismogram


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
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import envelope
        >>> seis = SAC.from_file('example.sac').seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope_seis = envelope(seis, Tn, alpha)
        >>>
        ```
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
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import gauss
        >>> seis = SAC.from_file('example.sac').seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> gauss_seis = gauss(seis, Tn, alpha)
        >>>
        ```
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
