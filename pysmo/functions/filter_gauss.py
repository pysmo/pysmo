import numpy as np
import copy
from pysmo import Seismogram


def envelope(seismogram: Seismogram, Tn: float, alpha: float) -> Seismogram:
    """
    Calculates the envelope of a gaussian filtered seismogram.

    :param name: Name of the seismogram object passed to this function.
    :type seismogram: pysmo.Seismogram
    :param Tn: Center period of Gaussian filter [in seconds]
    :type Tn: float
    :param alpha: Set alpha (which determines filterwidth)
    :type alpha: float
    :returns: seismogram containing the envelope

    Example::

        >>> from pysmo import SAC, envelope
        >>> seis = SAC.from_file('sacfile.sac').Seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope_seis = envelope(seis, Tn, alpha)
    """
    seis = copy.deepcopy(seismogram)
    seis.data = __gauss(seis, Tn, alpha)[0]
    return seis


def gauss(seismogram: Seismogram, Tn: float, alpha: float) -> Seismogram:
    """
    Returns a gaussian filtered seismogram.

    :param name: Name of the SAC object passed to this function.
    :type name: SAC
    :param Tn: Center period of Gaussian filter [in seconds]
    :type Tn: float
    :param alpha: Set alpha (which determines filterwidth)
    :type alpha: float
    :returns: gaussian filtered seismogram.

    Example usage::

        >>> from pysmo import SAC, gauss
        >>> seis = SAC.from_file('sacfile.sac').Seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> gauss_seis = gauss(seis, Tn, alpha)
    """
    seis = copy.deepcopy(seismogram)
    seis.data = __gauss(seis, Tn, alpha)[1]
    return seis


def __gauss(seis: Seismogram, Tn: float, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    Wn = 1 / float(Tn)
    Nyq = 0.5 / seis.sampling_rate
    npts = len(seis)
    spec = np.fft.fft(seis.data)
    W = np.array(np.linspace(0, Nyq, npts))
    Hn = spec * np.exp(-1 * alpha * ((W-Wn)/Wn)**2)
    Qn = complex(0, 1) * Hn.real - Hn.imag
    hn = np.fft.ifft(Hn).real
    qn = np.fft.ifft(Qn).real
    an = np.sqrt(hn**2 + qn**2)  # envelope
    return (an, hn)
