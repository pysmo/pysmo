"""Common distance and azimuth calculations using [`pyproj.Geod`][pyproj.Geod]."""

from pysmo import Location
from pyproj import Geod

__all__ = ["azimuth", "backazimuth", "distance"]

DEFAULT_ELLPS = "WGS84"
"""Default model for distance and azimuth calculations."""


def _azdist(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> tuple[float, float, float]:
    """Return forward/backazimuth and distance using pyproj (proj4 bindings).

    Args:
        location_1: location of point 1.
        location_2: location of point 2.
        ellps: Ellipsoid to use for calculations.

    Returns:
        az: Azimuth
        baz: Backazimuth
        dist: Distance between the points in metres.
    """
    g = Geod(ellps=ellps)
    az, baz, dist = g.inv(
        lons1=location_1.longitude,
        lats1=location_1.latitude,
        lons2=location_2.longitude,
        lats2=location_2.latitude,
    )

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


    Args:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Azimuth in degrees from location 1 to location 2.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import azimuth
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> azimuth(sac.event, sac.station)
        181.91993
        >>> # Use Clarke 1966 instead of default
        >>> azimuth(sac.event, sac.station, ellps='clrk66')
        181.92002
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[0]


def backazimuth(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate backazimuth (in DEG) between two points.

    Args:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Backzimuth in degrees from point 2 to point 1

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import backazimuth
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> backazimuth(sac.event, sac.station)
        2.467753
        >>> # Use Clarke 1966 instead of default
        >>> backazimuth(sac.event, sac.station, ellps='clrk66')
        2.467847
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[1]


def distance(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate the great circle distance (in metres) between two locations.

    Args:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for distance calculation

    Returns:
        Great Circle Distance in metres.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import distance
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> distance(sac.event, sac.station)
        1889154.994
        >>> # Use Clarke 1966 instead of default
        >>> distance(sac.event, sac.station, ellps='clrk66')
        1889121.778
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[2]
