"""Functions for spectral analysis."""

from typing import Literal

import numpy as np
import numpy.typing as npt
from scipy import signal

from pysmo import Seismogram

__all__ = ["psd"]


def psd(
    seismogram: Seismogram,
    nperseg: int,
    nfft: int,
    scaling: Literal["density", "spectrum"] = "density",
    include_dc: bool = False,
) -> tuple[npt.NDArray[np.floating], npt.NDArray[np.floating]]:
    """Calculate the Power Spectral Density (PSD) of a Seismogram using Welch's method.

    This is a convenience wrapper around [`welch`][scipy.signal.welch].

    Args:
        seismogram: The Seismogram object.
        nperseg: Length of each segment for Welch's method.
        nfft: Length of the FFT used.
        scaling: The scaling method for the PSD.
        include_dc: If `False`, the f=0Hz component is dropped, since it
            is typically undefined on the log-frequency axis PSDs are
            conventionally plotted on. Set to `True` to keep it, e.g. for
            a total-power calculation.

    Returns:
        A tuple containing the frequencies and the Power Spectral Density.
    """
    sampling_frequency = 1 / seismogram.delta.total_seconds()
    freqs, psd_values = signal.welch(
        seismogram.data,
        fs=sampling_frequency,
        nperseg=nperseg,
        nfft=nfft,
        scaling=scaling,
    )
    if include_dc:
        return freqs, psd_values
    return freqs[1:], psd_values[1:]
