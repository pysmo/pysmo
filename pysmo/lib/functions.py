from pyproj import Geod
from pysmo.lib.defaults import DEFAULT_ELLPS
from pysmo import Seismogram
import numpy as np
import scipy.signal  # type: ignore


def _azdist(
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


def _normalize(seismogram: Seismogram) -> np.ndarray:
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalised data.
    """
    norm = np.max(np.abs(seismogram.data))
    return seismogram.data / norm


def _detrend(seismogram: Seismogram) -> np.ndarray:
    """Normalize the seismogram with its absolute max value

    Parameters:
        seismogram: Seismogram object.

    Returns:
        Normalised data.
    """
    return scipy.signal.detrend(seismogram.data)


def _resample(seismogram: Seismogram, sampling_rate: float) -> np.ndarray:
    """Resample Seismogram object data using the Fourier method.

    Parameters:
        seismogram: Seismogram object.
        sampling_rate: New sampling rate.

    Returns:
        Resampled data.

    Warning:
        sampling_rate attribute still needs to be set!
    """
    len_in = len(seismogram)
    sampling_rate_in = seismogram.sampling_rate
    len_out = int(len_in * sampling_rate_in / sampling_rate)
    return scipy.signal.resample(seismogram.data, len_out)
