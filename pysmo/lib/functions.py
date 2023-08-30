from pyproj import Geod
from pysmo.lib.defaults import DEFAULT_ELLPS


def azdist(lat1: float, lon1: float, lat2: float, lon2: float,
           ellps: str = DEFAULT_ELLPS) -> tuple[float, float, float]:
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
