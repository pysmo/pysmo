from pysmo import Seismogram
from copy import deepcopy
from typing import overload, Literal
import numpy as np


@overload
def envelope(
    seismogram: Seismogram, Tn: float, alpha: float, clone: Literal[False] = ...
) -> None: ...


@overload
def envelope[T: Seismogram](
    seismogram: T, Tn: float, alpha: float, clone: Literal[True]
) -> T: ...


def envelope[T: Seismogram](
    seismogram: T, Tn: float, alpha: float, clone: bool = False
) -> T | None:
    """
    Calculates the envelope of a gaussian filtered seismogram.

    Args:
        seismogram: Name of the seismogram object passed to this function.
        Tn: Center period of Gaussian filter [in seconds]
        alpha: Set alpha (which determines filterwidth)
        clone: If True, return a new Seismogram object with the filtered data. If False, modify the input seismogram in place.

    Returns:
        Seismogram containing the envelope

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import envelope
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope_seis = envelope(seis, Tn, alpha, clone=True)
        >>>
        ```
    """
    if clone:
        seismogram = deepcopy(seismogram)
    seismogram.data = _gauss(seismogram, Tn, alpha)[0]
    return seismogram if clone else None


@overload
def gauss(
    seismogram: Seismogram, Tn: float, alpha: float, clone: Literal[False] = ...
) -> None: ...


@overload
def gauss[T: Seismogram](
    seismogram: T, Tn: float, alpha: float, clone: Literal[True]
) -> T: ...


def gauss[T: Seismogram](
    seismogram: T, Tn: float, alpha: float, clone: bool = False
) -> T | None:
    """
    Returns a gaussian filtered seismogram.

    Args:
        seismogram: Name of the SAC object passed to this function.
        Tn: Center period of Gaussian filter [in seconds]
        alpha: Set alpha (which determines filterwidth)

    Returns:
        Gaussian filtered seismogram.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import gauss
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> Tn = 50 # Center Gaussian filter at 50s period
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> gauss_seis = gauss(seis, Tn, alpha, clone=True)
        >>>
        ```
    """
    if clone:
        seismogram = deepcopy(seismogram)
    seismogram.data = _gauss(seismogram, Tn, alpha)[1]
    return seismogram if clone else None


def _gauss(
    seismogram: Seismogram, Tn: float, alpha: float
) -> tuple[np.ndarray, np.ndarray]:
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
