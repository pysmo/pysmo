__author__ = "Simon Lloyd"
__copyright__ = "Copyright (c) 2012 Simon Lloyd"


from pyproj import Geod
from pysmo import Location


def azimuth(point1: Location, point2: Location, ellps: str = 'WGS84') -> float:
    """
    Calculate azimuth (in DEG) between two points. The default ellipse used is
    'WGS84', but others may be specified. For more information see:

    https://pyproj4.github.io/pyproj/stable

    :param point1: Name of the event object providing coordinates of the origin point.
    :type point1: Location
    :param point2: Name of the station object providing coordinates of the target point.
    :type point2: Location
    :param ellps: Ellipsoid to use for azimuth calculation
    :type ellps: str
    :returns: Azimuth
    :rtype: float

    Example usage::

        >>> from pysmo import SAC, azimuth
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> azimuth = azimuth(sacobj.Event, sacobj.Station)  # the SAC class provides both event and station
        >>> azimuth = azimuth(sacobj.Event, sacobj.Station, ellps='clrk66') # Use Clarke 1966 instead of default
    """
    return __azdist(point1, point2, ellps)[0]


def backazimuth(point1: Location, point2: Location, ellps: str = 'WGS84') -> float:
    """
    Calculate backazimuth (in DEG) between two points. The default ellipse used is
    'WGS84', but others may be specified. For more information see:

    https://pyproj4.github.io/pyproj/stable

    :param point1: Name of the event object providing coordinates of the origin point.
    :type point1: Location
    :param point2: Name of the station object providing coordinates of the target point.
    :type point2: Location
    :param ellps: Ellipsoid to use for azimuth calculation
    :type ellps: str
    :returns: Azimuth
    :rtype: float

    Example usage::

        >>> from pysmo import SAC, backazimuth
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> azimuth = backazimuth(sacobj.Event, sacobj.Station)  # the SAC class provides both event and station
        >>> azimuth = backazimuth(sacobj.Event, sacobj.Station, ellps='clrk66') # Use Clarke 1966 instead of default
    """
    return __azdist(point1, point2, ellps)[1]


def distance(point1: Location, point2: Location, ellps: str = 'WGS84') -> float:
    """
    Calculate the great circle distance (in metres) between two points. The
    default ellipse used is 'WGS84', but others may be specified. For more information see:

    https://pyproj4.github.io/pyproj/stable

    :param point1: Name of the event object providing coordinates of the origin point.
    :type point1: Location
    :param point2: Name of the station object providing coordinates of the target point.
    :type point2: Location
    :param ellps: Ellipsoid to use for distance calculation
    :type ellps: str
    :returns: Great Circle Distance in metres.
    :rtype: float

    Example usage::

        >>> from pysmo import SAC, distance
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> azimuth = distance(sacobj.Event, sacobj.Station)  # the SAC class provides both event and station
        >>> azimuth = distance(sacobj.Event, sacobj.Station, ellps='clrk66') # Use Clarke 1966 instead of default
    """
    return __azdist(point1, point2, ellps)[2]


def __azdist(point1: Location, point2: Location, ellps: str) -> tuple[float, float, float]:
    """
    Return forward/backazimuth and distance using
    pyproj (proj4 bindings)
    """
    g = Geod(ellps=ellps)
    az, baz, dist = g.inv(point1.longitude, point1.latitude,
                          point2.longitude, point2.latitude)
    # Prefer positive bearings
    if az < 0:
        az += 360
    if baz < 0:
        baz += 360
    return az, baz, dist
