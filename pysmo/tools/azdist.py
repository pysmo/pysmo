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

    Parameters:
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


    Parameters:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Azimuth in degrees from location 1 to location 2.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import azimuth
        >>> sacobj = SAC.from_file('example.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth(sacobj.event, sacobj.station)
        181.9199258637492
        >>> # Use Clarke 1966 instead of default
        >>> azimuth(sacobj.event, sacobj.station, ellps='clrk66')
        181.92001941872516
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[0]


def backazimuth(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate backazimuth (in DEG) between two points.

    Parameters:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Backzimuth in degrees from point 2 to point 1

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import backazimuth
        >>> sacobj = SAC.from_file('example.sac')
        >>> # the SAC class provides both event and station
        >>> backazimuth(sacobj.event, sacobj.station)
        2.4677533885335947
        >>> # Use Clarke 1966 instead of default
        >>> backazimuth(sacobj.event, sacobj.station, ellps='clrk66')
        2.467847115319614
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[1]


def distance(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate the great circle distance (in metres) between two locations.

    Parameters:
        location_1: Name of the event object providing coordinates of the origin location.
        location_2: Name of the station object providing coordinates of the target location.
        ellps: Ellipsoid to use for distance calculation

    Returns:
        Great Circle Distance in metres.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import distance
        >>> sacobj = SAC.from_file('example.sac')
        >>> # the SAC class provides both event and station
        >>> distance(sacobj.event, sacobj.station)
        1889154.9940066522
        >>> # Use Clarke 1966 instead of default
        >>> distance(sacobj.event, sacobj.station, ellps='clrk66')
        1889121.778136402
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[2]
