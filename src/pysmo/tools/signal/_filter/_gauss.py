from copy import deepcopy
from typing import Literal, overload

import numpy as np

from pysmo import Seismogram

from ._registry import register_filter


@overload
def envelope(
    seismogram: Seismogram, fc: float, alpha: float, *, clone: Literal[False] = ...
) -> None: ...


@overload
def envelope[T: Seismogram](
    seismogram: T, fc: float, alpha: float, *, clone: Literal[True]
) -> T: ...


@register_filter
def envelope[T: Seismogram](
    seismogram: T, fc: float, alpha: float, *, clone: bool = False
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

    Raises:
        ValueError: If `seismogram.data` is empty, or `seismogram.delta` is
            not positive.

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
    seismogram: Seismogram, fc: float, alpha: float, *, clone: Literal[False] = ...
) -> None: ...


@overload
def gauss[T: Seismogram](
    seismogram: T, fc: float, alpha: float, *, clone: Literal[True]
) -> T: ...


@register_filter
def gauss[T: Seismogram](
    seismogram: T, fc: float, alpha: float, *, clone: bool = False
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

    Raises:
        ValueError: If `seismogram.data` is empty, or `seismogram.delta` is
            not positive.

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
        W:  Frequency axis (Hz) for each FFT bin, including negative
            frequencies. The Gaussian window is applied to |W| so that Hn
            stays conjugate-symmetric (hn is real).
        Hn: Gaussian-filtered spectrum — input spectrum multiplied by the
            Gaussian window centred at fc.
        hn: Filtered seismogram in the time domain (inverse FFT of Hn).
        qn: Hilbert transform of hn, obtained as the imaginary part of the
            analytic signal built from Hn (zero negative frequencies,
            double positive ones — the standard FFT-domain Hilbert
            transform).
        an: Instantaneous amplitude (envelope) — sqrt(hn² + qn²).
    """
    if len(seismogram.data) == 0:
        raise ValueError("Cannot apply a Gaussian filter to an empty seismogram.")
    dt = seismogram.delta.total_seconds()
    if dt <= 0:
        raise ValueError("Seismogram delta must be positive.")
    npts = len(seismogram.data)
    spec = np.fft.fft(seismogram.data)
    W = np.fft.fftfreq(npts, d=dt)
    Hn = spec * np.exp(-1 * alpha * ((np.abs(W) - fc) / fc) ** 2)
    hn = np.fft.ifft(Hn).real

    analytic_weights = np.zeros(npts)
    analytic_weights[0] = 1
    half = npts // 2
    if npts % 2 == 0:
        analytic_weights[1:half] = 2
        analytic_weights[half] = 1
    else:
        analytic_weights[1 : half + 1] = 2
    analytic_signal = np.fft.ifft(Hn * analytic_weights)
    an = np.abs(analytic_signal)  # envelope
    return (an, hn)
