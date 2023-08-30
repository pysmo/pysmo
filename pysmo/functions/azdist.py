from pysmo import Location
from pysmo.lib.functions import azdist
from pysmo.lib.defaults import DEFAULT_ELLPS


def azimuth(point1: Location, point2: Location, ellps: str = DEFAULT_ELLPS) -> float:
    """Calculate azimuth between two points.

    info:
        For more information see: https://pyproj4.github.io/pyproj/stable

    Parameters:
        point1: Name of the event object providing coordinates of the origin point.
        point2: Name of the station object providing coordinates of the target point.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Azimuth in degrees from point 1 to point 2.

    Examples:
        >>> from pysmo import SAC
        >>> from pysmo.functions import azimuth
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth = azimuth(sacobj.event, sacobj.station)
        >>> # Use Clarke 1966 instead of default
        >>> azimuth = azimuth(sacobj.event, sacobj.station, ellps='clrk66')

    """
    return __azdist(point1, point2, ellps)[0]


def backazimuth(point1: Location, point2: Location, ellps: str = DEFAULT_ELLPS) -> float:
    """Calculate backazimuth (in DEG) between two points.

    info:
        For more information see: https://pyproj4.github.io/pyproj/stable

    Parameters:
        point1: Name of the event object providing coordinates of the origin point.
        point2: Name of the station object providing coordinates of the target point.
        ellps: Ellipsoid to use for azimuth calculation

    Returns:
        Backzimuth in degrees from point 2 to point 1

    Examples:
        >>> from pysmo import SAC
        >>> from pysmo.functions import backazimuth
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth = backazimuth(sacobj.event, sacobj.station)
        >>> # Use Clarke 1966 instead of default
        >>> azimuth = backazimuth(sacobj.event, sacobj.station, ellps='clrk66')
    """
    return __azdist(point1, point2, ellps)[1]


def distance(point1: Location, point2: Location, ellps: str = DEFAULT_ELLPS) -> float:
    """Calculate the great circle distance (in metres) between two points.

    info:
        For more information see: https://pyproj4.github.io/pyproj/stable

    Parameters:
        point1: Name of the event object providing coordinates of the origin point.
        point2: Name of the station object providing coordinates of the target point.
        ellps: Ellipsoid to use for distance calculation

    Returns:
        Great Circle Distance in metres.

    Examples:
        >>> from pysmo import SAC
        >>> from pysmo.functions import distance
        >>> sacobj = SAC.from_file('sacfile.sac')
        >>> # the SAC class provides both event and station
        >>> azimuth = distance(sacobj.event, sacobj.station)
        >>> # Use Clarke 1966 instead of default
        >>> azimuth = distance(sacobj.event, sacobj.station, ellps='clrk66')
    """
    return __azdist(point1, point2, ellps)[2]


def __azdist(point1: Location, point2: Location, ellps: str) -> tuple[float, float, float]:
    """Return forward/backazimuth and distance using pyproj (proj4 bindings)."""
    return azdist(lat1=point1.latitude, lon1=point1.longitude, lat2=point2.latitude,
                  lon2=point2.longitude, ellps=ellps)
