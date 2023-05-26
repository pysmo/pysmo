from __future__ import annotations

__author__ = "Simon Lloyd"
__copyright__ = "Copyright (c) 2012 Simon Lloyd"


from pyproj import Geod
from pysmo.core.protocols import Station, Epicenter


def azimuth(event: Epicenter, station: Station, ellps: str = 'WGS84') -> float:
    """
    Calculate azimuth (in DEG) from an event to a station. The default ellipse used is
    'WGS84', but others may be specified. For more information see:

    https://pyproj4.github.io/pyproj/stable

    :param event: Name of the event object providing coordinates of the origin point.
    :type event: Event
    :param station: Name of the station object providing coordinates of the target point.
    :type station: Station
    :param ellps: Ellipsoid to use for azimuth calculation
    :type ellps: string
    :returns: Azimuth
    :rtype: float

    Example usage::

        >>> from pysmo import SAC, azimuth
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> azimuth = azimuth(sacobj, sacobj)  # the SAC class provides both event and station
        >>> azimuth = azimuth(sacobj, sacobj, ellps='clrk66') # Use Clarke 1966 instead of default
    """
    return __azdist(event, station, ellps)[0]


def backazimuth(event: Epicenter, station: Station, ellps: str = 'WGS84') -> float:
    """
    Calculate backazimuth (in DEG) from a station to an event. The default ellipse used is
    'WGS84', but others may be specified. For more information see:

    https://pyproj4.github.io/pyproj/stable

    :param event: Name of the event object providing coordinates of the origin point.
    :type event: Event
    :param station: Name of the station object providing coordinates of the target point.
    :type station: Station
    :param ellps: Ellipsoid to use for azimuth calculation
    :type ellps: string
    :returns: Azimuth
    :rtype: float

    Example usage::

        >>> from pysmo import SAC, backazimuth
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> azimuth = backazimuth(sacobj, sacobj)  # the SAC class provides both event and station
        >>> azimuth = backazimuth(sacobj, sacobj, ellps='clrk66') # Use Clarke 1966 instead of default
    """
    return __azdist(event, station, ellps)[1]


def distance(event: Epicenter, station: Station, ellps: str = 'WGS84') -> float:
    """
    Calculate the great circle distance (in metres) between an event and a station. The
    default ellipse used is 'WGS84', but others may be specified. For more information see:

    https://pyproj4.github.io/pyproj/stable

    :param event: Name of the event object providing coordinates of the origin point.
    :type event: Event
    :param station: Name of the station object providing coordinates of the target point.
    :type station: Station
    :param ellps: Ellipsoid to use for distance calculation
    :type ellps: string
    :returns: Great Circle Distance in metres.
    :rtype: float

    Example usage::

        >>> from pysmo import SAC, distance
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> azimuth = distance(sacobj, sacobj)  # the SAC class provides both event and station
        >>> azimuth = distance(sacobj, sacobj, ellps='clrk66') # Use Clarke 1966 instead of default
    """
    return __azdist(event, station, ellps)[2]


def __azdist(event: Epicenter, station: Station, ellps: str) -> tuple[float, float, float]:
    """
    Return forward/backazimuth and distance using
    pyproj (proj4 bindings)
    """
    g = Geod(ellps=ellps)
    az, baz, dist = g.inv(event.event_longitude, event.event_latitude,
                          station.station_longitude, station.station_latitude)
    # Prefer positive bearings
    if az < 0:
        az += 360
    if baz < 0:
        baz += 360
    return az, baz, dist
