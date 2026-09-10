"""Frequency-domain integration and differentiation."""

import copy
from typing import Literal, overload

import numpy as np

from pysmo import Seismogram

__all__ = ["differentiate", "integrate"]


@overload
def differentiate(seismogram: Seismogram, *, replace: Literal[False] = ...) -> None: ...


@overload
def differentiate[T: Seismogram](seismogram: T, *, replace: Literal[True]) -> T: ...


def differentiate[T: Seismogram](seismogram: T, *, replace: bool = False) -> T | None:
    r"""Differentiate a seismogram in the frequency domain.

    Multiplies the FFT of `seismogram.data` by $i\omega$ at each
    [`rfftfreq`][numpy.fft.rfftfreq] bin, then inverse transforms back to the
    time domain. The DC bin is correctly zeroed ($i\omega = 0$), since a
    constant offset differentiates to zero. For an even-length signal the
    Nyquist bin is dropped: `irfft` requires it to be real, and $i\omega$
    makes it imaginary.

    Args:
        seismogram: Seismogram object.
        replace: Return a new seismogram and leave the input untouched,
            instead of modifying it in place. Not supported by every
            concrete type (see [`pysmo.functions`][]).

    Returns:
        Differentiated [`Seismogram`][pysmo.Seismogram] object if called with
        `replace=True`.

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
        >>> velocity = differentiate(seismogram, replace=True)
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

    dt = seismogram.delta.total_seconds()
    npts = len(seismogram.data)
    freqs = np.fft.rfftfreq(npts, d=dt)
    omega = 2 * np.pi * freqs

    spectrum = np.fft.rfft(seismogram.data)
    spectrum *= 1j * omega
    differentiated = np.fft.irfft(spectrum, n=npts)

    if replace:
        return copy.replace(seismogram, data=differentiated)  # type: ignore[arg-type]

    seismogram.data = differentiated
    return None


@overload
def integrate(seismogram: Seismogram, *, replace: Literal[False] = ...) -> None: ...


@overload
def integrate[T: Seismogram](seismogram: T, *, replace: Literal[True]) -> T: ...


def integrate[T: Seismogram](seismogram: T, *, replace: bool = False) -> T | None:
    r"""Integrate a seismogram in the frequency domain.

    Divides the FFT of `seismogram.data` by $i\omega$ at each
    [`rfftfreq`][numpy.fft.rfftfreq] bin ($\omega > 0$), then inverse
    transforms back to the time domain. The DC bin is set to `0.0` rather
    than divided by. For an even-length signal the Nyquist bin is dropped:
    `irfft` requires it to be real, and dividing by $i\omega$ makes it
    imaginary. Working in the frequency domain avoids the unbounded
    low-frequency drift a cumulative time-domain integrator introduces.

    Args:
        seismogram: Seismogram object.
        replace: Return a new seismogram and leave the input untouched,
            instead of modifying it in place. Not supported by every
            concrete type (see [`pysmo.functions`][]).

    Returns:
        Integrated [`Seismogram`][pysmo.Seismogram] object if called with
        `replace=True`.

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
        >>> displacement = integrate(seismogram, replace=True)
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

    dt = seismogram.delta.total_seconds()
    npts = len(seismogram.data)
    freqs = np.fft.rfftfreq(npts, d=dt)
    omega = 2 * np.pi * freqs

    spectrum = np.fft.rfft(seismogram.data)
    integrated_spectrum = np.zeros_like(spectrum)
    integrated_spectrum[1:] = spectrum[1:] / (1j * omega[1:])
    integrated = np.fft.irfft(integrated_spectrum, n=npts)

    if replace:
        return copy.replace(seismogram, data=integrated)  # type: ignore[arg-type]

    seismogram.data = integrated
    return None
