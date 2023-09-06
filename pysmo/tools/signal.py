import numpy as np
from pysmo import Seismogram, MiniSeismogram


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
