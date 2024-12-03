"""This module provides functions that are not intended to be used directly.
Reasons for putting functions here:

    - They do not use pysmo types as input or output
    - They are used in 'real' pysmo functions and pysmo
      classes within methods at the same time
"""

from pyproj import Geod
from pysmo.lib.defaults import DEFAULT_ELLPS
from pysmo import Seismogram
import numpy as np
import numpy.typing as npt
import scipy.signal


def lib_azdist(
    lat1: float, lon1: float, lat2: float, lon2: float, ellps: str = DEFAULT_ELLPS
) -> tuple[float, float, float]:
    """Return forward/backazimuth and distance using pyproj (proj4 bindings).

    Parameters:
        lat1: latitude of point 1.
        lon1: longitude of point 1.
        lat2: latitude of point 2.
        lon2: longitude of point 2.
        ellps: Ellipsoid to use for calculations.

    Returns:
        az: Azimuth
        baz: Backazimuth
        dist: Distance between the points in metres.
    """
    g = Geod(ellps=ellps)
    az, baz, dist = g.inv(lons1=lon1, lats1=lat1, lons2=lon2, lats2=lat2)

    # Prefer positive bearings
    if az < 0:
        az += 360
    if baz < 0:
        baz += 360
    return az, baz, dist


def lib_normalize(seismogram: Seismogram) -> npt.NDArray:
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalised data.
    """
    norm = np.max(np.abs(seismogram.data))
    return seismogram.data / norm


def lib_detrend(seismogram: Seismogram) -> npt.NDArray:
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalised data.
    """
    return scipy.signal.detrend(seismogram.data)


def lib_resample(seismogram: Seismogram, delta: float) -> npt.NDArray:
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
