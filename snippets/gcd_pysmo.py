from pysmo import Location  # (1)!
from pysmo.classes import SAC
from pyproj import Geod


def f_pysmo(location_1: Location, location_2: Location) -> float:
    """Calculate the great circle distance between two locations.

    Parameters:
        location_1: Location of the first point.
        location_2: Location of the second point.

    Returns:
        Distance between the points in metres using the WGS84 ellipsoid.
    """

    g = Geod(ellps="WGS84")
    _, _, distance = g.inv(
        location_1.longitude,
        location_1.latitude,
        location_2.longitude,
        location_2.latitude,
    )
    return distance


my_seismogram = SAC.from_file("example.sac")
my_event = my_seismogram.event  # (2)!
my_station = my_seismogram.station
gcd = f_pysmo(my_event, my_station)
print(f"The great circle distance is {gcd} metres.")
