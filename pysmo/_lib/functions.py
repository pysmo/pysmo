"""This module provides functions that are not intended to be used directly.
Reasons for putting functions here:

    - They do not use pysmo types as input or output
    - They are used in 'real' pysmo functions and pysmo
      classes within methods at the same time
"""

from typing import TYPE_CHECKING
import numpy as np
import numpy.typing as npt
import scipy.signal

if TYPE_CHECKING:
    from pysmo import Seismogram


def lib_normalize(seismogram: "Seismogram") -> npt.NDArray:
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalised data.
    """
    norm = np.max(np.abs(seismogram.data))
    return seismogram.data / norm


def lib_detrend(seismogram: "Seismogram") -> npt.NDArray:
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalised data.
    """
    return scipy.signal.detrend(seismogram.data)


def lib_resample(seismogram: "Seismogram", delta: float) -> npt.NDArray:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        delta: New sampling interval.

    Returns:
        Resampled data.

    Warning:
        interval attribute still needs to be set!
    """
    len_in = len(seismogram)
    delta_in = seismogram.delta
    len_out = int(len_in * delta_in / delta)
    return scipy.signal.resample(seismogram.data, len_out)
