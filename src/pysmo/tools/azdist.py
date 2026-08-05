"""Common distance and azimuth calculations using [`pyproj.Geod`][]."""

import math

from pyproj import Geod

from pysmo import Location

__all__ = ["azimuth", "backazimuth", "distance", "haversine"]

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
        location_1: Origin location. Any object implementing the [`Location`][pysmo.Location] protocol.
        location_2: Target location. Any object implementing the [`Location`][pysmo.Location] protocol.
        ellps: Ellipsoid to use for azimuth calculation.

    Returns:
        Azimuth in degrees from location 1 to location 2.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import azimuth
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> azimuth(sac.event, sac.station)
        332.23754
        >>> # Use Clarke 1966 instead of default
        >>> azimuth(sac.event, sac.station, ellps='clrk66')
        332.23615
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[0]


def backazimuth(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate backazimuth between two points.

    Args:
        location_1: Origin location. Any object implementing the [`Location`][pysmo.Location] protocol.
        location_2: Target location. Any object implementing the [`Location`][pysmo.Location] protocol.
        ellps: Ellipsoid to use for backazimuth calculation.

    Returns:
        Backazimuth in degrees from point 2 to point 1.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import backazimuth
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> backazimuth(sac.event, sac.station)
        152.67366
        >>> # Use Clarke 1966 instead of default
        >>> backazimuth(sac.event, sac.station, ellps='clrk66')
        152.672271
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[1]


def distance(
    location_1: Location, location_2: Location, ellps: str = DEFAULT_ELLPS
) -> float:
    """Calculate the great circle distance (in metres) between two locations.

    Args:
        location_1: Origin location. Any object implementing the [`Location`][pysmo.Location] protocol.
        location_2: Target location. Any object implementing the [`Location`][pysmo.Location] protocol.
        ellps: Ellipsoid to use for distance calculation.

    Returns:
        Great Circle Distance in metres.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import distance
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> distance(sac.event, sac.station)
        8603325.124
        >>> # Use Clarke 1966 instead of default
        >>> distance(sac.event, sac.station, ellps='clrk66')
        8602982.024
        >>>
        ```
    """
    return _azdist(location_1=location_1, location_2=location_2, ellps=ellps)[2]


def haversine(location_1: Location, location_2: Location) -> float:
    """Calculate the great circle distance in degrees between two locations.

    Uses the haversine formula on a spherical Earth, which is the conventional
    model for seismological epicentral distance.

    Args:
        location_1: Origin location. Any object implementing the [`Location`][pysmo.Location] protocol.
        location_2: Target location. Any object implementing the [`Location`][pysmo.Location] protocol.

    Returns:
        Epicentral distance in degrees.

    Examples:
        ```python
        >>> from pysmo.classes import SAC
        >>> from pysmo.tools.azdist import haversine
        >>> sac = SAC.from_file("example.sac")
        >>> # the SAC class provides both event and station
        >>> haversine(sac.event, sac.station)
        77.638354
        >>> # compare with the SAC gcarc header (spherical law of cosines)
        >>> float(sac.gcarc)
        77.638354
        >>>
        ```
    """
    lat1 = math.radians(location_1.latitude)
    lat2 = math.radians(location_2.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(location_2.longitude - location_1.longitude)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    # Clamp to guard against floating-point rounding pushing a fraction
    # above 1.0 for near-identical or near-antipodal coordinates.
    a = min(1.0, max(0.0, a))
    return math.degrees(2 * math.asin(math.sqrt(a)))
