"""Frequency-domain integration and differentiation."""

from copy import deepcopy
from typing import Literal, overload

import numpy as np

from pysmo import Seismogram

__all__ = ["differentiate", "integrate"]


@overload
def differentiate(seismogram: Seismogram, *, clone: Literal[False] = ...) -> None: ...


@overload
def differentiate[T: Seismogram](seismogram: T, *, clone: Literal[True]) -> T: ...


def differentiate[T: Seismogram](seismogram: T, *, clone: bool = False) -> T | None:
    r"""Differentiate a seismogram in the frequency domain.

    Multiplies the FFT of `seismogram.data` by $i\omega$ at each
    [`rfftfreq`][numpy.fft.rfftfreq] bin, then inverse transforms back to the
    time domain. The DC bin is correctly zeroed ($i\omega = 0$), since a
    constant offset differentiates to zero.

    Args:
        seismogram: Seismogram object.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Differentiated [`Seismogram`][pysmo.Seismogram] object if called with
        `clone=True`.

    Raises:
        ValueError: If `seismogram.data` is empty.
        ValueError: If `seismogram.delta` is not positive.

    Examples:
        A synthetic sine wave with a known closed-form derivative
        ($\omega \cos(\omega t)$) is used to verify the result:

        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.signal import differentiate
        >>> dt = 0.1
        >>> npts = 250  # an exact number of cycles of the 1 Hz signal below
        >>> t = np.arange(npts) * dt
        >>> omega = 2 * np.pi * 1.0
        >>> seismogram = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        ...     delta=pd.Timedelta(seconds=dt),
        ...     data=np.sin(omega * t),
        ... )
        >>> velocity = differentiate(seismogram, clone=True)
        >>> expected = omega * np.cos(omega * t)
        >>> np.allclose(velocity.data, expected, atol=1e-6)
        True
        >>>
        ```
    """
    if len(seismogram.data) == 0:
        raise ValueError("Cannot differentiate an empty seismogram.")
    if seismogram.delta.total_seconds() <= 0:
        raise ValueError("Seismogram delta must be positive.")

    if clone:
        seismogram = deepcopy(seismogram)

    dt = seismogram.delta.total_seconds()
    npts = len(seismogram.data)
    freqs = np.fft.rfftfreq(npts, d=dt)
    omega = 2 * np.pi * freqs

    spectrum = np.fft.rfft(seismogram.data)
    spectrum *= 1j * omega
    seismogram.data = np.fft.irfft(spectrum, n=npts)

    return seismogram if clone else None


@overload
def integrate(seismogram: Seismogram, *, clone: Literal[False] = ...) -> None: ...


@overload
def integrate[T: Seismogram](seismogram: T, *, clone: Literal[True]) -> T: ...


def integrate[T: Seismogram](seismogram: T, *, clone: bool = False) -> T | None:
    r"""Integrate a seismogram in the frequency domain.

    Divides the FFT of `seismogram.data` by $i\omega$ at each
    [`rfftfreq`][numpy.fft.rfftfreq] bin ($\omega > 0$), then inverse
    transforms back to the time domain. The DC bin is set to `0.0` rather
    than divided by. Working in the frequency domain avoids the unbounded
    low-frequency drift a cumulative time-domain integrator introduces.

    Args:
        seismogram: Seismogram object.
        clone: Operate on a clone of the input seismogram.

    Returns:
        Integrated [`Seismogram`][pysmo.Seismogram] object if called with
        `clone=True`.

    Raises:
        ValueError: If `seismogram.data` is empty.
        ValueError: If `seismogram.delta` is not positive.

    Examples:
        A synthetic cosine wave with a known closed-form integral
        ($\sin(\omega t)$) is used to verify the result:

        ```python
        >>> import numpy as np
        >>> import pandas as pd
        >>> from pysmo import MiniSeismogram
        >>> from pysmo.tools.signal import integrate
        >>> dt = 0.1
        >>> npts = 250  # an exact number of cycles of the 1 Hz signal below
        >>> t = np.arange(npts) * dt
        >>> omega = 2 * np.pi * 1.0
        >>> seismogram = MiniSeismogram(
        ...     begin_time=pd.Timestamp("2010-02-27T06:30:00Z"),
        ...     delta=pd.Timedelta(seconds=dt),
        ...     data=omega * np.cos(omega * t),
        ... )
        >>> displacement = integrate(seismogram, clone=True)
        >>> expected = np.sin(omega * t)
        >>> np.allclose(displacement.data, expected, atol=1e-6)
        True
        >>>
        ```
    """
    if len(seismogram.data) == 0:
        raise ValueError("Cannot integrate an empty seismogram.")
    if seismogram.delta.total_seconds() <= 0:
        raise ValueError("Seismogram delta must be positive.")

    if clone:
        seismogram = deepcopy(seismogram)

    dt = seismogram.delta.total_seconds()
    npts = len(seismogram.data)
    freqs = np.fft.rfftfreq(npts, d=dt)
    omega = 2 * np.pi * freqs

    spectrum = np.fft.rfft(seismogram.data)
    integrated_spectrum = np.zeros_like(spectrum)
    integrated_spectrum[1:] = spectrum[1:] / (1j * omega[1:])
    seismogram.data = np.fft.irfft(integrated_spectrum, n=npts)

    return seismogram if clone else None
