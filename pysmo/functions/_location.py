"""Pysmo provides functions that perform common operations on the types of data that
match pysmo's types.
"""

from pysmo import Location
from pysmo._lib.defaults import DEFAULT_ELLPS
from pyproj import Geod

__all__ = ["azimuth", "backazimuth", "distance"]


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


def azimuth(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate azimuth between two points.

    info:
        For more information see: <https://pyproj4.github.io/pyproj/stable>

    Parameters:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Azimuth in degrees from location 1 to location 2.

    Examples:
        >>> from pysmo import SAC, azimuth
        >>> sacobj = SAC.from_file('testfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth(sacobj.event, sacobj.station)
        181.9199258637492
        >>> # Use Clarke 1966 instead of default
        >>> azimuth(sacobj.event, sacobj.station, ellps='clrk66')
        181.92001941872516
    """
    return _azdist(
        lat1=location_1.latitude,
        lon1=location_1.longitude,
        lat2=location_2.latitude,
        lon2=location_2.longitude,
        ellps=ellps,
    )[0]


def backazimuth(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate backazimuth (in DEG) between two points.

    info:
        For more information see: <https://pyproj4.github.io/pyproj/stable>

    Parameters:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Backzimuth in degrees from point 2 to point 1

    Examples:
        >>> from pysmo import SAC, backazimuth
        >>> sacobj = SAC.from_file('testfile.sac')
        >>> # the SAC class provides both event and station
        >>> backazimuth(sacobj.event, sacobj.station)
        2.4677533885335947
        >>> # Use Clarke 1966 instead of default
        >>> backazimuth(sacobj.event, sacobj.station, ellps='clrk66')
        2.467847115319614
    """
    return _azdist(
        lat1=location_1.latitude,
        lon1=location_1.longitude,
        lat2=location_2.latitude,
        lon2=location_2.longitude,
        ellps=ellps,
    )[1]


def distance(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate the great circle distance (in metres) between two locations.

    info:
        For more information see: <https://pyproj4.github.io/pyproj/stable>

    Parameters:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for distance calculation

    Returns:
        Great Circle Distance in metres.

    Examples:
        >>> from pysmo import SAC, distance
        >>> sacobj = SAC.from_file('testfile.sac')
        >>> # the SAC class provides both event and station
        >>> distance(sacobj.event, sacobj.station)
        1889154.9940066522
        >>> # Use Clarke 1966 instead of default
        >>> distance(sacobj.event, sacobj.station, ellps='clrk66')
        1889121.778136402
    """
    return _azdist(
        lat1=location_1.latitude,
        lon1=location_1.longitude,
        lat2=location_2.latitude,
        lon2=location_2.longitude,
        ellps=ellps,
    )[2]
