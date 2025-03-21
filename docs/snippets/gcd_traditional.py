from pysmo.classes import SAC
from pyproj import Geod  # (1)!


def f_traditional(seismogram: SAC) -> float:
    """Calculate the great circle distance between the event and station.

    Parameters:
        seismogram: SAC seismogram object.

    Returns:
        Distance between the points in metres using the WGS84 ellipsoid.
    """

    station_latitude = seismogram.stla  # (2)!
    station_longitude = seismogram.stlo
    event_latitude = seismogram.evla
    event_longitude = seismogram.evlo

    if (
        station_latitude is None  # (3)!
        or station_longitude is None
        or event_latitude is None
        or event_longitude is None
    ):
        raise ValueError("One or more coordinates are None.")

    g = Geod(ellps="WGS84")
    _, _, distance = g.inv(  # (4)!
        station_longitude, station_latitude, event_longitude, event_latitude
    )
    return distance


my_seismogram = SAC.from_file("testfile.sac")
gcd = f_traditional(my_seismogram)
print(f"The great circle distance is {gcd} metres.")
