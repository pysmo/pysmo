from copy import deepcopy
from typing import Literal, overload

import numpy as np

from pysmo import Seismogram

from ._registry import register_filter


@overload
def envelope(
    seismogram: Seismogram, fc: float, alpha: float, clone: Literal[False] = ...
) -> None: ...


@overload
def envelope[T: Seismogram](
    seismogram: T, fc: float, alpha: float, clone: Literal[True]
) -> T: ...


@register_filter
def envelope[T: Seismogram](
    seismogram: T, fc: float, alpha: float, clone: bool = False
) -> T | None:
    """Calculates the envelope of a gaussian filtered seismogram.

    Args:
        seismogram: Seismogram object.
        fc: Centre frequency of the Gaussian filter (in Hz).
        alpha: Dimensionless shape parameter controlling the filter width.
            Larger values produce a narrower (more selective) filter.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Seismogram containing the envelope.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import envelope
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> fc = 0.02 # Centre Gaussian filter at 0.02 Hz (50s period)
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> envelope_seis = envelope(seis, fc, alpha, clone=True)
        >>>
        ```
    """
    if clone:
        seismogram = deepcopy(seismogram)
    seismogram.data = _gauss(seismogram, fc, alpha)[0]
    return seismogram if clone else None


@overload
def gauss(
    seismogram: Seismogram, fc: float, alpha: float, clone: Literal[False] = ...
) -> None: ...


@overload
def gauss[T: Seismogram](
    seismogram: T, fc: float, alpha: float, clone: Literal[True]
) -> T: ...


@register_filter
def gauss[T: Seismogram](
    seismogram: T, fc: float, alpha: float, clone: bool = False
) -> T | None:
    """Returns a gaussian filtered seismogram.

    Args:
        seismogram: Seismogram object.
        fc: Centre frequency of the Gaussian filter (in Hz).
        alpha: Dimensionless shape parameter controlling the filter width.
            Larger values produce a narrower (more selective) filter.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Gaussian filtered seismogram.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.signal import gauss
        >>> seis = SAC.from_file("example.sac").seismogram
        >>> fc = 0.02 # Centre Gaussian filter at 0.02 Hz (50s period)
        >>> alpha = 50 # Set alpha (which determines filterwidth) to 50
        >>> gauss_seis = gauss(seis, fc, alpha, clone=True)
        >>>
        ```
    """
    if clone:
        seismogram = deepcopy(seismogram)
    seismogram.data = _gauss(seismogram, fc, alpha)[1]
    return seismogram if clone else None


def _gauss(
    seismogram: Seismogram, fc: float, alpha: float
) -> tuple[np.ndarray, np.ndarray]:
    """Apply a Gaussian filter and compute the analytic signal.

    Implements the multiple filter technique of Herrmann (1973)[^1].

    [^1]: Herrmann, R. B. (1973). Some aspects of band-pass filtering of surface
        waves. *Bulletin of the Seismological Society of America*, 63(2), 663–671.

    Variable names follow the paper's notation:
        W:  Frequency axis (Hz), 0 to Nyquist.
        Hn: Gaussian-filtered spectrum — input spectrum multiplied by the
            Gaussian window centred at fc.
        hn: Filtered seismogram in the time domain (inverse FFT of Hn).
        Qn: Spectrum of the Hilbert-transformed filtered signal, constructed
            by rotating Hn by 90° (real → imaginary, imaginary → −real).
        qn: Hilbert transform of hn in the time domain (inverse FFT of Qn).
        an: Instantaneous amplitude (envelope) — sqrt(hn² + qn²).
    """
    Nyq = 0.5 / seismogram.delta.total_seconds()
    npts = len(seismogram.data)
    spec = np.fft.fft(seismogram.data)
    W = np.array(np.linspace(0, Nyq, npts))
    Hn = spec * np.exp(-1 * alpha * ((W - fc) / fc) ** 2)
    Qn = complex(0, 1) * Hn.real - Hn.imag
    hn = np.fft.ifft(Hn).real
    qn = np.fft.ifft(Qn).real
    an = np.sqrt(hn**2 + qn**2)  # envelope
    return (an, hn)
